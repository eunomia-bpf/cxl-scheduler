# CXL Workload Generator

一个用于CXL内存测试的灵活工作负载生成器，采用解耦设计，将模式生成和执行彻底分离。

## 架构设计

### 核心理念

本工具采用**完全解耦**的设计，将工作负载定义、模式生成和执行分离：

```
Workload Spec → Pattern Generator → Pattern Spec → Pattern Executor
     ↓               ↓                  ↓              ↓
   高层描述        生成工具          操作序列        执行引擎
```

### 组件架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Workload Spec   │ -> │ Pattern Generator│ -> │ Pattern Spec    │
│ (高层工作负载)  │    │ (独立工具)      │    │ (操作序列)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         |
                                                         v
                                                ┌─────────────────┐
                                                │ Pattern Executor│
                                                │ (执行引擎)      │
                                                └─────────────────┘
```

## 核心概念

### 1. Pattern Specification (模式规范)

Pattern Spec是简单的操作序列描述，包含：

- **操作类型**: `Read`, `Write`, `Cpu`
- **内存地址**: 目标地址（仅内存操作）
- **大小**: 字节数（仅内存操作）
- **CPU周期**: 计算量（仅CPU操作）
- **线程ID**: 执行线程
- **时间戳**: 执行时机（纳秒）

### 2. 操作类型

```rust
pub enum OpType {
    Read,   // 内存读取
    Write,  // 内存写入
    Cpu,    // CPU计算
}
```

### 3. 操作结构

```rust
pub struct Operation {
    pub op_type: OpType,
    pub address: Option<u64>,      // 内存地址
    pub size: Option<usize>,       // 操作大小
    pub cpu_cycles: Option<u64>,   // CPU周期
    pub thread_id: usize,          // 线程ID
    pub timestamp_ns: u64,         // 时间戳
}
```

## 使用方式

### 1. 执行现有Pattern

```bash
# 基本用法
./workload-gen --pattern patterns/simple_read.json

# 使用CXL设备
./workload-gen --pattern patterns/simple_read.json --device /dev/cxl/mem0

# 使用mmap访问设备
./workload-gen --pattern patterns/simple_read.json --device /dev/cxl/mem0 --mmap

# 详细输出
./workload-gen --pattern patterns/simple_read.json --verbose
```

### 2. Pattern示例

简单的混合访问模式：

```json
{
  "name": "simple_mixed_pattern",
  "description": "Mixed read/write/cpu operations",
  "memory_size": 1048576,
  "device_path": null,
  "use_mmap": false,
  "duration_ns": 5000000000,
  "num_threads": 2,
  "operations": [
    {
      "op_type": "Read",
      "address": 0,
      "size": 4096,
      "cpu_cycles": null,
      "thread_id": 0,
      "timestamp_ns": 0
    },
    {
      "op_type": "Write",
      "address": 4096,
      "size": 4096, 
      "cpu_cycles": null,
      "thread_id": 1,
      "timestamp_ns": 1000000
    },
    {
      "op_type": "Cpu",
      "address": null,
      "size": null,
      "cpu_cycles": 10000,
      "thread_id": 0,
      "timestamp_ns": 2000000
    }
  ]
}
```

## 优势特性

### 1. 完全解耦

- **Pattern生成** 与 **Pattern执行** 完全分离
- 可以使用任何工具生成Pattern Spec
- 执行器只负责按照规范执行操作

### 2. 精确控制

- **纳秒级时间控制**: 每个操作都有精确的时间戳
- **线程级调度**: 明确指定每个操作的执行线程
- **地址级控制**: 精确指定内存访问地址

### 3. 灵活扩展

- **多种操作类型**: 支持内存读写和CPU计算
- **设备无关**: 支持系统内存和CXL设备
- **访问方式**: 支持mmap和read/write两种访问方式

### 4. 详细指标

- **每线程统计**: 详细的每线程性能数据
- **操作类型分离**: 读写分离的吞吐量统计
- **延迟分析**: 最小/最大/平均延迟

## 目录结构

```
workload-gen/
├── src/
│   ├── common.rs     # 通用类型定义
│   ├── executor.rs   # Pattern执行器
│   ├── lib.rs        # 库入口
│   └── main.rs       # 可执行文件
├── patterns/         # Pattern示例
│   ├── simple_read.json
│   └── example_*.json
├── Cargo.toml        # Rust项目配置
└── README.md         # 本文档
```

## 构建和安装

```bash
# 编译
cargo build --release

# 运行测试
cargo test

# 安装
cargo install --path .
```

## 扩展开发

### 1. Pattern生成器

可以创建独立的Pattern生成工具，从高层工作负载描述生成Pattern Spec：

```rust
// 示例：从工作负载规范生成Pattern
fn generate_pattern(workload: &WorkloadSpec) -> PatternSpec {
    // 实现具体的生成逻辑
    // 例如：sequential, random, hotspot等模式
}
```

### 2. 新操作类型

轻松添加新的操作类型：

```rust
pub enum OpType {
    Read,
    Write,  
    Cpu,
    // 新增操作类型
    Network,    // 网络操作
    Disk,       // 磁盘操作
    Custom(String), // 自定义操作
}
```

### 3. 高级调度

可以扩展执行器支持：

- **NUMA感知调度**
- **CPU亲和性控制**
- **优先级调度**
- **动态负载均衡**

## 性能特性

- **低开销**: 最小化执行器开销，专注于精确测试
- **高精度**: 纳秒级时间控制
- **可扩展**: 支持多线程并发执行
- **内存安全**: 使用Rust的内存安全特性

## 使用场景

1. **CXL设备性能测试**: 测试CXL内存的带宽和延迟
2. **内存访问模式验证**: 验证不同访问模式的性能特征
3. **多线程负载测试**: 测试并发访问的性能表现
4. **调度算法验证**: 验证内存调度算法的效果

## 示例输出

```
=== Execution Results ===
Pattern: simple_sequential_read
Duration: 5.001 s
Operations: 1000
Average Latency: 245.67 ns
Read: 4096000 bytes, 0.82 MB/s
Write: 2048000 bytes, 0.41 MB/s
CPU cycles: 50000

=== Per-Thread Stats ===
Thread 0: 600 ops, avg 234.12 ns
Thread 1: 400 ops, avg 262.45 ns
```

这个架构实现了工作负载生成和执行的完全解耦，为CXL内存测试提供了灵活、精确、可扩展的工具基础。 