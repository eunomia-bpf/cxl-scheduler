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
}

impl PatternExecutor {
    pub fn new(pattern: &PatternSpec) -> Result<Self> {
        let memory = if let Some(device_path) = &pattern.device_path {
            Arc::new(MemoryManager::new_device_memory(device_path, pattern.memory_size, pattern.use_mmap)?)
        } else {
            Arc::new(MemoryManager::new_system_memory(pattern.memory_size)?)
        };
        
        let metrics = MetricsCollector::new(pattern.num_threads);
        
        Ok(Self { memory, metrics })
    }
    
    pub fn execute(&self, pattern: &PatternSpec) -> Result<ExecutionResults> {
        println!("Executing pattern: {}", pattern.name);
        println!("Operations: {}", pattern.operations.len());
        println!("Threads: {}", pattern.num_threads);
        
        // Group operations by thread
        let mut per_thread_ops: Vec<Vec<Operation>> = vec![Vec::new(); pattern.num_threads];
        for op in &pattern.operations {
            let tid = op.thread_id % pattern.num_threads;
            per_thread_ops[tid].push(op.clone());
        }
        
        // Sort by timestamp
        for ops in &mut per_thread_ops {
            ops.sort_by_key(|op| op.timestamp_ns);
        }
        
        let start_time = Instant::now();
        
        // Spawn worker threads
        let mut handles = Vec::new();
        for thread_id in 0..pattern.num_threads {
            let ops = std::mem::take(&mut per_thread_ops[thread_id]);
            let memory = Arc::clone(&self.memory);
            let metrics = self.metrics.clone();
            
            let handle = thread::spawn(move || {
                let thread_start = Instant::now();
                
                for op in ops {
                    // Wait until it's time for this operation
                    let now_ns = thread_start.elapsed().as_nanos() as u64;
                    if op.timestamp_ns > now_ns {
                        let sleep_ns = op.timestamp_ns - now_ns;
                        thread::sleep(Duration::from_nanos(sleep_ns));
                    }
                    
                    // Execute operation
                    let latency = match op.op_type {
                        OpType::Read => {
                            memory.execute_read(
                                op.address.unwrap_or(0),
                                op.size.unwrap_or(4096)
                            )
                        },
                        OpType::Write => {
                            memory.execute_write(
                                op.address.unwrap_or(0),
                                op.size.unwrap_or(4096)
                            )
                        },
                        OpType::Cpu => {
                            memory.execute_cpu(op.cpu_cycles.unwrap_or(1000))
                        },
                    };
                    
                    if let Ok(latency) = latency {
                        metrics.record_operation(thread_id, &op, latency);
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
        Ok(self.metrics.finalize(total_duration))
    }
} 