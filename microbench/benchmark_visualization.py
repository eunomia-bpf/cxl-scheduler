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
THREAD_NUMBERS = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1000]
READ_RATIOS = np.arange(0.05, 1.0, 0.05)  # 0.05 to 0.95
DURATION = 10  # seconds per test
BLOCK_SIZE = 4096  # 4KB
BUFFER_SIZE = "1G"  # 1GB
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
        "-b", str(BLOCK_SIZE),
        "-s", BUFFER_SIZE
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

def collect_data():
    """Run all benchmark combinations and collect results"""
    results = []
    
    total_runs = len(THREAD_NUMBERS) * len(READ_RATIOS)
    
    with tqdm(total=total_runs, desc="Running benchmarks") as pbar:
        for num_threads in THREAD_NUMBERS:
            for read_ratio in READ_RATIOS:
                pbar.set_description(f"Threads: {num_threads}, Read ratio: {read_ratio:.2f}")
                
                metrics = run_benchmark(num_threads, read_ratio)
                
                if metrics:
                    result = {
                        'threads': num_threads,
                        'read_ratio': read_ratio,
                        **metrics
                    }
                    results.append(result)
                    
                    # Save intermediate results
                    pd.DataFrame(results).to_csv(
                        os.path.join(RESULTS_DIR, f'results_intermediate_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'),
                        index=False
                    )
                
                pbar.update(1)
                time.sleep(1)  # Brief pause between tests
    
    return pd.DataFrame(results)

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
    
    # Check if we should load existing data
    existing_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.csv')]
    
    if existing_files and input("Found existing results. Use latest? (y/n): ").lower() == 'y':
        latest_file = sorted(existing_files)[-1]
        df = pd.read_csv(os.path.join(RESULTS_DIR, latest_file))
        print(f"Loaded {len(df)} results from {latest_file}")
    else:
        # Collect new data
        print(f"Running {len(THREAD_NUMBERS) * len(READ_RATIOS)} benchmark combinations...")
        print(f"Estimated time: {len(THREAD_NUMBERS) * len(READ_RATIOS) * (DURATION + 1) / 60:.1f} minutes")
        
        df = collect_data()
        
        if df.empty:
            print("No data collected!")
            return
        
        # Save final results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(RESULTS_DIR, f'results_final_{timestamp}.csv')
        df.to_csv(results_file, index=False)
        print(f"Results saved to {results_file}")
    
    # Create figures
    print("\nGenerating figures...")
    create_figures(df)
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"Max total bandwidth: {df['total_bandwidth'].max():.2f} MB/s")
    print(f"Best configuration: {df.loc[df['total_bandwidth'].idxmax()].to_dict()}")
    print(f"Mean bandwidth: {df['total_bandwidth'].mean():.2f} MB/s")

if __name__ == "__main__":
    main()