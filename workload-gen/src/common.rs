use serde::{Deserialize, Serialize};

/// Ultra-simple operation - just describes "what to do"
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "op")]
pub enum Operation {
    #[serde(rename = "read")]
    Read { addr: u64, size: u64, thread: u32 },
    
    #[serde(rename = "write")]
    Write { addr: u64, size: u64, thread: u32 },
    
    #[serde(rename = "cpu")]
    Cpu { cycles: u64, thread: u32 },
    
    #[serde(rename = "gpu")]
    Gpu { kernel: String, thread: u32 },
}

/// Ultra-simple pattern - just a list of operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pattern {
    pub name: String,
    pub operations: Vec<Operation>,
}

/// Address mapping configuration - separate from pattern
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressMap {
    pub memory_regions: Vec<MemoryRegion>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryRegion {
    pub name: String,
    pub base: u64,
    pub size: u64,
    #[serde(rename = "type")]
    pub region_type: RegionType,
    pub device: Option<String>,
    pub numa_node: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RegionType {
    Dram,
    Cxl,
    Gpu,
    Storage,
}

/// Schedule mapping configuration - separate from pattern
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduleMap {
    pub thread_mapping: Vec<ThreadMapping>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreadMapping {
    pub thread: u32,
    pub cpu: Option<u32>,
    pub gpu: Option<u32>,
    pub numa_node: Option<u32>,
}

/// Execution configuration - separate from pattern
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionConfig {
    pub duration_seconds: Option<u64>,
    pub rate_limit: Option<u64>,
    pub warmup_seconds: Option<u64>,
    pub metrics_interval: Option<u64>,
}

/// Workload specification for pattern generation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkloadSpec {
    pub name: String,
    pub workload_type: WorkloadType,
    pub params: std::collections::HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum WorkloadType {
    Sequential,
    Random,
    Hotspot,
    Database,
    Analytics,
    Cache,
    Mixed,
}

/// Runtime statistics
#[derive(Debug, Default, Clone, Serialize)]
pub struct ThreadStats {
    pub thread_id: u32,
    pub operations_completed: u64,
    pub bytes_read: u64,
    pub bytes_written: u64,
    pub cpu_cycles_executed: u64,
    pub total_latency_ns: u64,
    pub min_latency_ns: u64,
    pub max_latency_ns: u64,
}

/// Execution results
#[derive(Debug, Default, Clone, Serialize)]
pub struct ExecutionResults {
    pub pattern_name: String,
    pub total_duration_ns: u64,
    pub total_operations: u64,
    pub total_bytes_read: u64,
    pub total_bytes_written: u64,
    pub total_cpu_cycles: u64,
    pub average_latency_ns: f64,
    pub read_throughput_mbps: f64,
    pub write_throughput_mbps: f64,
    pub operations_per_second: f64,
    pub thread_stats: Vec<ThreadStats>,
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