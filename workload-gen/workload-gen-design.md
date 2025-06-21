# CXL Workload Generator Design Document

## Overview

The CXL Workload Generator is a flexible, low-level memory access pattern generator designed to simulate realistic workloads for CXL memory testing. Unlike high-level workload simulators, this tool focuses on raw memory operations (read/write) at specific addresses, allowing precise control over memory access patterns.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Pattern Spec    │ -> │ Pattern Generator│ -> │ Operation Queue │
│ (JSON)          │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         |
┌─────────────────┐    ┌──────────────────┐             |
│ Metrics         │ <- │ Thread Scheduler │ <-----------┘
│ Collector       │    │ & Executor       │
└─────────────────┘    └──────────────────┘
```

## Core Components

### 1. Pattern Generator (`PatternGenerator`)
**Responsibility**: Generate sequences of memory operations based on pattern specifications.

**Input**: Pattern specification (JSON)
**Output**: Stream of `MemoryOperation` objects

```cpp
struct MemoryOperation {
    uint64_t address;        // Target memory address (offset from base)
    OperationType op_type;   // READ or WRITE
    size_t size;            // Operation size in bytes
    uint64_t timestamp_ns;   // When to execute (relative to start)
    int thread_id;          // Which thread should execute
    void* data;             // Data to write (for WRITE ops)
};
```

**Supported Patterns**:
- Sequential: Linear address progression
- Random: Uniform random address distribution
- Strided: Fixed stride access pattern
- Hotspot: 80/20 hot/cold data distribution
- Zipfian: Zipf distribution for realistic locality
- Custom: User-defined address sequences

### 2. Thread Scheduler (`ThreadScheduler`)
**Responsibility**: Execute memory operations on appropriate threads with precise timing.

**Features**:
- Thread pool management
- NUMA-aware thread placement
- CPU affinity control
- Timeline-based operation scheduling
- Rate limiting and throttling
- Load balancing across threads

### 3. Memory Manager (`MemoryManager`)
**Responsibility**: Handle memory allocation and address mapping.

**Capabilities**:
- CXL device memory mapping
- System memory allocation
- Address space management
- Memory pattern initialization
- NUMA node allocation control

### 4. Metrics Collector (`MetricsCollector`)
**Responsibility**: Collect detailed performance metrics during execution.

**Metrics**:
- Per-thread latency histograms
- Bandwidth utilization over time
- Operation completion rates
- Cache miss/hit simulation
- Memory access locality statistics

## Pattern Specification Format

### JSON Structure
```json
{
  "workload_name": "mixed_access_pattern",
  "memory_config": {
    "total_size": "4GB",
    "base_address": 0,
    "initialization": "random"
  },
  "execution_config": {
    "duration": 60,
    "num_threads": 8,
    "thread_affinity": "numa_local"
  },
  "patterns": [
    {
      "name": "sequential_read",
      "type": "sequential",
      "weight": 0.3,
      "params": {
        "operation": "read",
        "start_address": 0,
        "end_address": "1GB",
        "block_size": 4096,
        "stride": 4096
      }
    },
    {
      "name": "random_write",
      "type": "random",
      "weight": 0.2,
      "params": {
        "operation": "write",
        "address_range": ["1GB", "2GB"],
        "block_sizes": [64, 256, 1024, 4096],
        "block_size_weights": [0.1, 0.2, 0.3, 0.4]
      }
    },
    {
      "name": "hotspot_mixed",
      "type": "hotspot",
      "weight": 0.5,
      "params": {
        "hot_region_size": "200MB",
        "hot_region_ratio": 0.8,
        "read_write_ratio": 0.7,
        "block_size": 4096
      }
    }
  ],
  "phases": [
    {
      "name": "warmup",
      "duration": 10,
      "rate_limit": "100MB/s",
      "active_patterns": ["sequential_read"]
    },
    {
      "name": "steady_state",
      "duration": 40,
      "rate_limit": "unlimited",
      "active_patterns": ["sequential_read", "random_write", "hotspot_mixed"]
    },
    {
      "name": "burst",
      "duration": 10,
      "rate_limit": "unlimited",
      "thread_multiplier": 2,
      "active_patterns": ["hotspot_mixed"]
    }
  ]
}
```

## Implementation Details

### Directory Structure
```
workload-gen/
├── include/
│   ├── pattern_generator.h
│   ├── thread_scheduler.h
│   ├── memory_manager.h
│   ├── metrics_collector.h
│   └── common.h
├── src/
│   ├── pattern_generator.cpp
│   ├── thread_scheduler.cpp
│   ├── memory_manager.cpp
│   ├── metrics_collector.cpp
│   └── main.cpp
├── patterns/
│   ├── example_sequential.json
│   ├── example_random.json
│   ├── example_hotspot.json
│   └── example_mixed.json
├── CMakeLists.txt
└── README.md
```

### Key Classes

#### PatternGenerator
```cpp
class PatternGenerator {
public:
    PatternGenerator(const PatternSpec& spec);
    
