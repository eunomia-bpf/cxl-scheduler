use clap::{Parser, Subcommand};
use anyhow::Result;
use std::path::PathBuf;

mod common;
mod executor;
mod generator;

use common::{Pattern, WorkloadSpec, ExecutionResults, AddressMap, ScheduleMap, ExecutionConfig};
use executor::PatternExecutor;
use generator::generate_pattern;

#[derive(Parser)]
#[command(name = "workload-gen")]
#[command(about = "CXL workload generator with ultra-simple, orthogonal design")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Execute a pattern specification
    Exec {
        /// Path to pattern JSON file
        #[arg(short, long)]
        pattern: PathBuf,
        
        /// Address mapping configuration
        #[arg(short, long)]
        address_map: Option<PathBuf>,
        
        /// Schedule mapping configuration  
        #[arg(short, long)]
        schedule_map: Option<PathBuf>,
        
        /// Execution configuration
        #[arg(short, long)]
        execution_config: Option<PathBuf>,
        
        /// Override duration in seconds
        #[arg(short, long)]
        duration: Option<u64>,
        
        /// Verbose output
        #[arg(short, long)]
        verbose: bool,
        
        /// Output results to file
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    
    /// Generate a pattern from workload specification
    Generate {
        /// Workload type
        #[arg(short, long)]
        workload_type: Option<String>,
        
        /// Path to workload specification JSON file
        #[arg(short, long)]
        workload: Option<PathBuf>,
        
        /// Number of operations to generate
        #[arg(long, default_value = "1000")]
        operations: u64,
        
        /// Number of threads
        #[arg(long, default_value = "4")]
        threads: u32,
        
        /// Read ratio (0.0-1.0)
        #[arg(long, default_value = "0.7")]
        read_ratio: f64,
        
        /// Block size in bytes
        #[arg(long, default_value = "4096")]
        block_size: u64,
        
        /// Output pattern file
        #[arg(short, long)]
        output: PathBuf,
        
        /// Verbose output
        #[arg(short, long)]
        verbose: bool,
    },
    
    /// Analyze pattern scheduling requirements
    Schedule {
        /// Path to pattern JSON file
        #[arg(short, long)]
        pattern: PathBuf,
        
        /// Analyze scheduling requirements
        #[arg(long)]
        analyze: bool,
        
        /// Generate recommended schedule config
        #[arg(long)]
        generate_config: bool,
        
        /// Output config file
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
}

fn main() -> Result<()> {
    env_logger::init();
    let cli = Cli::parse();

    match cli.command {
        Commands::Exec { 
            pattern, 
            address_map,
            schedule_map,
            execution_config,
            duration,
            verbose, 
            output 
        } => {
            execute_command(pattern, address_map, schedule_map, execution_config, duration, verbose, output)
        }
        Commands::Generate { 
            workload_type,
            workload, 
            operations,
            threads,
            read_ratio,
            block_size,
            output, 
            verbose 
        } => {
            generate_command(workload_type, workload, operations, threads, read_ratio, block_size, output, verbose)
        }
        Commands::Schedule {
            pattern,
            analyze,
            generate_config,
            output,
        } => {
            schedule_command(pattern, analyze, generate_config, output)
        }
    }
}

fn execute_command(
    pattern_path: PathBuf,
    address_map_path: Option<PathBuf>,
    schedule_map_path: Option<PathBuf>,
    execution_config_path: Option<PathBuf>,
    duration_override: Option<u64>,
    verbose: bool,
    output_path: Option<PathBuf>,
) -> Result<()> {
    // Load pattern
    let pattern_content = std::fs::read_to_string(&pattern_path)?;
    let pattern: Pattern = serde_json::from_str(&pattern_content)?;
    
    // Load optional configurations
    let address_map = if let Some(path) = address_map_path {
        let content = std::fs::read_to_string(&path)?;
        Some(serde_json::from_str::<AddressMap>(&content)?)
    } else {
        None
    };
    
    let schedule_map = if let Some(path) = schedule_map_path {
        let content = std::fs::read_to_string(&path)?;
        Some(serde_json::from_str::<ScheduleMap>(&content)?)
    } else {
        None
    };
    
    let mut execution_config = if let Some(path) = execution_config_path {
        let content = std::fs::read_to_string(&path)?;
        serde_json::from_str::<ExecutionConfig>(&content)?
    } else {
        ExecutionConfig {
            duration_seconds: Some(10),
            rate_limit: None,
            warmup_seconds: None,
            metrics_interval: None,
        }
    };
    
    // Apply duration override
    if let Some(duration) = duration_override {
        execution_config.duration_seconds = Some(duration);
    }
    
    if verbose {
        println!("=== Pattern Execution ===");
        println!("Pattern: {}", pattern.name);
        println!("Operations: {}", pattern.operations.len());
        
        // Analyze threads
        let mut threads: std::collections::HashSet<u32> = std::collections::HashSet::new();
        for op in &pattern.operations {
            match op {
                common::Operation::Read { thread, .. } |
                common::Operation::Write { thread, .. } |
                common::Operation::Cpu { thread, .. } |
                common::Operation::Gpu { thread, .. } => {
                    threads.insert(*thread);
                }
            }
        }
        println!("Threads: {:?}", threads);
        
        if let Some(ref addr_map) = address_map {
            println!("Memory regions: {}", addr_map.memory_regions.len());
        }
        
        if let Some(ref sched_map) = schedule_map {
            println!("Thread mappings: {}", sched_map.thread_mapping.len());
        }
        
        println!("Duration: {:?} seconds", execution_config.duration_seconds);
        println!();
    }
    
    // Execute pattern
    let executor = PatternExecutor::new(pattern, address_map, schedule_map, execution_config)?;
    let results = executor.execute()?;
    
    // Display results
    display_results(&results, verbose);
    
    // Save results if requested
    if let Some(output) = output_path {
        let results_json = serde_json::to_string_pretty(&results)?;
        std::fs::write(output, results_json)?;
        println!("Results saved to file");
    }
    
    Ok(())
}

fn generate_command(
    workload_type: Option<String>,
    workload_path: Option<PathBuf>,
    operations: u64,
    threads: u32,
    read_ratio: f64,
    block_size: u64,
    output_path: PathBuf,
    verbose: bool,
) -> Result<()> {
    let pattern = if let Some(workload_path) = workload_path {
        // Generate from workload file
        let workload_content = std::fs::read_to_string(&workload_path)?;
        let workload: WorkloadSpec = serde_json::from_str(&workload_content)?;
        
        if verbose {
            println!("=== Pattern Generation ===");
            println!("Workload: {}", workload.name);
            println!("Type: {:?}", workload.workload_type);
            println!();
        }
        
        generate_pattern(&workload)?
    } else if let Some(wl_type) = workload_type {
        // Generate from command line parameters
        let workload_type = match wl_type.as_str() {
            "sequential" => common::WorkloadType::Sequential,
            "random" => common::WorkloadType::Random,
            "hotspot" => common::WorkloadType::Hotspot,
            "database" => common::WorkloadType::Database,
            "analytics" => common::WorkloadType::Analytics,
            "cache" => common::WorkloadType::Cache,
            "mixed" => common::WorkloadType::Mixed,
            _ => return Err(anyhow::anyhow!("Unknown workload type: {}", wl_type)),
        };
        
        let mut params = std::collections::HashMap::new();
        params.insert("operations".to_string(), serde_json::Value::Number(operations.into()));
        params.insert("threads".to_string(), serde_json::Value::Number(threads.into()));
        params.insert("read_ratio".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(read_ratio).unwrap()));
        params.insert("block_size".to_string(), serde_json::Value::Number(block_size.into()));
        
        let workload = WorkloadSpec {
            name: format!("{}_generated", wl_type),
            workload_type,
            params,
        };
        
        if verbose {
            println!("=== Pattern Generation ===");
            println!("Type: {:?}", workload.workload_type);
            println!("Operations: {}", operations);
            println!("Threads: {}", threads);
            println!("Read ratio: {}", read_ratio);
            println!("Block size: {}", block_size);
            println!();
        }
        
        generate_pattern(&workload)?
    } else {
        return Err(anyhow::anyhow!("Must specify either --workload-type or --workload"));
    };
    
    if verbose {
        println!("Generated pattern: {}", pattern.name);
        println!("Total operations: {}", pattern.operations.len());
        println!();
    }
    
    // Save pattern
    let pattern_json = serde_json::to_string_pretty(&pattern)?;
    std::fs::write(&output_path, pattern_json)?;
    
    println!("Pattern generated and saved to: {}", output_path.display());
    
    Ok(())
}

