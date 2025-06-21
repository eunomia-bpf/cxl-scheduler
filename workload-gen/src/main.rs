use workload_gen::*;
use clap::Parser;
use anyhow::Result;
use std::fs;

#[derive(Parser, Debug)]
#[command(author, version, about = "CXL Pattern Executor", long_about = None)]
struct Cli {
    /// Path to pattern specification JSON file
    #[arg(short, long)]
    pattern: String,

    /// Device path for CXL memory (overrides pattern spec)
    #[arg(short = 'D', long)]
    device: Option<String>,

    /// Use mmap when accessing device
    #[arg(long, default_value_t = false)]
    mmap: bool,

    /// Verbose output
    #[arg(short, long, default_value_t = false)]
    verbose: bool,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    
    if cli.verbose {
        env_logger::init();
    }

    // Load pattern specification
    let spec_content = fs::read_to_string(&cli.pattern)?;
    let mut pattern_spec: PatternSpec = serde_json::from_str(&spec_content)?;

    // Apply CLI overrides
    if let Some(device_path) = cli.device {
        pattern_spec.device_path = Some(device_path);
        pattern_spec.use_mmap = cli.mmap;
    }

    // Create and run executor
    let executor = PatternExecutor::new(&pattern_spec)?;
    let results = executor.execute(&pattern_spec)?;

    // Display results
    println!("=== Execution Results ===");
    println!("Pattern: {}", pattern_spec.name);
    println!("Duration: {:.3} s", results.total_duration_ns as f64 / 1e9);
    println!("Operations: {}", results.total_operations);
    println!("Average Latency: {:.2} ns", results.average_latency_ns);
    
    if results.total_bytes_read > 0 {
        println!("Read: {} bytes, {:.2} MB/s", 
                 results.total_bytes_read, 
                 results.read_throughput_mbps);
    }
    
    if results.total_bytes_written > 0 {
        println!("Write: {} bytes, {:.2} MB/s", 
                 results.total_bytes_written, 
                 results.write_throughput_mbps);
    }
    
    if results.total_cpu_cycles > 0 {
        println!("CPU cycles: {}", results.total_cpu_cycles);
    }

    if cli.verbose {
        println!("\n=== Per-Thread Stats ===");
        for (i, thread_stats) in results.thread_stats.iter().enumerate() {
            if thread_stats.operations_completed > 0 {
                println!("Thread {}: {} ops, avg {:.2} ns", 
                         i, 
                         thread_stats.operations_completed,
                         thread_stats.total_latency_ns as f64 / thread_stats.operations_completed as f64);
            }
        }
    }

    Ok(())
}
