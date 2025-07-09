#!/usr/bin/env python3
"""
Benchmark visualization script for double_bandwidth
Runs the benchmark with varying thread numbers and read ratios
"""

import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import json
import os
import re
from datetime import datetime
import time

# Configuration
# Test 1: Fixed thread count (1000), varying read ratios
TEST1_THREADS = 1000
TEST1_READ_RATIOS = np.arange(0.05, 1.0, 0.05)  # 0.05 to 0.95

# Test 2: Fixed read ratio (0.5), varying thread counts
TEST2_THREAD_NUMBERS = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1000]
TEST2_READ_RATIO = 0.5

DURATION = 5  # seconds per test
BLOCK_SIZE = 64  # 64B
BUFFER_SIZE = 8*1024*1024*1024  # 8GB
DEVICE = ""  # Empty for mmap mode
USE_MMAP = True  # Use memory mapping instead of device access

# Output directories
RESULTS_DIR = "benchmark_results"
FIGURES_DIR = "figures"

def ensure_dirs():
    """Create necessary directories"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

def run_benchmark(num_threads, read_ratio):
    """Run double_bandwidth with specific parameters"""
    cmd = [
        "./double_bandwidth",
        "-t", str(num_threads),
        "-r", f"{read_ratio:.2f}",
        "-d", str(DURATION),
        "-s", str(BLOCK_SIZE),
        "-b", str(BUFFER_SIZE),
        "-N", "1"
    ]
    
    if USE_MMAP:
        cmd.append("-m")
    elif DEVICE:
        cmd.extend(["-D", DEVICE])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DURATION+30)
        if result.returncode != 0:
            print(f"Error running benchmark: {result.stderr}")
            return None
        
        # Parse output
        output = result.stdout
        metrics = {}
        
        # Extract metrics using regex
        patterns = {
            'read_bandwidth': r'Read bandwidth: ([\d.]+) MB/s',
            'write_bandwidth': r'Write bandwidth: ([\d.]+) MB/s',
            'total_bandwidth': r'Total bandwidth: ([\d.]+) MB/s',
            'read_iops': r'Read IOPS: ([\d.]+) ops/s',
            'write_iops': r'Write IOPS: ([\d.]+) ops/s',
            'total_iops': r'Total IOPS: ([\d.]+) ops/s'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                metrics[key] = float(match.group(1))
            else:
                metrics[key] = 0.0
        
        return metrics
        
    except subprocess.TimeoutExpired:
        print(f"Timeout for threads={num_threads}, read_ratio={read_ratio}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def collect_data(test_num):
    """Run benchmark for specified test"""
    results = []
    
    if test_num == 1:
        # Test 1: Fixed thread count, varying read ratios
        total_runs = len(TEST1_READ_RATIOS)
        print(f"\nTest 1: Fixed thread count ({TEST1_THREADS}), varying read ratios")
        
        with tqdm(total=total_runs, desc="Running Test 1") as pbar:
            for read_ratio in TEST1_READ_RATIOS:
                pbar.set_description(f"Threads: {TEST1_THREADS}, Read ratio: {read_ratio:.2f}")
                
                metrics = run_benchmark(TEST1_THREADS, read_ratio)
                
                if metrics:
                    result = {
                        'threads': TEST1_THREADS,
                        'read_ratio': read_ratio,
                        **metrics
                    }
                    results.append(result)
                    
                    # Save intermediate results
                    pd.DataFrame(results).to_csv(
                        os.path.join(RESULTS_DIR, f'test1_intermediate_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'),
                        index=False
                    )
                
                pbar.update(1)
                time.sleep(1)  # Brief pause between tests
    
    elif test_num == 2:
        # Test 2: Fixed read ratio, varying thread counts
        total_runs = len(TEST2_THREAD_NUMBERS)
        print(f"\nTest 2: Fixed read ratio ({TEST2_READ_RATIO}), varying thread counts")
        
        with tqdm(total=total_runs, desc="Running Test 2") as pbar:
            for num_threads in TEST2_THREAD_NUMBERS:
                pbar.set_description(f"Threads: {num_threads}, Read ratio: {TEST2_READ_RATIO}")
                
                metrics = run_benchmark(num_threads, TEST2_READ_RATIO)
                
                if metrics:
                    result = {
                        'threads': num_threads,
                        'read_ratio': TEST2_READ_RATIO,
                        **metrics
                    }
                    results.append(result)
                    
                    # Save intermediate results
                    pd.DataFrame(results).to_csv(
                        os.path.join(RESULTS_DIR, f'test2_intermediate_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'),
                        index=False
                    )
                
                pbar.update(1)
                time.sleep(1)  # Brief pause between tests
    
    return pd.DataFrame(results)

def create_test1_figures(df):
    """Create visualization figures for Test 1 (fixed threads, varying read ratio)"""
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 12
    
    # 1. Line plot of bandwidth vs read ratio
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df['read_ratio'], df['total_bandwidth'], 'o-', linewidth=2, markersize=8, label='Total')
    ax.plot(df['read_ratio'], df['read_bandwidth'], 's-', linewidth=2, markersize=6, label='Read')
    ax.plot(df['read_ratio'], df['write_bandwidth'], '^-', linewidth=2, markersize=6, label='Write')
    ax.set_xlabel('Read Ratio')
    ax.set_ylabel('Bandwidth (MB/s)')
    ax.set_title(f'Bandwidth vs Read Ratio (Threads = {TEST1_THREADS})')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'test1_bandwidth_vs_read_ratio.png'), dpi=300)
    plt.close()
    
    # 2. IOPS plot
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df['read_ratio'], df['total_iops'], 'o-', linewidth=2, markersize=8, label='Total IOPS')
    ax.plot(df['read_ratio'], df['read_iops'], 's-', linewidth=2, markersize=6, label='Read IOPS')
    ax.plot(df['read_ratio'], df['write_iops'], '^-', linewidth=2, markersize=6, label='Write IOPS')
    ax.set_xlabel('Read Ratio')
    ax.set_ylabel('IOPS')
    ax.set_title(f'IOPS vs Read Ratio (Threads = {TEST1_THREADS})')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'test1_iops_vs_read_ratio.png'), dpi=300)
    plt.close()
    
    # 3. Stacked area plot
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.fill_between(df['read_ratio'], 0, df['read_bandwidth'], alpha=0.7, label='Read Bandwidth')
    ax.fill_between(df['read_ratio'], df['read_bandwidth'], df['total_bandwidth'], alpha=0.7, label='Write Bandwidth')
    ax.set_xlabel('Read Ratio')
    ax.set_ylabel('Bandwidth (MB/s)')
    ax.set_title(f'Read/Write Bandwidth Distribution (Threads = {TEST1_THREADS})')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'test1_bandwidth_stacked.png'), dpi=300)
    plt.close()

def create_test2_figures(df):
    """Create visualization figures for Test 2 (fixed read ratio, varying threads)"""
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 12
    
    # 1. Line plot of bandwidth vs threads
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df['threads'], df['total_bandwidth'], 'o-', linewidth=2, markersize=8, label='Total')
    ax.plot(df['threads'], df['read_bandwidth'], 's-', linewidth=2, markersize=6, label='Read')
    ax.plot(df['threads'], df['write_bandwidth'], '^-', linewidth=2, markersize=6, label='Write')
    ax.set_xlabel('Number of Threads')
    ax.set_ylabel('Bandwidth (MB/s)')
    ax.set_title(f'Bandwidth Scaling with Thread Count (Read Ratio = {TEST2_READ_RATIO})')
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'test2_bandwidth_vs_threads.png'), dpi=300)
    plt.close()
    
    # 2. Efficiency plot
    df['bandwidth_per_thread'] = df['total_bandwidth'] / df['threads']
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df['threads'], df['bandwidth_per_thread'], 'o-', linewidth=2, markersize=8)
    ax.set_xlabel('Number of Threads')
    ax.set_ylabel('Bandwidth per Thread (MB/s)')
    ax.set_title(f'Bandwidth Efficiency (Read Ratio = {TEST2_READ_RATIO})')
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'test2_bandwidth_efficiency.png'), dpi=300)
    plt.close()
    
    # 3. IOPS scaling
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(df['threads'], df['total_iops'], 'o-', linewidth=2, markersize=8, label='Total IOPS')
    ax.plot(df['threads'], df['read_iops'], 's-', linewidth=2, markersize=6, label='Read IOPS')
    ax.plot(df['threads'], df['write_iops'], '^-', linewidth=2, markersize=6, label='Write IOPS')
    ax.set_xlabel('Number of Threads')
    ax.set_ylabel('IOPS')
    ax.set_title(f'IOPS Scaling with Thread Count (Read Ratio = {TEST2_READ_RATIO})')
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'test2_iops_vs_threads.png'), dpi=300)
    plt.close()
    
    # 4. Scalability plot (normalized)
    fig, ax = plt.subplots(figsize=(12, 8))
    baseline_bw = df[df['threads'] == df['threads'].min()]['total_bandwidth'].values[0]
    df['speedup'] = df['total_bandwidth'] / baseline_bw
    df['ideal_speedup'] = df['threads'] / df['threads'].min()
    
    ax.plot(df['threads'], df['speedup'], 'o-', linewidth=2, markersize=8, label='Actual Speedup')
    ax.plot(df['threads'], df['ideal_speedup'], '--', linewidth=2, alpha=0.7, label='Ideal Linear Speedup')
    ax.set_xlabel('Number of Threads')
    ax.set_ylabel('Speedup')
    ax.set_title(f'Scalability Analysis (Read Ratio = {TEST2_READ_RATIO})')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'test2_scalability.png'), dpi=300)
    plt.close()

def create_figures(df):
    """Create various visualization figures"""
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 12
    
    # 1. Heatmap of total bandwidth
    fig, ax = plt.subplots(figsize=(14, 10))
    pivot_data = df.pivot(index='threads', columns='read_ratio', values='total_bandwidth')
    sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='YlOrRd', 
                cbar_kws={'label': 'Total Bandwidth (MB/s)'})
    plt.title('Total Bandwidth vs Thread Count and Read Ratio')
    plt.xlabel('Read Ratio')
    plt.ylabel('Number of Threads')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'bandwidth_heatmap.png'), dpi=300)
    plt.close()
    
    # 2. Line plot of bandwidth vs threads for different read ratios
    fig, ax = plt.subplots(figsize=(12, 8))
    selected_ratios = [0.1, 0.3, 0.5, 0.7, 0.9]
    for ratio in selected_ratios:
        data = df[df['read_ratio'].round(2).isin([ratio])]
        if not data.empty:
            plt.plot(data['threads'], data['total_bandwidth'], 
                    marker='o', label=f'Read ratio: {ratio}', linewidth=2)
    
    plt.xlabel('Number of Threads')
    plt.ylabel('Total Bandwidth (MB/s)')
    plt.title('Bandwidth Scaling with Thread Count')
    plt.xscale('log')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'bandwidth_vs_threads.png'), dpi=300)
    plt.close()
    
    # 3. Read vs Write bandwidth comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Read bandwidth heatmap
    pivot_read = df.pivot(index='threads', columns='read_ratio', values='read_bandwidth')
    sns.heatmap(pivot_read, annot=True, fmt='.0f', cmap='Blues', 
                cbar_kws={'label': 'Read Bandwidth (MB/s)'}, ax=ax1)
    ax1.set_title('Read Bandwidth')
    ax1.set_xlabel('Read Ratio')
    ax1.set_ylabel('Number of Threads')
    
    # Write bandwidth heatmap
    pivot_write = df.pivot(index='threads', columns='read_ratio', values='write_bandwidth')
    sns.heatmap(pivot_write, annot=True, fmt='.0f', cmap='Greens', 
                cbar_kws={'label': 'Write Bandwidth (MB/s)'}, ax=ax2)
    ax2.set_title('Write Bandwidth')
    ax2.set_xlabel('Read Ratio')
    ax2.set_ylabel('Number of Threads')
    
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'read_write_bandwidth_comparison.png'), dpi=300)
    plt.close()
    
    # 4. 3D surface plot
    from mpl_toolkits.mplot3d import Axes3D
    
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Prepare data for 3D plot
    threads_unique = sorted(df['threads'].unique())
    ratios_unique = sorted(df['read_ratio'].unique())
    X, Y = np.meshgrid(ratios_unique, threads_unique)
    Z = pivot_data.values
    
    surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)
    ax.set_xlabel('Read Ratio')
    ax.set_ylabel('Number of Threads')
    ax.set_zlabel('Total Bandwidth (MB/s)')
    ax.set_title('3D Bandwidth Surface')
    fig.colorbar(surf)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'bandwidth_3d_surface.png'), dpi=300)
    plt.close()
    
    # 5. Efficiency plot (bandwidth per thread)
    df['bandwidth_per_thread'] = df['total_bandwidth'] / df['threads']
    
    fig, ax = plt.subplots(figsize=(12, 8))
    pivot_efficiency = df.pivot(index='threads', columns='read_ratio', values='bandwidth_per_thread')
    sns.heatmap(pivot_efficiency, annot=True, fmt='.1f', cmap='coolwarm', 
                cbar_kws={'label': 'Bandwidth per Thread (MB/s)'})
    plt.title('Bandwidth Efficiency (per Thread)')
    plt.xlabel('Read Ratio')
    plt.ylabel('Number of Threads')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'bandwidth_efficiency.png'), dpi=300)
    plt.close()
    
    # 6. IOPS comparison
    fig, ax = plt.subplots(figsize=(12, 8))
    pivot_iops = df.pivot(index='threads', columns='read_ratio', values='total_iops')
    sns.heatmap(pivot_iops, annot=True, fmt='.0f', cmap='plasma', 
                cbar_kws={'label': 'Total IOPS'})
    plt.title('Total IOPS vs Thread Count and Read Ratio')
    plt.xlabel('Read Ratio')
    plt.ylabel('Number of Threads')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'iops_heatmap.png'), dpi=300)
    plt.close()
    
    # 7. Contour plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Prepare data for contour plot
    threads_unique = sorted(df['threads'].unique())
    ratios_unique = sorted(df['read_ratio'].unique())
    
    # Check if we have enough data points for a contour plot
    if len(threads_unique) >= 2 and len(ratios_unique) >= 2:
        X_contour, Y_contour = np.meshgrid(ratios_unique, threads_unique)
        Z_contour = pivot_data.values
        
        contour = ax.contourf(X_contour, Y_contour, Z_contour, levels=20, cmap='viridis')
        contour_lines = ax.contour(X_contour, Y_contour, Z_contour, levels=10, colors='black', alpha=0.4, linewidths=0.5)
        ax.clabel(contour_lines, inline=True, fontsize=8)
        fig.colorbar(contour, label='Total Bandwidth (MB/s)')
        ax.set_xlabel('Read Ratio')
        ax.set_ylabel('Number of Threads')
        ax.set_yscale('log')
        ax.set_title('Bandwidth Contour Plot')
    else:
        # If not enough data for contour, create a line plot instead
        if len(threads_unique) == 1:
            ax.plot(df['read_ratio'], df['total_bandwidth'], 'o-', linewidth=2, markersize=8)
            ax.set_xlabel('Read Ratio')
            ax.set_ylabel('Total Bandwidth (MB/s)')
            ax.set_title(f'Bandwidth vs Read Ratio (Threads = {threads_unique[0]})')
            ax.grid(True, alpha=0.3)
        else:
            # Single read ratio with multiple threads
            ax.plot(df['threads'], df['total_bandwidth'], 'o-', linewidth=2, markersize=8)
            ax.set_xlabel('Number of Threads')
            ax.set_ylabel('Total Bandwidth (MB/s)')
            ax.set_title(f'Bandwidth vs Thread Count (Read Ratio = {ratios_unique[0]:.2f})')
            ax.set_xscale('log')
            ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, 'bandwidth_contour.png'), dpi=300)
    plt.close()
    
    print(f"Figures saved to {FIGURES_DIR}/")

def main():
    """Main execution function"""
    print("CXL Double Bandwidth Benchmark Visualization")
    print("=" * 50)
    
    # Ensure directories exist
    ensure_dirs()
    
    # Check if benchmark exists
    if not os.path.exists("./double_bandwidth"):
        print("Error: double_bandwidth executable not found!")
        print("Please build it first with 'make double_bandwidth'")
        return
    
    # Ask which test to run
    print("\nSelect test to run:")
    print("1. Test 1: Fixed thread count (1000), varying read ratios (0.05-0.95)")
    print("2. Test 2: Fixed read ratio (0.5), varying thread counts (2-1000)")
    print("3. Both tests")
    
    test_choice = input("\nEnter your choice (1/2/3): ").strip()
    
    if test_choice not in ['1', '2', '3']:
        print("Invalid choice. Exiting.")
        return
    
    tests_to_run = []
    if test_choice == '1':
        tests_to_run = [1]
    elif test_choice == '2':
        tests_to_run = [2]
    else:
        tests_to_run = [1, 2]
    
    # Run selected tests
    for test_num in tests_to_run:
        # Check if we should load existing data
        test_prefix = f'test{test_num}_final'
        existing_files = [f for f in os.listdir(RESULTS_DIR) if f.startswith(test_prefix) and f.endswith('.csv')]
        
        if existing_files and input(f"\nFound existing results for Test {test_num}. Use latest? (y/n): ").lower() == 'y':
            latest_file = sorted(existing_files)[-1]
            df = pd.read_csv(os.path.join(RESULTS_DIR, latest_file))
            print(f"Loaded {len(df)} results from {latest_file}")
        else:
            # Collect new data
            if test_num == 1:
                print(f"\nRunning Test 1: {len(TEST1_READ_RATIOS)} benchmark combinations...")
                print(f"Estimated time: {len(TEST1_READ_RATIOS) * (DURATION + 1) / 60:.1f} minutes")
            else:
                print(f"\nRunning Test 2: {len(TEST2_THREAD_NUMBERS)} benchmark combinations...")
                print(f"Estimated time: {len(TEST2_THREAD_NUMBERS) * (DURATION + 1) / 60:.1f} minutes")
            
            df = collect_data(test_num)
            
            if df.empty:
                print(f"No data collected for Test {test_num}!")
                continue
            
            # Save final results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = os.path.join(RESULTS_DIR, f'test{test_num}_final_{timestamp}.csv')
            df.to_csv(results_file, index=False)
            print(f"Test {test_num} results saved to {results_file}")
        
        # Create figures for the test
        print(f"\nGenerating figures for Test {test_num}...")
        if test_num == 1:
            create_test1_figures(df)
        else:
            create_test2_figures(df)
        
        # Print summary statistics
        print(f"\nTest {test_num} Summary Statistics:")
        print(f"Max total bandwidth: {df['total_bandwidth'].max():.2f} MB/s")
        print(f"Best configuration: {df.loc[df['total_bandwidth'].idxmax()].to_dict()}")
        print(f"Mean bandwidth: {df['total_bandwidth'].mean():.2f} MB/s")
        
        if test_num == 1:
            # Additional stats for Test 1
            best_read_ratio = df.loc[df['total_bandwidth'].idxmax()]['read_ratio']
            print(f"Optimal read ratio: {best_read_ratio:.2f}")
        else:
            # Additional stats for Test 2
            print(f"Max bandwidth per thread: {(df['total_bandwidth'] / df['threads']).max():.2f} MB/s")
    
    print(f"\nAll figures saved to {FIGURES_DIR}/")

if __name__ == "__main__":
    main()