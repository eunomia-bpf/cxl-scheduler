# CXL Memory Microbenchmarks

This directory contains three C++ microbenchmark programs designed to test CXL (Compute Express Link) memory performance and various memory access patterns.

## Programs Overview

### 1. `double_bandwidth.cpp` - Advanced CXL Bandwidth Benchmark
The most comprehensive benchmark with rate limiting and advanced features.

**Features:**
- Configurable read/write ratio for bidirectional traffic simulation
- Token bucket rate limiter to control bandwidth
- Support for both system memory and device access (via file/device paths)
- Multiple access methods: memory copy, mmap, direct read/write
- Thread-level bandwidth control and statistics
- Thread ID tracking with even/odd assignment for readers/writers

**Key Options:**
- `-r, --read-ratio`: Ratio of readers (0.0-1.0, default: 0.5)
- `-B, --max-bandwidth`: Maximum total bandwidth in MB/s (0=unlimited)
- `-D, --device`: CXL device path for direct device access
- `-m, --mmap`: Use mmap instead of read/write syscalls
- `-c, --cxl-mem`: Indicate the device is CXL memory

### 2. `cxl_memory_test.cpp` - Comprehensive CXL Memory Access Test
The most advanced program supporting multiple CXL memory access modes.

**Features:**
- Multiple memory access modes:
  - `system`: System RAM allocation (CXL integrated as system RAM)
  - `physical`: Direct physical memory access via /dev/mem
  - `numa`: NUMA-aware system memory allocation
  - `interleave`: CXL memory interleave across multiple physical addresses
  - `cxl`: CXL memory via NUMA node allocation
  - `multi`: Multiple CXL buffers on NUMA node
- NUMA topology awareness and node-specific allocation
- Physical address mapping for direct CXL device access
- System information display (RAM, CXL regions, NUMA topology)
- Interleaving across multiple CXL memory windows

**Key Options:**
- `-m, --mode`: Memory access mode (system/physical/numa/interleave/cxl/multi)
- `-a, --address`: Physical address for physical mode (hex)
- `-n, --numa-node`: NUMA node for numa/cxl modes
- `-p, --cxl-addrs`: CXL physical addresses for interleave mode
- `-c, --cxl-nodes`: CXL NUMA nodes (comma-separated)

### 3. `double_bandwidth_thread.cpp` - Simple Bandwidth Benchmark
A simplified version of the bandwidth benchmark without rate limiting.

**Features:**
- Basic read/write ratio configuration
- Support for memory and device access
- Mmap and direct I/O support
- Simple thread-based bandwidth measurement

## Dependencies

- **C++17 compatible compiler** (GCC 7+ or Clang 5+)
- **pthread library** (for multithreading)
- **numa library** (libnuma-dev) - required for `cxl_memory_test.cpp`
- **Root privileges** - required for physical memory access modes

### Installing Dependencies

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install build-essential libnuma-dev
```

#### RHEL/CentOS/Fedora:
```bash
sudo yum install gcc-c++ numactl-devel  # RHEL/CentOS
sudo dnf install gcc-c++ numactl-devel  # Fedora
```

## Building

### Using Make (Recommended):
```bash
make all          # Build all programs
make clean        # Clean build artifacts
make install      # Install to system (requires sudo)
```

### Building Individual Programs:
```bash
make double_bandwidth        # Advanced bandwidth benchmark
make cxl_memory_test        # Comprehensive CXL memory test
make double_bandwidth_thread # Simple bandwidth benchmark
```

### Manual Compilation:
```bash
# Advanced bandwidth benchmark
g++ -std=c++17 -pthread -O3 -Wall -Wextra -o double_bandwidth double_bandwidth.cpp

# CXL memory test (requires numa)
g++ -std=c++17 -pthread -lnuma -O3 -Wall -Wextra -o cxl_memory_test cxl_memory_test.cpp

# Simple bandwidth benchmark
g++ -std=c++17 -pthread -O3 -Wall -Wextra -o double_bandwidth_thread double_bandwidth_thread.cpp
```

## Usage Examples

### 1. System Memory Testing

Test system memory (including CXL memory integrated as system RAM):
```bash
# Basic system memory test
./cxl_memory_test -m system -t 16 -r 0.6 -d 30

