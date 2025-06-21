# CXL Workload Generator - Simple & Orthogonal Design

一个用于CXL内存测试的极简工作负载生成器，采用完全正交的设计，各组件职责单一且可独立配置。

## 核心设计理念

### 1. 极简Pattern - 只描述"做什么"

Pattern只包含最基础的操作序列，不包含任何复杂逻辑：

```json
{
  "operations": [
    {"op": "read", "addr": 0, "size": 4096, "thread": 0},
    {"op": "write", "addr": 4096, "size": 4096, "thread": 1},
    {"op": "cpu", "cycles": 10000, "thread": 0},
    {"op": "gpu", "kernel": "gemm", "thread": 2}
  ]
}
```

### 2. 正交组件架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Generator   │ -> │ Pattern     │ -> │ Scheduler   │
│ (生成什么)  │    │ (做什么)    │    │ (在哪里做)  │
└─────────────┘    └─────────────┘    └─────────────┘
                                              |
                                              v
                                      ┌─────────────┐
                                      │ Executor    │
                                      │ (怎么做)    │
                                      └─────────────┘
```

### 3. 组件职责分离

- **Pattern**: 纯粹的操作序列，无任何配置
- **Generator**: 根据高层工作负载生成Pattern
- **Scheduler**: 控制Pattern在哪个CPU/GPU/设备上执行
- **Executor**: 负责实际执行，处理地址映射、设备访问等

## Pattern规范 - 极简设计

### 操作类型

```rust
pub enum Operation {
    Read { addr: u64, size: u64, thread: u32 },
    Write { addr: u64, size: u64, thread: u32 },
    Cpu { cycles: u64, thread: u32 },
    Gpu { kernel: String, thread: u32 },
}
```

### Pattern结构

```rust
pub struct Pattern {
    pub name: String,
    pub operations: Vec<Operation>,
}
```

就这么简单！没有：
- ❌ iterations
- ❌ repeat_pattern  
- ❌ working_set_size
- ❌ think_time
- ❌ stride
- ❌ memory_init
- ❌ 任何配置参数

## 配置分离设计

### 1. 地址映射配置 (AddressMap)

```json
{
  "memory_regions": [
    {"name": "system_mem", "base": 0, "size": "1GB", "type": "dram"},
    {"name": "cxl_mem", "base": "1GB", "size": "2GB", "type": "cxl", "device": "/dev/cxl0"},
    {"name": "gpu_mem", "base": "3GB", "size": "1GB", "type": "gpu", "device": 0}
  ]
}
```

### 2. 调度配置 (ScheduleMap)

```json
{
  "thread_mapping": [
    {"thread": 0, "cpu": 0, "numa_node": 0},
    {"thread": 1, "cpu": 4, "numa_node": 1},
    {"thread": 2, "gpu": 0}
  ]
}
```

### 3. 执行配置 (ExecutionConfig)

```json
{
  "duration_seconds": 60,
  "rate_limit": null,
  "warmup_seconds": 5,
  "metrics_interval": 1000
}
```

## 子命令设计

### 1. generate - 生成Pattern

```bash
# 从高层工作负载生成简单Pattern
workload-gen generate \
  --workload workloads/database.json \
  --output patterns/db_pattern.json

# 生成特定类型的Pattern
workload-gen generate \
  --type sequential \
  --size 1000 \
  --threads 4 \
  --output patterns/seq.json
```

### 2. exec - 执行Pattern

```bash
# 基本执行
workload-gen exec --pattern patterns/simple.json

# 使用地址映射
workload-gen exec \
  --pattern patterns/simple.json \
  --address-map configs/cxl_map.json

# 使用调度配置
workload-gen exec \
  --pattern patterns/simple.json \
  --schedule-map configs/numa_schedule.json \
  --execution-config configs/long_run.json

