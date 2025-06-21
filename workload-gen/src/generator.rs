use crate::common::*;
use anyhow::Result;
use rand::prelude::*;
use std::collections::HashMap;

/// Generate a simple pattern from a workload specification
pub fn generate_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    match workload.workload_type {
        WorkloadType::Sequential => generate_sequential_pattern(workload),
        WorkloadType::Random => generate_random_pattern(workload),
        WorkloadType::Hotspot => generate_hotspot_pattern(workload),
        WorkloadType::Database => generate_database_pattern(workload),
        WorkloadType::Analytics => generate_analytics_pattern(workload),
        WorkloadType::Cache => generate_cache_pattern(workload),
        WorkloadType::Mixed => generate_mixed_pattern(workload),
    }
}

fn generate_sequential_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    let operations_count = get_param_as_u64(&workload.params, "operations").unwrap_or(1000);
    let threads = get_param_as_u32(&workload.params, "threads").unwrap_or(4);
    let read_ratio = get_param_as_f64(&workload.params, "read_ratio").unwrap_or(0.7);
    let block_size = get_param_as_u64(&workload.params, "block_size").unwrap_or(4096);
    
    let mut operations = Vec::new();
    let ops_per_thread = operations_count / threads as u64;
    
    for thread in 0..threads {
        let thread_base_addr = thread as u64 * 1024 * 1024; // 1MB per thread
        let mut current_addr = thread_base_addr;
        
        for _ in 0..ops_per_thread {
            if rand::random::<f64>() < read_ratio {
                operations.push(Operation::Read {
                    addr: current_addr,
                    size: block_size,
                    thread,
                });
            } else {
                operations.push(Operation::Write {
                    addr: current_addr,
                    size: block_size,
                    thread,
                });
            }
            current_addr += block_size;
        }
    }
    
    Ok(Pattern {
        name: workload.name.clone(),
        operations,
    })
}

fn generate_random_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    let operations_count = get_param_as_u64(&workload.params, "operations").unwrap_or(1000);
    let threads = get_param_as_u32(&workload.params, "threads").unwrap_or(4);
    let read_ratio = get_param_as_f64(&workload.params, "read_ratio").unwrap_or(0.7);
    let block_size = get_param_as_u64(&workload.params, "block_size").unwrap_or(4096);
    let memory_size = get_param_as_u64(&workload.params, "memory_size").unwrap_or(1024 * 1024 * 1024); // 1GB
    
    let mut operations = Vec::new();
    let ops_per_thread = operations_count / threads as u64;
    let mut rng = StdRng::seed_from_u64(42);
    
    for thread in 0..threads {
        for _ in 0..ops_per_thread {
            let random_addr = rng.gen_range(0..(memory_size - block_size) / block_size) * block_size;
            
            if rand::random::<f64>() < read_ratio {
                operations.push(Operation::Read {
                    addr: random_addr,
                    size: block_size,
                    thread,
                });
            } else {
                operations.push(Operation::Write {
                    addr: random_addr,
                    size: block_size,
                    thread,
                });
            }
        }
    }
    
    Ok(Pattern {
        name: workload.name.clone(),
        operations,
    })
}

fn generate_hotspot_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    let operations_count = get_param_as_u64(&workload.params, "operations").unwrap_or(1000);
    let threads = get_param_as_u32(&workload.params, "threads").unwrap_or(4);
    let read_ratio = get_param_as_f64(&workload.params, "read_ratio").unwrap_or(0.8);
    let block_size = get_param_as_u64(&workload.params, "block_size").unwrap_or(4096);
    let hotspot_ratio = get_param_as_f64(&workload.params, "hotspot_ratio").unwrap_or(0.8);
    let memory_size = get_param_as_u64(&workload.params, "memory_size").unwrap_or(1024 * 1024 * 1024);
    
    let mut operations = Vec::new();
    let ops_per_thread = operations_count / threads as u64;
    let hotspot_size = memory_size / 10; // Hot region is 10% of total memory
    let mut rng = StdRng::seed_from_u64(42);
    
    for thread in 0..threads {
        for _ in 0..ops_per_thread {
            let addr = if rand::random::<f64>() < hotspot_ratio {
                // Access hot region
                rng.gen_range(0..(hotspot_size - block_size) / block_size) * block_size
            } else {
                // Access cold region
                hotspot_size + rng.gen_range(0..((memory_size - hotspot_size - block_size) / block_size)) * block_size
            };
            
            if rand::random::<f64>() < read_ratio {
                operations.push(Operation::Read {
                    addr,
                    size: block_size,
                    thread,
                });
            } else {
                operations.push(Operation::Write {
                    addr,
                    size: block_size,
                    thread,
                });
            }
        }
    }
    
    Ok(Pattern {
        name: workload.name.clone(),
        operations,
    })
}

fn generate_database_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    let operations_count = get_param_as_u64(&workload.params, "operations").unwrap_or(1000);
    let threads = get_param_as_u32(&workload.params, "threads").unwrap_or(4);
    let read_ratio = get_param_as_f64(&workload.params, "read_ratio").unwrap_or(0.9);
    let block_size = get_param_as_u64(&workload.params, "block_size").unwrap_or(8192);
    
    let mut operations = Vec::new();
    let ops_per_thread = operations_count / threads as u64;
    
    for thread in 0..threads {
        let thread_base_addr = thread as u64 * 10 * 1024 * 1024; // 10MB per thread
        let mut current_addr = thread_base_addr;
        
        for i in 0..ops_per_thread {
            // Simulate database access: mostly sequential with some random seeks
            if i % 10 == 0 {
                // Random seek every 10 operations
                current_addr = thread_base_addr + (rand::random::<u64>() % (5 * 1024 * 1024)) & !(block_size - 1);
            }
            
            if rand::random::<f64>() < read_ratio {
                operations.push(Operation::Read {
                    addr: current_addr,
                    size: block_size,
                    thread,
                });
            } else {
                operations.push(Operation::Write {
                    addr: current_addr,
                    size: block_size,
                    thread,
                });
            }
            
            current_addr += block_size;
        }
    }
    
    Ok(Pattern {
        name: workload.name.clone(),
        operations,
    })
}

