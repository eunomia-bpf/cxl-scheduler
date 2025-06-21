use crate::common::*;
use anyhow::Result;
use std::fs::OpenOptions;
use std::os::unix::fs::OpenOptionsExt;
use std::ptr;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

/// Simple memory manager
pub struct MemoryManager {
    base_address: *mut u8,
    size: u64,
    is_device: bool,
}

impl MemoryManager {
    pub fn new_system_memory(size: u64) -> Result<Self> {
        let base_address = unsafe {
            let layout = std::alloc::Layout::from_size_align(size as usize, 4096)?;
            std::alloc::alloc(layout)
        };
        
        if base_address.is_null() {
            anyhow::bail!("Failed to allocate {} bytes", size);
        }
        
        // Initialize with pattern
        unsafe {
            for i in 0..size {
                *base_address.add(i as usize) = (i % 256) as u8;
            }
        }
        
        Ok(Self {
            base_address,
            size,
            is_device: false,
        })
    }
    
    pub fn new_device_memory(device_path: &str, size: u64, use_mmap: bool) -> Result<Self> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .custom_flags(libc::O_DIRECT)
            .open(device_path)?;
            
        let base_address = if use_mmap {
            unsafe {
                let addr = libc::mmap(
                    ptr::null_mut(),
                    size as libc::size_t,
                    libc::PROT_READ | libc::PROT_WRITE,
                    libc::MAP_SHARED,
                    std::os::unix::io::AsRawFd::as_raw_fd(&file),
                    0,
                );
                
                if addr == libc::MAP_FAILED {
                    anyhow::bail!("Failed to mmap device");
                }
                
                addr as *mut u8
            }
        } else {
            // For read/write mode, allocate staging buffer
            let layout = std::alloc::Layout::from_size_align(size as usize, 4096)?;
            unsafe { std::alloc::alloc(layout) }
        };
        
        if base_address.is_null() {
            anyhow::bail!("Failed to allocate/map device memory");
        }
        
        Ok(Self {
            base_address,
            size,
            is_device: true,
        })
    }
    
    pub fn execute_read(&self, address: u64, size: usize) -> Result<Duration> {
        if address + size as u64 > self.size {
            anyhow::bail!("Read beyond memory bounds");
        }
        
        let start = Instant::now();
        let mut buffer = vec![0u8; size];
        
        unsafe {
            ptr::copy_nonoverlapping(
                self.base_address.add(address as usize),
                buffer.as_mut_ptr(),
                size,
            );
        }
        
        // Prevent optimization
        std::hint::black_box(buffer);
        
        Ok(start.elapsed())
    }
    
    pub fn execute_write(&self, address: u64, size: usize) -> Result<Duration> {
        if address + size as u64 > self.size {
            anyhow::bail!("Write beyond memory bounds");
        }
        
        let start = Instant::now();
        let buffer = vec![0xAA; size]; // Write pattern
        
        unsafe {
            ptr::copy_nonoverlapping(
                buffer.as_ptr(),
                self.base_address.add(address as usize),
                size,
            );
        }
        
        Ok(start.elapsed())
    }
    
    pub fn execute_cpu(&self, cycles: u64) -> Result<Duration> {
        let start = Instant::now();
        
        // Simple CPU workload
        let mut sum: u64 = 0;
        for i in 0..cycles {
            sum = sum.wrapping_add(i).wrapping_mul(i);
        }
        
        // Prevent optimization
        std::hint::black_box(sum);
        
        Ok(start.elapsed())
    }
}

impl Drop for MemoryManager {
    fn drop(&mut self) {
        if !self.base_address.is_null() {
            if self.is_device {
                unsafe {
                    libc::munmap(self.base_address as *mut libc::c_void, self.size as libc::size_t);
                }
            } else {
                unsafe {
                    let layout = std::alloc::Layout::from_size_align_unchecked(self.size as usize, 4096);
                    std::alloc::dealloc(self.base_address, layout);
                }
            }
        }
    }
}

unsafe impl Send for MemoryManager {}
unsafe impl Sync for MemoryManager {}

/// Metrics collector
#[derive(Clone)]
pub struct MetricsCollector {
    stats: Arc<Mutex<ExecutionResults>>,
}

impl MetricsCollector {
    pub fn new(num_threads: usize) -> Self {
        let mut results = ExecutionResults::default();
        results.thread_stats = vec![ThreadStats::default(); num_threads];
        
        Self {
            stats: Arc::new(Mutex::new(results)),
        }
    }
    
    pub fn record_operation(&self, thread_id: usize, op: &Operation, latency: Duration) {
        let mut stats = self.stats.lock().unwrap();
        let thread_stats = &mut stats.thread_stats[thread_id];
        
        thread_stats.thread_id = thread_id;
        thread_stats.operations_completed += 1;
        
        let latency_ns = latency.as_nanos() as u64;
        thread_stats.total_latency_ns += latency_ns;
        
        if thread_stats.min_latency_ns == 0 || latency_ns < thread_stats.min_latency_ns {
            thread_stats.min_latency_ns = latency_ns;
        }
        if latency_ns > thread_stats.max_latency_ns {
            thread_stats.max_latency_ns = latency_ns;
        }
        
        match op.op_type {
            OpType::Read => {
                thread_stats.bytes_read += op.size.unwrap_or(0) as u64;
            },
            OpType::Write => {
                thread_stats.bytes_written += op.size.unwrap_or(0) as u64;
            },
            OpType::Cpu => {
                thread_stats.cpu_cycles_executed += op.cpu_cycles.unwrap_or(0);
            },
        }
    }
    