# 组合使用
workload-gen exec \
  --pattern patterns/complex.json \
  --address-map configs/multi_device.json \
  --schedule-map configs/gpu_schedule.json \
  --execution-config configs/benchmark.json
```

### 3. schedule - 调度分析

```bash
# 分析Pattern的调度需求
workload-gen schedule \
  --pattern patterns/complex.json \
  --analyze

# 生成推荐的调度配置
workload-gen schedule \
  --pattern patterns/complex.json \
  --generate-config \
  --output configs/recommended.json
```

## 设备支持

### 1. 内存设备

```json
{
  "type": "memory",
  "access_method": "mmap|direct|syscall",
  "device_path": "/dev/cxl0",
  "numa_node": 1
}
```

### 2. GPU设备

```json
{
  "type": "gpu",
  "device_id": 0,
  "kernels": {
    "gemm": {"grid": [256, 256], "block": [16, 16]},
    "copy": {"threads": 1024}
  }
}
```

### 3. 存储设备

```json
{
  "type": "storage", 
  "device_path": "/dev/nvme0n1",
  "access_method": "io_uring|aio|sync"
}
```

## 示例Pattern

### 1. 极简读写Pattern

```json
{
  "name": "simple_rw",
  "operations": [
    {"op": "read", "addr": 0, "size": 4096, "thread": 0},
    {"op": "write", "addr": 4096, "size": 4096, "thread": 0},
    {"op": "read", "addr": 8192, "size": 4096, "thread": 1}
  ]
}
```

### 2. 混合计算Pattern

```json
{
  "name": "mixed_compute",
  "operations": [
    {"op": "read", "addr": 0, "size": 1048576, "thread": 0},
    {"op": "cpu", "cycles": 1000000, "thread": 0},
    {"op": "gpu", "kernel": "gemm", "thread": 1},
    {"op": "write", "addr": 1048576, "size": 1048576, "thread": 0}
  ]
}
```

### 3. 多设备Pattern

```json
{
  "name": "multi_device",
  "operations": [
    {"op": "read", "addr": 0, "size": 4096, "thread": 0},
    {"op": "read", "addr": 1073741824, "size": 4096, "thread": 1},
    {"op": "read", "addr": 3221225472, "size": 4096, "thread": 2}
  ]
}
```

## 工作流程

### 1. Pattern生成

```bash
# 生成数据库工作负载Pattern
workload-gen generate \
  --type database \
  --read-ratio 0.9 \
  --block-size 8192 \
  --operations 1000 \
  --threads 4 \
  --output db.json
```

### 2. 配置设备映射

```bash
# 创建地址映射配置
cat > address_map.json << EOF
{
  "memory_regions": [
    {"name": "dram", "base": 0, "size": "1GB", "type": "dram"},
    {"name": "cxl", "base": "1GB", "size": "2GB", "type": "cxl", "device": "/dev/cxl0"}
  ]
}
EOF
```

### 3. 执行测试

```bash
# 执行测试
workload-gen exec \
  --pattern db.json \
  --address-map address_map.json \
  --duration 60 \
  --output results.json
```

## 优势

### 1. 极简Pattern
- Pattern文件小，易于理解和调试
- 可以手工编写简单的测试Pattern
- 便于版本控制和diff

### 2. 完全正交
- Pattern生成与执行完全分离
- 地址映射与Pattern无关
- 调度策略独立配置
- 每个组件可单独测试

### 3. 高度可扩展
- 新设备类型只需扩展地址映射
- 新调度策略只需修改调度器
- Pattern格式永远不变

### 4. 灵活组合
- 同一个Pattern可以在不同设备上执行
- 同一个设备配置可以运行不同Pattern
- 调度策略可以独立优化

### 5. 易于集成
- Pattern可以被其他工具生成
- 执行结果标准化
- 配置文件可以被其他系统使用

这种设计实现了真正的关注点分离，每个组件都有明确的职责，同时保持了最大的灵活性和可扩展性。 