use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;

/// Simple operation types
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum OpType {
    Read,
    Write,
    Cpu,  // CPU computation
}

/// Single memory/cpu operation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Operation {
    /// Operation type
    pub op_type: OpType,
    /// Target address (for memory ops)
    pub address: Option<u64>,
    /// Size in bytes (for memory ops)
    pub size: Option<usize>,
    /// CPU cycles (for CPU ops)
    pub cpu_cycles: Option<u64>,
    /// Thread ID to execute on
    pub thread_id: usize,
    /// Timestamp when to execute (nanoseconds from start)
    pub timestamp_ns: u64,
}

/// Pattern specification - just a list of operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternSpec {
    /// Pattern metadata
    pub name: String,
    pub description: Option<String>,
    
    /// Memory configuration
    pub memory_size: u64,
    pub device_path: Option<String>,
    pub use_mmap: bool,
    
    /// Execution parameters  
    pub duration_ns: u64,
    pub num_threads: usize,
    
    /// The actual operation sequence
    pub operations: Vec<Operation>,
}

/// Runtime statistics
#[derive(Debug, Default, Clone)]
pub struct ThreadStats {
    pub thread_id: usize,
    pub operations_completed: u64,
    pub bytes_read: u64,
    pub bytes_written: u64,
    pub cpu_cycles_executed: u64,
    pub total_latency_ns: u64,
    pub min_latency_ns: u64,
    pub max_latency_ns: u64,
}

/// Execution results
#[derive(Debug, Default, Clone)]
pub struct ExecutionResults {
    pub total_duration_ns: u64,
    pub total_operations: u64,
    pub total_bytes_read: u64,
    pub total_bytes_written: u64,
    pub total_cpu_cycles: u64,
    pub average_latency_ns: f64,
    pub read_throughput_mbps: f64,
    pub write_throughput_mbps: f64,
    pub thread_stats: Vec<ThreadStats>,
}

/// Workload specification (for pattern generation)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkloadSpec {
    pub name: String,
    pub memory_size: String,
    pub duration: u64,
    pub threads: usize,
    pub patterns: Vec<WorkloadPattern>,
}

/// High-level workload pattern description
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkloadPattern {
    pub name: String,
    pub pattern_type: String, // "sequential", "random", "hotspot", etc.
    pub weight: f64,
    pub params: std::collections::HashMap<String, serde_json::Value>,
}

/// Utility functions
pub fn parse_size_string(size_str: &str) -> anyhow::Result<u64> {
    let size_str = size_str.trim().to_uppercase();
    
    if let Some(num_str) = size_str.strip_suffix("GB") {
        let num: f64 = num_str.parse()?;
        Ok((num * 1024.0 * 1024.0 * 1024.0) as u64)
    } else if let Some(num_str) = size_str.strip_suffix("MB") {
        let num: f64 = num_str.parse()?;
        Ok((num * 1024.0 * 1024.0) as u64)
    } else if let Some(num_str) = size_str.strip_suffix("KB") {
        let num: f64 = num_str.parse()?;
        Ok((num * 1024.0) as u64)
    } else if let Some(num_str) = size_str.strip_suffix("B") {
        Ok(num_str.parse()?)
    } else {
        Ok(size_str.parse()?)
    }
}

/// Parse bandwidth strings like "100MB/s"
pub fn parse_bandwidth_string(bw_str: &str) -> anyhow::Result<Option<u64>> {
    if bw_str.trim().to_lowercase() == "unlimited" {
        return Ok(None);
    }
    
    let bw_str = bw_str.trim().to_uppercase().replace("/S", "");
    let bytes_per_sec = parse_size_string(&bw_str)?;
    Ok(Some(bytes_per_sec))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_size_string() {
        assert_eq!(parse_size_string("1GB").unwrap(), 1024 * 1024 * 1024);
        assert_eq!(parse_size_string("100MB").unwrap(), 100 * 1024 * 1024);
        assert_eq!(parse_size_string("4KB").unwrap(), 4 * 1024);
        assert_eq!(parse_size_string("1024").unwrap(), 1024);
    }

    #[test]
    fn test_parse_bandwidth_string() {
        assert_eq!(parse_bandwidth_string("unlimited").unwrap(), None);
        assert_eq!(parse_bandwidth_string("100MB/s").unwrap(), Some(100 * 1024 * 1024));
    }
} 