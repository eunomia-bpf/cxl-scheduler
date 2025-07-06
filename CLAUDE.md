# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a CXL (Compute Express Link) Memory Bandwidth-Aware Scheduler that uses eBPF for kernel-level scheduling to optimize CXL memory access patterns and bandwidth utilization. The project is research-oriented and requires Linux kernel 6.14.0+ with sched_ext support.

## Build Commands

### Main Project Build
```bash
# Install dependencies
make install  # Installs libelf-dev, clang, llvm

# Build source directory
make build
```

### eBPF Scheduler
```bash
cd ebpf/

# Build scheduler variants
make minimal    # Minimal scheduler (recommended for initial testing)
make simple     # Simple scheduler with basic features
make complex    # Complex scheduler (may hit BPF instruction limits)

# Run tests and demos
make test       # Test the scheduler
make demo       # Run bandwidth scheduling demo
make compare    # Performance comparison tests
make stress     # Stress test with multiple processes
```

### Microbenchmarks
```bash
cd microbench/

# Build benchmarks
make all                    # Build all benchmarks
make double_bandwidth       # Advanced bandwidth test with rate limiting
make cxl_memory_test       # Comprehensive CXL memory test

# Run tests
make test       # Basic functionality tests
make quicktest  # Quick 5-second tests
```

### Intel PCM Tools
```bash
cd pcm/
mkdir build && cd build
cmake ..
cmake --build . --parallel  # Build all PCM tools
```

### Workload Generator
```bash
cd workload-gen/
cargo build
cargo test
```

## Architecture Overview

### Core Components

1. **eBPF Scheduler (`/ebpf/`)**
   - Kernel-space eBPF programs that make scheduling decisions
   - User-space controller for configuration and monitoring
   - Token bucket algorithm for bandwidth control
   - Multiple complexity levels (minimal, simple, complex)

2. **Microbenchmarks (`/microbench/`)**
   - Memory bandwidth testing tools
   - CXL-specific memory access patterns
   - NUMA-aware testing capabilities
   - Rate limiting and performance measurement

3. **Performance Monitoring (`/pcm/`)**
   - Intel PCM integration for hardware counters
   - CXL bandwidth and latency monitoring
   - System-wide performance metrics

4. **Workload Generator (`/workload-gen/`)**
   - Rust-based configurable workload generation
   - Orthogonal design with separate pattern generation and execution
   - Support for CPU, GPU, and CXL devices

### Key Technical Concepts

1. **CXL Memory Access**
   - The scheduler optimizes access to CXL memory devices
   - Supports NUMA topology awareness
   - Direct physical memory access through `/dev/mem`
   - Interleaved CXL memory configurations

2. **eBPF Integration**
   - Uses Linux sched_ext for extensible scheduling
   - BPF maps for communication between kernel and user space
   - Task classification based on process names and behavior
   - Real-time bandwidth monitoring and control

3. **Performance Optimization**
   - Token bucket algorithm for bandwidth limiting
   - CPU affinity and thread pinning
   - Memory access pattern optimization
   - Integration with DAMON for memory access monitoring

## Development Guidelines

### Working with eBPF Code
- eBPF programs have strict instruction limits; use minimal version for development
- Changes to BPF structures require rebuilding vmlinux headers
- Use `bpftool` for debugging BPF programs and maps
- Test with `make test` before deploying schedulers

### Memory Access Testing
- Always specify NUMA nodes when testing CXL memory
- Use appropriate memory sizes based on available CXL capacity
- Monitor system memory with `numactl -H` before testing
- Check CXL device status in `/sys/bus/cxl/devices/`

### Performance Measurement
- Use PCM tools for hardware-level monitoring
- Enable performance counters with appropriate permissions
- Consider memory bandwidth saturation points
- Test with various access patterns (sequential, random, strided)

## Common Tasks

### Testing CXL Memory Bandwidth
```bash
# Build and run CXL memory test
cd microbench/
make cxl_memory_test
sudo ./cxl_memory_test -n 2 -s 1G  # Node 2, 1GB test
```

### Running eBPF Scheduler with Workload
```bash
cd ebpf/
make minimal
sudo ./run_scheduler.sh  # Loads scheduler and runs test
```

### Monitoring CXL Performance
```bash
cd pcm/build/
sudo ./pcm-memory  # Monitor memory bandwidth
sudo ./pcm-numa    # NUMA-specific metrics
```

### Debugging eBPF Programs
```bash
# View loaded BPF programs
sudo bpftool prog list

# Inspect BPF maps
sudo bpftool map list
sudo bpftool map dump id <map_id>

# Check kernel logs for BPF errors
sudo dmesg | grep -i bpf
```

## Important Files and Locations

- eBPF scheduler implementation: `ebpf/cxl_pmu.bpf.c`
- Bandwidth controller: `ebpf/cxl_bandwidth_scheduler.c`
- CXL memory test: `microbench/cxl_memory_test.cpp`
- Advanced bandwidth test: `microbench/double_bandwidth.cpp`
- Scheduler configuration: `ebpf/cxl_bandwidth_controller.h`
- Test reports: `ebpf/BANDWIDTH_SCHEDULING_REPORT.md`