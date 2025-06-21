#!/usr/bin/env python3
"""
CXL Double Bandwidth Benchmark Runner and Plotter
Author: CXL Scheduler Team

This script runs the double_bandwidth microbenchmark with various parameters,
optionally monitors system memory bandwidth using Intel PCM, and generates
comprehensive bandwidth plots and analysis.

Features:
- Run bandwidth benchmarks with configurable parameters
- Intel PCM memory monitoring integration
- Real-time bandwidth plotting
- CSV output for further analysis
- Sweep testing across different configurations
- Performance analysis and reporting
"""

import os
import sys
import subprocess
import argparse
import time
import csv
import re
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json

# Import plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd
    import numpy as np
    HAS_PLOTTING = True
except ImportError as e:
    print(f"Warning: Plotting libraries not available: {e}")
    print("Install with: pip install matplotlib pandas numpy")
    HAS_PLOTTING = False

class BenchmarkConfig:
    """Configuration class for benchmark parameters."""
    def __init__(self):
        self.buffer_size = 1024 * 1024 * 1024  # 1GB default
        self.block_size = 4096  # 4KB default
        self.duration = 60  # 60 seconds default
        self.num_threads = 4  # 4 threads default
        self.read_ratio = 0.5  # 50% read ratio default
        self.max_bandwidth = 0  # Unlimited bandwidth
        self.device_path = ""  # Use system memory
        self.use_mmap = False
        self.is_cxl_mem = False
        self.use_pcm = False  # Whether to use PCM monitoring
        self.pcm_path = ""  # Path to PCM executable
        self.output_dir = "results"  # Output directory