    pub fn finalize(&self, total_duration: Duration) -> ExecutionResults {
        let mut stats = self.stats.lock().unwrap();
        
        stats.total_duration_ns = total_duration.as_nanos() as u64;
        stats.total_operations = stats.thread_stats.iter().map(|t| t.operations_completed).sum();
        stats.total_bytes_read = stats.thread_stats.iter().map(|t| t.bytes_read).sum();
        stats.total_bytes_written = stats.thread_stats.iter().map(|t| t.bytes_written).sum();
        stats.total_cpu_cycles = stats.thread_stats.iter().map(|t| t.cpu_cycles_executed).sum();
        
        if stats.total_operations > 0 {
            let total_latency: u64 = stats.thread_stats.iter().map(|t| t.total_latency_ns).sum();
            stats.average_latency_ns = total_latency as f64 / stats.total_operations as f64;
        }
        
        let seconds = total_duration.as_secs_f64();
        if seconds > 0.0 {
            stats.read_throughput_mbps = (stats.total_bytes_read as f64 / (1024.0 * 1024.0)) / seconds;
            stats.write_throughput_mbps = (stats.total_bytes_written as f64 / (1024.0 * 1024.0)) / seconds;
        }
        
        (*stats).clone()
    }
}

/// Simple pattern executor
pub struct PatternExecutor {
    memory: Arc<MemoryManager>,
    metrics: MetricsCollector,
    pattern: PatternSpec,
}

impl PatternExecutor {
    pub fn new(pattern: PatternSpec) -> Result<Self> {
        let memory = if let Some(device_path) = &pattern.device_path {
            Arc::new(MemoryManager::new_device_memory(device_path, pattern.memory_size, pattern.use_mmap)?)
        } else {
            Arc::new(MemoryManager::new_system_memory(pattern.memory_size)?)
        };
        
        let metrics = MetricsCollector::new(pattern.num_threads);
        
        Ok(Self { memory, metrics, pattern })
    }
    
    pub fn execute(&self) -> Result<ExecutionResults> {
        let pattern = &self.pattern;
        println!("Executing pattern: {}", pattern.name);
        println!("Thread patterns: {}", pattern.thread_patterns.len());
        println!("Threads: {}", pattern.num_threads);
        
        let start_time = Instant::now();
        
        // Spawn worker threads
        let mut handles = Vec::new();
        for thread_pattern in &pattern.thread_patterns {
            let thread_pattern = thread_pattern.clone();
            let memory = Arc::clone(&self.memory);
            let metrics = self.metrics.clone();
            
            let handle = thread::spawn(move || {
                let thread_id = thread_pattern.thread_id;
                let working_set_base = thread_pattern.working_set_base.unwrap_or(0);
                let working_set_size = thread_pattern.working_set_size.unwrap_or(u64::MAX);
                
                // Repeat pattern if specified
                let repeat_count = thread_pattern.repeat_pattern.unwrap_or(1);
                
                for _repeat in 0..repeat_count {
                    for op in &thread_pattern.operations {
                        let iterations = op.iterations.unwrap_or(1);
                        let mut current_address = working_set_base + op.address.unwrap_or(0);
                        
                        for _iter in 0..iterations {
                            // Execute operation
                            let latency = match op.op_type {
                                OpType::Read => {
                                    let size = op.size.unwrap_or(4096);
                                    // Ensure address is within working set
                                    if current_address + size as u64 > working_set_base + working_set_size {
                                        current_address = working_set_base;
                                    }
                                    memory.execute_read(current_address, size)
                                },
                                OpType::Write => {
                                    let size = op.size.unwrap_or(4096);
                                    // Ensure address is within working set
                                    if current_address + size as u64 > working_set_base + working_set_size {
                                        current_address = working_set_base;
                                    }
                                    memory.execute_write(current_address, size)
                                },
                                OpType::Cpu => {
                                    memory.execute_cpu(op.cpu_cycles.unwrap_or(1000))
                                },
                            };
                            
                            if let Ok(latency) = latency {
                                metrics.record_operation(thread_id, &op, latency);
                            }
                            
                            // Update address with stride
                            if let Some(stride) = op.stride {
                                current_address += stride;
                            }
                            
                            // Think time
                            if let Some(think_time_ns) = op.think_time_ns {
                                thread::sleep(Duration::from_nanos(think_time_ns));
                            }
                        }
                    }
                }
            });
            
            handles.push(handle);
        }
        
        // Wait for all threads
        for handle in handles {
            handle.join().expect("Thread panicked");
        }
        
        let total_duration = start_time.elapsed();
        let mut results = self.metrics.finalize(total_duration);
        results.pattern_name = pattern.name.clone();
        Ok(results)
    }
} 