fn schedule_command(
    pattern_path: PathBuf,
    analyze: bool,
    generate_config: bool,
    output_path: Option<PathBuf>,
) -> Result<()> {
    // Load pattern
    let pattern_content = std::fs::read_to_string(&pattern_path)?;
    let pattern: Pattern = serde_json::from_str(&pattern_content)?;
    
    if analyze {
        println!("=== Schedule Analysis ===");
        println!("Pattern: {}", pattern.name);
        
        // Analyze thread usage
        let mut threads: std::collections::HashSet<u32> = std::collections::HashSet::new();
        let mut gpu_threads: std::collections::HashSet<u32> = std::collections::HashSet::new();
        
        for op in &pattern.operations {
            match op {
                common::Operation::Read { thread, .. } |
                common::Operation::Write { thread, .. } |
                common::Operation::Cpu { thread, .. } => {
                    threads.insert(*thread);
                }
                common::Operation::Gpu { thread, .. } => {
                    gpu_threads.insert(*thread);
                    threads.insert(*thread);
                }
            }
        }
        
        println!("Total threads: {}", threads.len());
        println!("CPU threads: {}", threads.len() - gpu_threads.len());
        println!("GPU threads: {}", gpu_threads.len());
        
        // Analyze address ranges
        let mut min_addr = u64::MAX;
        let mut max_addr = 0u64;
        
        for op in &pattern.operations {
            match op {
                common::Operation::Read { addr, size, .. } |
                common::Operation::Write { addr, size, .. } => {
                    min_addr = min_addr.min(*addr);
                    max_addr = max_addr.max(*addr + *size);
                }
                _ => {}
            }
        }
        
        if min_addr != u64::MAX {
            println!("Address range: 0x{:x} - 0x{:x} ({} bytes)", min_addr, max_addr, max_addr - min_addr);
        }
    }
    
    if generate_config {
        // Generate a basic schedule config
        let mut threads: std::collections::HashSet<u32> = std::collections::HashSet::new();
        let mut gpu_threads: std::collections::HashSet<u32> = std::collections::HashSet::new();
        
        for op in &pattern.operations {
            match op {
                common::Operation::Read { thread, .. } |
                common::Operation::Write { thread, .. } |
                common::Operation::Cpu { thread, .. } => {
                    threads.insert(*thread);
                }
                common::Operation::Gpu { thread, .. } => {
                    gpu_threads.insert(*thread);
                    threads.insert(*thread);
                }
            }
        }
        
        let mut thread_mapping = Vec::new();
        let mut cpu_id = 0u32;
        
        for &thread in &threads {
            if gpu_threads.contains(&thread) {
                thread_mapping.push(common::ThreadMapping {
                    thread,
                    cpu: None,
                    gpu: Some(0),
                    numa_node: None,
                });
            } else {
                thread_mapping.push(common::ThreadMapping {
                    thread,
                    cpu: Some(cpu_id),
                    gpu: None,
                    numa_node: Some(cpu_id / 4), // Assume 4 CPUs per NUMA node
                });
                cpu_id += 1;
            }
        }
        
        let schedule_map = ScheduleMap { thread_mapping };
        
        if let Some(output) = output_path {
            let config_json = serde_json::to_string_pretty(&schedule_map)?;
            std::fs::write(&output, config_json)?;
            println!("Schedule config saved to: {}", output.display());
        } else {
            let config_json = serde_json::to_string_pretty(&schedule_map)?;
            println!("Generated schedule config:");
            println!("{}", config_json);
        }
    }
    
    Ok(())
}