fn generate_analytics_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    let operations_count = get_param_as_u64(&workload.params, "operations").unwrap_or(1000);
    let threads = get_param_as_u32(&workload.params, "threads").unwrap_or(4);
    let block_size = get_param_as_u64(&workload.params, "block_size").unwrap_or(1024 * 1024); // 1MB blocks
    let cpu_cycles = get_param_as_u64(&workload.params, "cpu_cycles").unwrap_or(1000000);
    
    let mut operations = Vec::new();
    let ops_per_thread = operations_count / threads as u64;
    
    for thread in 0..threads {
        let thread_base_addr = thread as u64 * 100 * 1024 * 1024; // 100MB per thread
        let mut current_addr = thread_base_addr;
        
        for i in 0..ops_per_thread {
            // Read large sequential blocks
            operations.push(Operation::Read {
                addr: current_addr,
                size: block_size,
                thread,
            });
            
            // Add CPU computation after every few reads
            if i % 5 == 4 {
                operations.push(Operation::Cpu {
                    cycles: cpu_cycles,
                    thread,
                });
            }
            
            current_addr += block_size;
        }
    }
    
    Ok(Pattern {
        name: workload.name.clone(),
        operations,
    })
}

fn generate_cache_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    let operations_count = get_param_as_u64(&workload.params, "operations").unwrap_or(1000);
    let threads = get_param_as_u32(&workload.params, "threads").unwrap_or(4);
    let read_ratio = get_param_as_f64(&workload.params, "read_ratio").unwrap_or(0.95);
    let block_size = get_param_as_u64(&workload.params, "block_size").unwrap_or(64); // Cache line size
    let cache_miss_ratio = get_param_as_f64(&workload.params, "cache_miss_ratio").unwrap_or(0.1);
    
    let mut operations = Vec::new();
    let ops_per_thread = operations_count / threads as u64;
    let cache_size = 32 * 1024; // 32KB cache per thread
    
    for thread in 0..threads {
        let thread_base_addr = thread as u64 * 1024 * 1024; // 1MB per thread
        
        for _ in 0..ops_per_thread {
            let addr = if rand::random::<f64>() < cache_miss_ratio {
                // Cache miss - access beyond cache
                thread_base_addr + cache_size + (rand::random::<u64>() % (512 * 1024)) & !(block_size - 1)
            } else {
                // Cache hit - access within cache
                thread_base_addr + (rand::random::<u64>() % cache_size) & !(block_size - 1)
            };
            
            if rand::random::<f64>() < read_ratio {
                operations.push(Operation::Read {
                    addr,
                    size: block_size,
                    thread,
                });
            } else {
                operations.push(Operation::Write {
                    addr,
                    size: block_size,
                    thread,
                });
            }
        }
    }
    
    Ok(Pattern {
        name: workload.name.clone(),
        operations,
    })
}

fn generate_mixed_pattern(workload: &WorkloadSpec) -> Result<Pattern> {
    let operations_count = get_param_as_u64(&workload.params, "operations").unwrap_or(1000);
    let threads = get_param_as_u32(&workload.params, "threads").unwrap_or(4);
    let read_ratio = get_param_as_f64(&workload.params, "read_ratio").unwrap_or(0.7);
    let block_size = get_param_as_u64(&workload.params, "block_size").unwrap_or(4096);
    let cpu_ratio = get_param_as_f64(&workload.params, "cpu_ratio").unwrap_or(0.2);
    let cpu_cycles = get_param_as_u64(&workload.params, "cpu_cycles").unwrap_or(10000);
    
    let mut operations = Vec::new();
    let ops_per_thread = operations_count / threads as u64;
    
    for thread in 0..threads {
        let thread_base_addr = thread as u64 * 1024 * 1024; // 1MB per thread
        let mut current_addr = thread_base_addr;
        
        for _ in 0..ops_per_thread {
            if rand::random::<f64>() < cpu_ratio {
                // CPU operation
                operations.push(Operation::Cpu {
                    cycles: cpu_cycles,
                    thread,
                });
            } else {
                // Memory operation
                if rand::random::<f64>() < read_ratio {
                    operations.push(Operation::Read {
                        addr: current_addr,
                        size: block_size,
                        thread,
                    });
                } else {
                    operations.push(Operation::Write {
                        addr: current_addr,
                        size: block_size,
                        thread,
                    });
                }
                current_addr += block_size;
            }
        }
    }
    
    Ok(Pattern {
        name: workload.name.clone(),
        operations,
    })
}

// Helper functions
fn get_param_as_u64(params: &HashMap<String, serde_json::Value>, key: &str) -> Option<u64> {
    params.get(key)?.as_u64()
}

fn get_param_as_u32(params: &HashMap<String, serde_json::Value>, key: &str) -> Option<u32> {
    params.get(key)?.as_u64().map(|v| v as u32)
}

fn get_param_as_f64(params: &HashMap<String, serde_json::Value>, key: &str) -> Option<f64> {
    params.get(key)?.as_f64()
} 