    // Generate operation sequence for entire workload
    std::vector<MemoryOperation> generateOperations();
    
    // Generate operations for specific phase
    std::vector<MemoryOperation> generatePhaseOperations(
        const PhaseSpec& phase, uint64_t start_time_ns);
        
private:
    std::unique_ptr<SequentialPattern> sequential_gen_;
    std::unique_ptr<RandomPattern> random_gen_;
    std::unique_ptr<HotspotPattern> hotspot_gen_;
    std::unique_ptr<ZipfianPattern> zipfian_gen_;
};
```

#### ThreadScheduler
```cpp
class ThreadScheduler {
public:
    ThreadScheduler(int num_threads, const ExecutionConfig& config);
    
    // Execute all operations according to timeline
    void executeWorkload(const std::vector<MemoryOperation>& operations);
    
    // Set CPU affinity and NUMA placement
    void configureThreadAffinity();
    
private:
    std::vector<std::thread> worker_threads_;
    std::vector<std::queue<MemoryOperation>> thread_queues_;
    ThreadPool thread_pool_;
};
```

#### MemoryManager
```cpp
class MemoryManager {
public:
    MemoryManager(const MemoryConfig& config);
    
    // Allocate and initialize memory region
    void* allocateMemory(size_t size, int numa_node = -1);
    
    // Map CXL device memory
    void* mapCXLDevice(const std::string& device_path, size_t size);
    
    // Perform actual memory operation
    void executeOperation(const MemoryOperation& op);
    
private:
    void* base_address_;
    size_t total_size_;
    std::vector<void*> memory_regions_;
};
```

## Usage Examples

### Basic Sequential Access
```bash
./workload-gen --pattern patterns/sequential.json --duration 30 --threads 4
```

### Complex Multi-Phase Workload
```bash
./workload-gen --pattern patterns/mixed_realistic.json --output metrics.csv
```

### CXL Device Testing
```bash
./workload-gen --pattern patterns/hotspot.json --device /dev/cxl/mem0 --mmap
```

## Advanced Features

### 1. Timeline-Based Execution
- Operations scheduled with nanosecond precision
- Support for bursty traffic patterns
- Realistic think time simulation

### 2. NUMA Awareness
- Thread placement on specific NUMA nodes
- Memory allocation from target NUMA domains
- Cross-NUMA access pattern simulation

### 3. Rate Limiting
- Token bucket algorithm for bandwidth control
- Per-thread and global rate limits
- Dynamic rate adjustment during execution

### 4. Extensible Pattern System
- Plugin architecture for custom patterns
- Scripting support for complex sequences
- Mathematical function-based generators

## Performance Considerations

1. **Lock-free operation queues** for minimal scheduling overhead
2. **Pre-generated operation sequences** to avoid runtime pattern generation
3. **Memory prefetching** simulation for realistic cache behavior
4. **Efficient metrics collection** with minimal timing impact

## Testing Strategy

1. **Unit tests** for each pattern generator
2. **Integration tests** for end-to-end workload execution
3. **Performance validation** against known memory benchmarks
4. **Pattern verification** to ensure generated addresses match specifications

## Future Enhancements

1. **Dynamic pattern adjustment** based on runtime feedback
2. **Machine learning-based** realistic pattern generation
3. **Network-attached memory** simulation
4. **Multi-node workload** coordination
5. **Real application trace replay**

---

This design provides a foundation for a flexible, precise, and realistic memory access pattern generator specifically designed for CXL memory testing and evaluation. 