class BenchmarkRunner:
    """Main class for running bandwidth benchmarks."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results = []
        self.pcm_process = None
        self.benchmark_executable = self._find_benchmark_executable()
        self.pcm_executable = self._find_pcm_executable()
        
        # Create output directory
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _find_benchmark_executable(self) -> str:
        """Find the double_bandwidth executable."""
        possible_paths = [
            "microbench/double_bandwidth",
            "microbench/build/double_bandwidth",
            "../microbench/double_bandwidth",
            "../microbench/build/double_bandwidth"
        ]
        
        for path in possible_paths:
            full_path = Path(path)
            if full_path.exists() and full_path.is_file():
                return str(full_path.absolute())
        
        raise FileNotFoundError("Could not find double_bandwidth executable. Please build it first.")
    
    def _find_pcm_executable(self) -> Optional[str]:
        """Find the PCM memory executable."""
        possible_paths = [
            "pcm/build/bin/pcm-memory",
            "../pcm/build/bin/pcm-memory",
            "/usr/local/bin/pcm-memory",
            "/usr/bin/pcm-memory"
        ]
        
        for path in possible_paths:
            full_path = Path(path)
            if full_path.exists() and full_path.is_file():
                return str(full_path.absolute())
        
        return None
    
    def _build_benchmark_command(self) -> List[str]:
        """Build the command line for the benchmark."""
        cmd = [self.benchmark_executable]
        
        cmd.extend(["-b", str(self.config.buffer_size)])
        cmd.extend(["-s", str(self.config.block_size)])
        cmd.extend(["-t", str(self.config.num_threads)])
        cmd.extend(["-d", str(self.config.duration)])
        cmd.extend(["-r", str(self.config.read_ratio)])
        
        if self.config.max_bandwidth > 0:
            cmd.extend(["-B", str(self.config.max_bandwidth)])
        
        if self.config.device_path:
            cmd.extend(["-D", self.config.device_path])
        
        if self.config.use_mmap:
            cmd.append("-m")
        
        if self.config.is_cxl_mem:
            cmd.append("-c")
        
        return cmd
    
    def _build_pcm_command(self, benchmark_cmd: List[str]) -> List[str]:
        """Build the PCM command line."""
        if not self.pcm_executable:
            raise RuntimeError("PCM executable not found")
        
        csv_file = os.path.join(self.config.output_dir, f"pcm_output_{int(time.time())}.csv")
        pcm_cmd = [self.pcm_executable, "-csv=" + csv_file, "--"]
        pcm_cmd.extend(benchmark_cmd)
        
        return pcm_cmd, csv_file
    
    def run_single_benchmark(self, test_name: str = "default") -> Dict:
        """Run a single benchmark test."""
        print(f"Running benchmark: {test_name}")
        print(f"Configuration: {self.config.num_threads} threads, "
              f"{self.config.read_ratio:.1f} read ratio, "
              f"{self.config.duration}s duration")
        
        benchmark_cmd = self._build_benchmark_command()
        
        if self.config.use_pcm and self.pcm_executable:
            return self._run_with_pcm(benchmark_cmd, test_name)
        else:
            return self._run_without_pcm(benchmark_cmd, test_name)
    
    def _run_without_pcm(self, benchmark_cmd: List[str], test_name: str) -> Dict:
        """Run benchmark without PCM monitoring."""
        start_time = datetime.now()
        
        try:
            result = subprocess.run(benchmark_cmd, capture_output=True, text=True, timeout=self.config.duration + 30)
            
            if result.returncode != 0:
                print(f"Benchmark failed with return code {result.returncode}")
                print(f"Error: {result.stderr}")
                return {}
            
            # Parse benchmark output
            output = result.stdout
            return self._parse_benchmark_output(output, test_name, start_time)
            
        except subprocess.TimeoutExpired:
            print("Benchmark timed out")
            return {}
        except Exception as e:
            print(f"Error running benchmark: {e}")
            return {}
    
    def _run_with_pcm(self, benchmark_cmd: List[str], test_name: str) -> Dict:
        """Run benchmark with PCM monitoring."""
        pcm_cmd, csv_file = self._build_pcm_command(benchmark_cmd)
        start_time = datetime.now()
        
        try:
            print("Starting PCM monitoring...")
            result = subprocess.run(pcm_cmd, capture_output=True, text=True, timeout=self.config.duration + 60)
            
            if result.returncode != 0:
                print(f"PCM monitoring failed with return code {result.returncode}")
                print(f"Error: {result.stderr}")
                return {}
            
            # Parse both benchmark and PCM outputs
            benchmark_data = self._parse_benchmark_output(result.stdout, test_name, start_time)
            pcm_data = self._parse_pcm_csv(csv_file) if os.path.exists(csv_file) else {}
            
            # Combine results
            combined_data = {**benchmark_data, **pcm_data}
            combined_data['pcm_csv_file'] = csv_file
            
            return combined_data
            
        except subprocess.TimeoutExpired:
            print("PCM monitoring timed out")
            return {}
        except Exception as e:
            print(f"Error running PCM monitoring: {e}")
            return {}
    
    def _parse_benchmark_output(self, output: str, test_name: str, start_time: datetime) -> Dict:
        """Parse benchmark output to extract performance metrics."""
        data = {
            'test_name': test_name,
            'start_time': start_time,
            'config': {
                'threads': self.config.num_threads,
                'read_ratio': self.config.read_ratio,
                'duration': self.config.duration,
                'buffer_size': self.config.buffer_size,
                'block_size': self.config.block_size
            }
        }
        
        # Extract bandwidth values
        read_bw_match = re.search(r'Read bandwidth:\s+([\d.]+)\s+MB/s', output)
        write_bw_match = re.search(r'Write bandwidth:\s+([\d.]+)\s+MB/s', output)
        total_bw_match = re.search(r'Total bandwidth:\s+([\d.]+)\s+MB/s', output)
        
        # Extract IOPS values
        read_iops_match = re.search(r'Read IOPS:\s+([\d.e+]+)\s+ops/s', output)
        write_iops_match = re.search(r'Write IOPS:\s+([\d.e+]+)\s+ops/s', output)
        total_iops_match = re.search(r'Total IOPS:\s+([\d.e+]+)\s+ops/s', output)
        
        if read_bw_match:
            data['read_bandwidth_mbps'] = float(read_bw_match.group(1))
        if write_bw_match:
            data['write_bandwidth_mbps'] = float(write_bw_match.group(1))
        if total_bw_match:
            data['total_bandwidth_mbps'] = float(total_bw_match.group(1))
        
        if read_iops_match:
            data['read_iops'] = float(read_iops_match.group(1))
        if write_iops_match:
            data['write_iops'] = float(write_iops_match.group(1))
        if total_iops_match:
            data['total_iops'] = float(total_iops_match.group(1))
        
        return data
    
    def _parse_pcm_csv(self, csv_file: str) -> Dict:
        """Parse PCM CSV output file."""
        try:
            with open(csv_file, 'r') as f:
                lines = f.readlines()
            
            # Find the data lines (skip header)
            data_lines = []
            for line in lines:
                if line.startswith('2'):  # Data lines start with year
                    data_lines.append(line.strip().split(','))
            
            if not data_lines:
                return {}
            
            # Extract system memory bandwidth (last few columns)
            system_read_values = []
            system_write_values = []
            
            for line in data_lines:
                if len(line) > 48:  # Ensure we have enough columns
                    try:
                        read_bw = float(line[-3])  # System read bandwidth
                        write_bw = float(line[-2])  # System write bandwidth
                        system_read_values.append(read_bw)
                        system_write_values.append(write_bw)
                    except (ValueError, IndexError):
                        continue
            
            if system_read_values and system_write_values:
                return {
                    'pcm_avg_read_bandwidth_mbps': np.mean(system_read_values),
                    'pcm_avg_write_bandwidth_mbps': np.mean(system_write_values),
                    'pcm_avg_total_bandwidth_mbps': np.mean(system_read_values) + np.mean(system_write_values),
                    'pcm_max_read_bandwidth_mbps': np.max(system_read_values),
                    'pcm_max_write_bandwidth_mbps': np.max(system_write_values),
                    'pcm_max_total_bandwidth_mbps': np.max(np.array(system_read_values) + np.array(system_write_values)),
                    'pcm_samples': len(system_read_values)
                }
            
        except Exception as e:
            print(f"Error parsing PCM CSV: {e}")
            return {}
        
        return {}
    
    def run_sweep_test(self, read_ratios: List[float] = None, thread_counts: List[int] = None) -> List[Dict]:
        """Run a sweep test across different configurations."""
        if read_ratios is None:
            read_ratios = [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]
        
        if thread_counts is None:
            thread_counts = [self.config.num_threads]
        
        results = []
        
        for threads in thread_counts:
            original_threads = self.config.num_threads
            self.config.num_threads = threads
            
            for ratio in read_ratios:
                original_ratio = self.config.read_ratio
                self.config.read_ratio = ratio
                
                test_name = f"sweep_t{threads}_r{ratio:.1f}"
                result = self.run_single_benchmark(test_name)
                if result:
                    results.append(result)
                
                self.config.read_ratio = original_ratio
                
                # Brief pause between tests
                time.sleep(2)
            
            self.config.num_threads = original_threads
        
        return results
    
    def save_results(self, results: List[Dict], filename: str = None):
        """Save benchmark results to CSV and JSON files."""
        if not results:
            print("No results to save")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if filename is None:
            csv_filename = f"benchmark_results_{timestamp}.csv"
            json_filename = f"benchmark_results_{timestamp}.json"
        else:
            csv_filename = f"{filename}.csv"
            json_filename = f"{filename}.json"
        
        csv_path = os.path.join(self.config.output_dir, csv_filename)
        json_path = os.path.join(self.config.output_dir, json_filename)
        
        # Save CSV
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = ['test_name', 'threads', 'read_ratio', 'duration', 'buffer_size', 'block_size',
                         'read_bandwidth_mbps', 'write_bandwidth_mbps', 'total_bandwidth_mbps',
                         'read_iops', 'write_iops', 'total_iops']
            
            # Add PCM fields if available
            if any('pcm_avg_read_bandwidth_mbps' in result for result in results):
                fieldnames.extend(['pcm_avg_read_bandwidth_mbps', 'pcm_avg_write_bandwidth_mbps', 
                                 'pcm_avg_total_bandwidth_mbps', 'pcm_max_read_bandwidth_mbps',
                                 'pcm_max_write_bandwidth_mbps', 'pcm_max_total_bandwidth_mbps'])
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = {
                    'test_name': result.get('test_name', ''),
                    'threads': result.get('config', {}).get('threads', 0),
                    'read_ratio': result.get('config', {}).get('read_ratio', 0),
                    'duration': result.get('config', {}).get('duration', 0),
                    'buffer_size': result.get('config', {}).get('buffer_size', 0),
                    'block_size': result.get('config', {}).get('block_size', 0),
                    'read_bandwidth_mbps': result.get('read_bandwidth_mbps', 0),
                    'write_bandwidth_mbps': result.get('write_bandwidth_mbps', 0),
                    'total_bandwidth_mbps': result.get('total_bandwidth_mbps', 0),
                    'read_iops': result.get('read_iops', 0),
                    'write_iops': result.get('write_iops', 0),
                    'total_iops': result.get('total_iops', 0)
                }
                
                # Add PCM data if available
                for key in ['pcm_avg_read_bandwidth_mbps', 'pcm_avg_write_bandwidth_mbps', 
                           'pcm_avg_total_bandwidth_mbps', 'pcm_max_read_bandwidth_mbps',
                           'pcm_max_write_bandwidth_mbps', 'pcm_max_total_bandwidth_mbps']:
                    if key in result:
                        row[key] = result[key]
                
                writer.writerow(row)
        
        # Save JSON
        with open(json_path, 'w') as jsonfile:
            json.dump(results, jsonfile, indent=2, default=str)
        
        print(f"Results saved to:")
        print(f"  CSV: {csv_path}")
        print(f"  JSON: {json_path}")

def create_plots(results: List[Dict], output_dir: str = "results"):
    """Create various plots from benchmark results."""
    if not HAS_PLOTTING:
        print("Plotting libraries not available. Skipping plot generation.")
        return
    
    if not results:
        print("No results to plot")
        return
    
    # Set up plotting style
    plt.style.use('default')
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 10
    
    # Extract data for plotting
    read_ratios = [r.get('config', {}).get('read_ratio', 0) for r in results]
    read_bandwidths = [r.get('read_bandwidth_mbps', 0) for r in results]
    write_bandwidths = [r.get('write_bandwidth_mbps', 0) for r in results]
    total_bandwidths = [r.get('total_bandwidth_mbps', 0) for r in results]
    
    # Plot 1: Bandwidth vs Read Ratio
    plt.figure(figsize=(12, 8))
    plt.subplot(2, 2, 1)
    plt.plot(read_ratios, read_bandwidths, 'b-o', label='Read Bandwidth', linewidth=2, markersize=6)
    plt.plot(read_ratios, write_bandwidths, 'r-s', label='Write Bandwidth', linewidth=2, markersize=6)
    plt.plot(read_ratios, total_bandwidths, 'g-^', label='Total Bandwidth', linewidth=2, markersize=6)
    plt.xlabel('Read Ratio')
    plt.ylabel('Bandwidth (MB/s)')
    plt.title('Bandwidth vs Read Ratio')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: IOPS vs Read Ratio
    plt.subplot(2, 2, 2)
    read_iops = [r.get('read_iops', 0) for r in results]
    write_iops = [r.get('write_iops', 0) for r in results]
    total_iops = [r.get('total_iops', 0) for r in results]
    
    plt.plot(read_ratios, read_iops, 'b-o', label='Read IOPS', linewidth=2, markersize=6)
    plt.plot(read_ratios, write_iops, 'r-s', label='Write IOPS', linewidth=2, markersize=6)
    plt.plot(read_ratios, total_iops, 'g-^', label='Total IOPS', linewidth=2, markersize=6)
    plt.xlabel('Read Ratio')
    plt.ylabel('IOPS')
    plt.title('IOPS vs Read Ratio')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
    
    # Plot 3: PCM vs Benchmark Comparison (if PCM data available)
    plt.subplot(2, 2, 3)
    pcm_total_bw = [r.get('pcm_avg_total_bandwidth_mbps', 0) for r in results]
    if any(pcm_total_bw):
        plt.plot(read_ratios, total_bandwidths, 'g-^', label='Benchmark Total BW', linewidth=2, markersize=6)
        plt.plot(read_ratios, pcm_total_bw, 'm-d', label='PCM Total BW', linewidth=2, markersize=6)
        plt.xlabel('Read Ratio')
        plt.ylabel('Bandwidth (MB/s)')
        plt.title('Benchmark vs PCM Bandwidth')
        plt.legend()
        plt.grid(True, alpha=0.3)
    else:
        plt.text(0.5, 0.5, 'No PCM Data Available', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('PCM Data Not Available')
    
    # Plot 4: Efficiency Analysis
    plt.subplot(2, 2, 4)
    threads = [r.get('config', {}).get('threads', 1) for r in results]
    per_thread_bw = [total_bandwidths[i] / threads[i] if threads[i] > 0 else 0 for i in range(len(results))]
    
    plt.plot(read_ratios, per_thread_bw, 'k-o', label='Bandwidth per Thread', linewidth=2, markersize=6)
    plt.xlabel('Read Ratio')
    plt.ylabel('Bandwidth per Thread (MB/s)')
    plt.title('Threading Efficiency')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_filename = f"bandwidth_analysis_{timestamp}.png"
    plot_path = os.path.join(output_dir, plot_filename)
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"Plot saved to: {plot_path}")

def main():
    parser = argparse.ArgumentParser(description='CXL Double Bandwidth Benchmark Runner')
    
    # Basic benchmark parameters
    parser.add_argument('-b', '--buffer-size', type=int, default=1024*1024*1024,
                       help='Buffer size in bytes (default: 1GB)')
    parser.add_argument('-s', '--block-size', type=int, default=4096,
                       help='Block size in bytes (default: 4KB)')
    parser.add_argument('-t', '--threads', type=int, default=4,
                       help='Number of threads (default: 4)')
    parser.add_argument('-d', '--duration', type=int, default=60,
                       help='Test duration in seconds (default: 60)')
    parser.add_argument('-r', '--read-ratio', type=float, default=0.5,
                       help='Read ratio 0.0-1.0 (default: 0.5)')
    parser.add_argument('-B', '--max-bandwidth', type=int, default=0,
                       help='Max bandwidth in MB/s (default: unlimited)')
    
    # Device options
    parser.add_argument('-D', '--device', type=str, default='',
                       help='Device path for testing')
    parser.add_argument('-m', '--mmap', action='store_true',
                       help='Use mmap instead of read/write')
    parser.add_argument('-c', '--cxl-mem', action='store_true',
                       help='Device is CXL memory')
    
    # PCM monitoring
    parser.add_argument('--pcm', action='store_true',
                       help='Enable PCM memory monitoring')
    
    # Test modes
    parser.add_argument('--sweep', action='store_true',
                       help='Run sweep test across read ratios')
    parser.add_argument('--sweep-ratios', type=str, default='0.0,0.2,0.4,0.5,0.6,0.8,1.0',
                       help='Comma-separated read ratios for sweep test')
    parser.add_argument('--sweep-threads', type=str, default='',
                       help='Comma-separated thread counts for sweep test')
    
    # Output options
    parser.add_argument('-o', '--output-dir', type=str, default='results',
                       help='Output directory (default: results)')
    parser.add_argument('--no-plot', action='store_true',
                       help='Skip plot generation')
    parser.add_argument('--save-name', type=str, default='',
                       help='Custom name for saved results')
    
    args = parser.parse_args()
    
    # Create configuration
    config = BenchmarkConfig()
    config.buffer_size = args.buffer_size
    config.block_size = args.block_size
    config.num_threads = args.threads
    config.duration = args.duration
    config.read_ratio = args.read_ratio
    config.max_bandwidth = args.max_bandwidth
    config.device_path = args.device
    config.use_mmap = args.mmap
    config.is_cxl_mem = args.cxl_mem
    config.use_pcm = args.pcm
    config.output_dir = args.output_dir
    
    # Create benchmark runner
    try:
        runner = BenchmarkRunner(config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please build the benchmark first:")
        print("  cd microbench && make double_bandwidth")
        sys.exit(1)
    
    if args.pcm and not runner.pcm_executable:
        print("Warning: PCM monitoring requested but pcm-memory not found")
        print("PCM monitoring will be disabled")
        config.use_pcm = False
    
    print(f"CXL Double Bandwidth Benchmark Runner")
    print(f"Output directory: {config.output_dir}")
    print(f"PCM monitoring: {'Enabled' if config.use_pcm else 'Disabled'}")
    print()
    
    # Run tests
    if args.sweep:
        print("Running sweep test...")
        read_ratios = [float(x.strip()) for x in args.sweep_ratios.split(',')]
        thread_counts = []
        if args.sweep_threads:
            thread_counts = [int(x.strip()) for x in args.sweep_threads.split(',')]
        else:
            thread_counts = [config.num_threads]
        
        results = runner.run_sweep_test(read_ratios, thread_counts)
    else:
        print("Running single benchmark test...")
        result = runner.run_single_benchmark("single_test")
        results = [result] if result else []
    
    # Save results
    if results:
        filename = args.save_name if args.save_name else None
        runner.save_results(results, filename)
        
        # Generate plots
        if not args.no_plot:
            print("Generating plots...")
            create_plots(results, config.output_dir)
        
        # Print summary
        print("\n=== Test Summary ===")
        for result in results:
            name = result.get('test_name', 'Unknown')
            total_bw = result.get('total_bandwidth_mbps', 0)
            read_bw = result.get('read_bandwidth_mbps', 0)
            write_bw = result.get('write_bandwidth_mbps', 0)
            threads = result.get('config', {}).get('threads', 0)
            read_ratio = result.get('config', {}).get('read_ratio', 0)
            
            print(f"{name}: {total_bw:.1f} MB/s total "
                  f"({read_bw:.1f} read, {write_bw:.1f} write) "
                  f"[{threads}T, {read_ratio:.1f}R]")
    else:
        print("No successful test results")

if __name__ == "__main__":
    main() 