# System memory with large buffer
./double_bandwidth -b 10737418240 -t 20 -r 0.7 -d 60
```

### 2. Direct CXL Device Access

Test direct CXL device access (requires root):
```bash
# Direct physical memory access to CXL region
sudo ./cxl_memory_test -m physical -a 0x4080000000 -t 8 -d 30

# Multiple CXL devices interleave
sudo ./cxl_memory_test -m interleave -p 0x2080000000,0x2a5c0000000 -t 16 -d 60
```

### 3. NUMA-Aware Testing

Test CXL memory via NUMA nodes:
```bash
# CXL memory on specific NUMA node
./cxl_memory_test -m cxl -n 2 -t 16 -r 0.6 -d 60

# Multiple CXL buffers simulation
./cxl_memory_test -m multi -n 2 -c 2 -t 16 -r 0.6 -d 60
```

### 4. Bandwidth-Limited Testing

Test with bandwidth controls:
```bash
# Limit total bandwidth to 10 GB/s
./double_bandwidth -B 10240 -t 16 -r 0.5 -d 30

# Test with different read/write ratios
./double_bandwidth -r 0.8 -t 20 -d 60  # 80% reads, 20% writes
```

### 5. Device File Testing

Test with device files or block devices:
```bash
# Test with CXL device file using mmap
./double_bandwidth -D /dev/cxl/mem0 -m -c -t 8 -d 30

# Test with direct I/O
./double_bandwidth -D /dev/cxl/mem0 -t 8 -d 30
```

## Automated Testing

Use the provided shell script for comprehensive bandwidth sweeps:
```bash
chmod +x run_bandwidth_sweep.sh
./run_bandwidth_sweep.sh
```

This will test various read/write ratios and generate detailed results.

## Output Interpretation

### Metrics Reported:
- **Read/Write Bandwidth (MB/s)**: Sustained throughput for each operation type
- **Read/Write IOPS**: Operations per second
- **Total Bandwidth**: Combined read and write throughput
- **Total IOPS**: Combined operations per second

### System Information:
The `cxl_memory_test` program displays:
- Total system RAM
- CXL region sizes and addresses
- NUMA topology and memory distribution
- Available CXL memory windows

## Troubleshooting

### Permission Issues:
```bash
# For physical memory access
sudo ./cxl_memory_test -m physical ...

# For device access
sudo chmod 666 /dev/cxl/mem0  # If needed
```

### Memory Allocation Failures:
- Reduce buffer size with `-b` option
- Check available memory: `free -h`
- Check NUMA memory: `numactl --hardware`

### NUMA Issues:
- Install numactl: `sudo apt-get install numactl`
- Check NUMA topology: `numactl --hardware`
- List NUMA nodes: `ls /sys/devices/system/node/`

### CXL Device Issues:
- Check CXL devices: `ls /dev/cxl/`
- Check CXL regions: `cat /proc/iomem | grep -i cxl`
- Verify CXL kernel support: `dmesg | grep -i cxl`

## Performance Tips

1. **Thread Count**: Set threads to 2x CPU cores for optimal performance
2. **Buffer Size**: Use large buffers (>1GB) for sustained bandwidth testing
3. **Block Size**: 4KB-64KB block sizes typically show best performance
4. **NUMA Affinity**: Use `numactl` to bind processes to specific NUMA nodes
5. **CPU Isolation**: Use `isolcpus` kernel parameter for dedicated benchmark cores

## Advanced Configuration

### Environment Variables:
```bash
export CXL_BENCHMARK_THREADS=32    # Default thread count
export CXL_BENCHMARK_DURATION=120  # Default test duration
```

### Kernel Parameters:
```bash
# For better performance
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo 1 > /sys/kernel/mm/numa_balancing
```

## Contributing

When adding new features:
1. Update the appropriate program's help text
2. Add corresponding command-line options
3. Update this README with new usage examples
4. Test with various CXL configurations

## License

These microbenchmarks are part of the CXL scheduler research project. 