fn display_results(results: &ExecutionResults, verbose: bool) {
    println!("=== Execution Results ===");
    println!("Pattern: {}", results.pattern_name);
    println!("Duration: {:.3} s", results.total_duration_ns as f64 / 1_000_000_000.0);
    println!("Operations: {}", results.total_operations);
    
    if results.total_operations > 0 {
        println!("Average Latency: {:.2} ns", results.average_latency_ns);
        println!("Operations/sec: {:.2}", results.operations_per_second);
    }
    
    if results.total_bytes_read > 0 {
        println!("Read: {} bytes, {:.2} MB/s", 
            results.total_bytes_read, 
            results.read_throughput_mbps
        );
    }
    
    if results.total_bytes_written > 0 {
        println!("Write: {} bytes, {:.2} MB/s", 
            results.total_bytes_written, 
            results.write_throughput_mbps
        );
    }
    
    if results.total_cpu_cycles > 0 {
        println!("CPU cycles: {}", results.total_cpu_cycles);
    }
    
    if verbose {
        println!("\n=== Per-Thread Stats ===");
        for thread_stat in &results.thread_stats {
            println!("Thread {}: {} ops, avg {:.2} ns, min {:.2} ns, max {:.2} ns",
                thread_stat.thread_id,
                thread_stat.operations_completed,
                if thread_stat.operations_completed > 0 {
                    thread_stat.total_latency_ns as f64 / thread_stat.operations_completed as f64
                } else { 0.0 },
                thread_stat.min_latency_ns,
                thread_stat.max_latency_ns
            );
        }
    }
}
