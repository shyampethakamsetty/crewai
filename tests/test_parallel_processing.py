#!/usr/bin/env python3
"""
Test script for parallel sentence processing functionality.
This demonstrates the performance improvements of parallel processing over sequential processing.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from market_analysis.tools.parallel_tool import ParallelSentenceProcessorTool
from market_analysis.tools.advanced_sentence_processor import AdvancedSentenceProcessor

def create_large_transcript(size_mb: float = 1.0) -> str:
    """Create a large transcript for testing parallel processing"""
    base_text = """
    Apple stock is trading at $150.50 today. The company reported strong earnings growth of 15% year-over-year. 
    AAPL has been performing well in the market. The CEO mentioned that iPhone sales increased by 20% this quarter. 
    Analysts are bullish on the stock with a target price of $175. The market cap is now over $2.5 trillion. 
    Investors are excited about the new product launches scheduled for Q4. The stock price has increased by 25% this year.
    
    Microsoft stock is also performing well at $300.25. The cloud computing division grew by 30% this quarter.
    MSFT has been expanding its Azure platform rapidly. The company's AI initiatives are gaining traction.
    Revenue from Office 365 continues to grow steadily. The gaming division saw strong Xbox sales.
    
    Tesla stock is volatile at $250.75. The electric vehicle market is becoming more competitive.
    TSLA delivered 500,000 vehicles this quarter. The company is expanding production capacity.
    Battery technology improvements are driving down costs. The autonomous driving features are progressing well.
    
    Amazon stock is stable at $3,200. The e-commerce giant continues to dominate online retail.
    AMZN's AWS cloud services are growing rapidly. The company is investing heavily in logistics.
    Prime membership continues to grow globally. The advertising business is expanding significantly.
    
    Google stock is performing well at $2,800. The search giant's advertising revenue is strong.
    GOOGL's YouTube platform is growing rapidly. The cloud division is gaining market share.
    The company's AI research is leading the industry. Android continues to dominate mobile platforms.
    """
    
    # Calculate how many repetitions we need
    target_size = size_mb * 1024 * 1024  # Convert MB to bytes
    base_size = len(base_text.encode('utf-8'))
    repetitions = int(target_size / base_size) + 1
    
    # Create the large transcript
    large_transcript = base_text * repetitions
    
    # Trim to exact size
    while len(large_transcript.encode('utf-8')) > target_size:
        large_transcript = large_transcript[:-1000]
    
    return large_transcript

def test_sequential_processing(transcript: str, trader: str = "SequentialTest") -> dict:
    """Test sequential processing using the original processor"""
    print(f"\n{'='*60}")
    print("TESTING SEQUENTIAL PROCESSING")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Initialize sequential processor
    processor = AdvancedSentenceProcessor()
    
    # Process transcript
    result = processor.process_sentences(transcript, "youtube", trader)
    
    processing_time = time.time() - start_time
    
    print(f"Sequential Processing Results:")
    print(f"  - Transcript size: {len(transcript) / (1024*1024):.2f} MB")
    print(f"  - Sentences generated: {result['sentence_count']}")
    print(f"  - Processing time: {processing_time:.2f} seconds")
    print(f"  - Processing rate: {len(transcript) / (1024*1024) / processing_time:.2f} MB/s")
    
    return {
        "method": "sequential",
        "transcript_size_mb": len(transcript) / (1024*1024),
        "sentences_generated": result['sentence_count'],
        "processing_time": processing_time,
        "processing_rate_mbps": len(transcript) / (1024*1024) / processing_time
    }

def test_parallel_processing(transcript: str, max_workers: int, trader: str = "ParallelTest") -> dict:
    """Test parallel processing using the new parallel processor"""
    print(f"\n{'='*60}")
    print(f"TESTING PARALLEL PROCESSING ({max_workers} workers)")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Initialize parallel processor
    tool = ParallelSentenceProcessorTool(max_workers=max_workers)
    
    # Process transcript
    result = tool.process_transcript(transcript, "youtube", trader)
    
    processing_time = time.time() - start_time
    
    if result["status"] == "success":
        data = result["data"]
        print(f"Parallel Processing Results:")
        print(f"  - Transcript size: {len(transcript) / (1024*1024):.2f} MB")
        print(f"  - Sentences generated: {data['sentence_count']}")
        print(f"  - Chunks processed: {data['chunks_processed']}")
        print(f"  - Workers used: {data['workers_used']}")
        print(f"  - Processing time: {processing_time:.2f} seconds")
        print(f"  - Processing rate: {len(transcript) / (1024*1024) / processing_time:.2f} MB/s")
        print(f"  - From cache: {result['from_cache']}")
        
        return {
            "method": f"parallel_{max_workers}_workers",
            "transcript_size_mb": len(transcript) / (1024*1024),
            "sentences_generated": data['sentence_count'],
            "chunks_processed": data['chunks_processed'],
            "workers_used": data['workers_used'],
            "processing_time": processing_time,
            "processing_rate_mbps": len(transcript) / (1024*1024) / processing_time,
            "from_cache": result['from_cache']
        }
    else:
        print(f"Parallel processing failed: {result['message']}")
        return {
            "method": f"parallel_{max_workers}_workers",
            "error": result['message'],
            "processing_time": processing_time
        }

def compare_performance(results: list) -> None:
    """Compare performance between different processing methods"""
    print(f"\n{'='*60}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*60}")
    
    # Filter out failed results
    successful_results = [r for r in results if 'error' not in r]
    
    if not successful_results:
        print("No successful results to compare")
        return
    
    # Find the fastest method
    fastest = min(successful_results, key=lambda x: x['processing_time'])
    
    print(f"Fastest method: {fastest['method']}")
    print(f"Processing time: {fastest['processing_time']:.2f} seconds")
    print(f"Processing rate: {fastest['processing_rate_mbps']:.2f} MB/s")
    
    # Compare with sequential
    sequential_results = [r for r in successful_results if r['method'] == 'sequential']
    parallel_results = [r for r in successful_results if r['method'].startswith('parallel')]
    
    if sequential_results and parallel_results:
        seq_time = sequential_results[0]['processing_time']
        best_parallel = min(parallel_results, key=lambda x: x['processing_time'])
        par_time = best_parallel['processing_time']
        
        speedup = seq_time / par_time
        print(f"\nSpeedup: {speedup:.2f}x faster with parallel processing")
        print(f"Time saved: {seq_time - par_time:.2f} seconds")
        
        # Calculate efficiency
        workers_used = best_parallel['workers_used']
        efficiency = speedup / workers_used * 100
        print(f"Parallel efficiency: {efficiency:.1f}%")

def test_worker_scaling(transcript: str) -> None:
    """Test how performance scales with different numbers of workers"""
    print(f"\n{'='*60}")
    print("WORKER SCALING TEST")
    print(f"{'='*60}")
    
    import multiprocessing as mp
    max_cpus = mp.cpu_count()
    
    # Test with different numbers of workers
    worker_counts = [1, 2, 4, 8]
    if max_cpus > 8:
        worker_counts.append(max_cpus)
    
    scaling_results = []
    
    for workers in worker_counts:
        if workers > max_cpus:
            continue
            
        result = test_parallel_processing(transcript, workers, f"ScalingTest_{workers}workers")
        if 'error' not in result:
            scaling_results.append(result)
    
    # Analyze scaling
    if scaling_results:
        print(f"\nScaling Analysis:")
        for result in scaling_results:
            workers = result['workers_used']
            time_taken = result['processing_time']
            rate = result['processing_rate_mbps']
            print(f"  {workers} workers: {time_taken:.2f}s ({rate:.2f} MB/s)")

def main():
    """Main test function"""
    print("PARALLEL SENTENCE PROCESSING PERFORMANCE TEST")
    print("=" * 60)
    
    # Create test transcript (1MB)
    print("Creating test transcript...")
    transcript = create_large_transcript(1.0)
    print(f"Created transcript: {len(transcript) / (1024*1024):.2f} MB")
    
    results = []
    
    # Test sequential processing
    seq_result = test_sequential_processing(transcript)
    results.append(seq_result)
    
    # Test parallel processing with different worker counts
    worker_counts = [2, 4]
    import multiprocessing as mp
    if mp.cpu_count() >= 8:
        worker_counts.append(8)
    
    for workers in worker_counts:
        par_result = test_parallel_processing(transcript, workers)
        results.append(par_result)
    
    # Compare performance
    compare_performance(results)
    
    # Test worker scaling
    test_worker_scaling(transcript)
    
    # Save results
    output_file = Path("output") / "parallel_processing_test_results.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "transcript_size_mb": len(transcript) / (1024*1024),
            "results": results
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    # Show final stats
    tool = ParallelSentenceProcessorTool()
    stats = tool.get_processing_stats()
    print(f"\nFinal Processing Stats:")
    print(f"  Total transcripts processed: {stats['stats']['total_transcripts_processed']}")
    print(f"  Total sentences generated: {stats['stats']['total_sentences_generated']}")
    print(f"  Average processing time: {stats['stats']['average_processing_time']:.2f}s")
    print(f"  Total chunks processed: {stats['stats']['chunks_processed']}")

if __name__ == "__main__":
    main() 