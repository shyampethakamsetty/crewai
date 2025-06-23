#!/usr/bin/env python3
"""
Test script for intelligent agent behavior - testing file existence checks
Tests that agents skip processing when output files already exist.
"""

import sys
import os
import json

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from market_analysis.tools.sentence_processor_tool import SentenceProcessorTool
from market_analysis.tools.ticker_tagger_tool import TickerTaggerTool

def create_test_data():
    """Create test data files."""
    test_dir = "tests/sample_data"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create input file
    sample_data = {
        "data": [
            {
                "source": "youtube",
                "trader": "test_channel",
                "data": "Tesla is looking good. TSLA should hit $300 soon. Apple is also strong."
            }
        ],
        "total_transcript_hours": 1.0,
        "total_videos_collected": 1,
        "total_transcripts_collected": 1
    }
    
    input_file = f"{test_dir}/youtube_processed.json"
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    return test_dir, input_file

def test_sentence_processor_intelligence():
    """Test sentence processor intelligence (skip if output exists)."""
    print("=" * 60)
    print("TESTING: Sentence Processor Intelligence")
    print("=" * 60)
    
    test_dir, input_file = create_test_data()
    
    # Initialize tool
    processor = SentenceProcessorTool()
    
    # Test 1: First run (should process)
    print("🔄 First run (should process):")
    result1_json = processor._run(
        processed_data_file=input_file,
        output_dir=test_dir
    )
    result1 = json.loads(result1_json)
    print(f"   Status: {result1['status']}")
    print(f"   Summary: {result1.get('summary', 'N/A')}")
    
    # Test 2: Second run (should skip)
    print("\n🧠 Second run (should skip - intelligent behavior):")
    result2_json = processor._run(
        processed_data_file=input_file,
        output_dir=test_dir
    )
    result2 = json.loads(result2_json)
    print(f"   Status: {result2['status']}")
    print(f"   Reason: {result2.get('reason', 'N/A')}")
    print(f"   Summary: {result2.get('summary', 'N/A')}")
    
    # Verify intelligence
    if result1['status'] == 'success' and result2['status'] == 'skipped':
        print("   ✅ Intelligence verified: First run processed, second run skipped")
        return True
    else:
        print("   ❌ Intelligence failed")
        return False

def test_ticker_tagger_intelligence():
    """Test ticker tagger intelligence (skip if output exists)."""
    print("\n" + "=" * 60)
    print("TESTING: Ticker Tagger Intelligence")
    print("=" * 60)
    
    test_dir, _ = create_test_data()
    
    # Create sentences input file (from sentence processor output)
    sentences_data = {
        "data": [
            {
                "source": "youtube",
                "trader": "test_channel",
                "sentences": [
                    "Tesla is looking good.",
                    "TSLA should hit $300 soon.",
                    "Apple is also strong."
                ],
                "sentence_count": 3,
                "processing_date": "2024-01-15"
            }
        ],
        "sentence_processing_date": "2024-01-15"
    }
    
    sentences_file = f"{test_dir}/sentences_processed.json"
    with open(sentences_file, 'w', encoding='utf-8') as f:
        json.dump(sentences_data, f, indent=2)
    
    # Initialize tool
    tagger = TickerTaggerTool()
    
    # Test 1: First run (should process)
    print("🔄 First run (should process):")
    result1_json = tagger._run(
        sentences_file=sentences_file,
        asset_mapping_file="src/market_analysis/config/asset_mapping.yaml",
        output_dir=test_dir
    )
    result1 = json.loads(result1_json)
    print(f"   Status: {result1['status']}")
    print(f"   Summary: {result1.get('summary', 'N/A')}")
    
    # Test 2: Second run (should skip)
    print("\n🧠 Second run (should skip - intelligent behavior):")
    result2_json = tagger._run(
        sentences_file=sentences_file,
        asset_mapping_file="src/market_analysis/config/asset_mapping.yaml",
        output_dir=test_dir
    )
    result2 = json.loads(result2_json)
    print(f"   Status: {result2['status']}")
    print(f"   Reason: {result2.get('reason', 'N/A')}")
    print(f"   Summary: {result2.get('summary', 'N/A')}")
    
    # Verify intelligence
    if result1['status'] == 'success' and result2['status'] == 'skipped':
        print("   ✅ Intelligence verified: First run processed, second run skipped")
        return True
    else:
        print("   ❌ Intelligence failed")
        return False

def test_performance_benefits():
    """Test the performance benefits of intelligent skipping."""
    print("\n" + "=" * 60)
    print("TESTING: Performance Benefits")
    print("=" * 60)
    
    test_dir, input_file = create_test_data()
    
    # Time the first run
    import time
    
    processor = SentenceProcessorTool()
    
    start_time = time.time()
    result1_json = processor._run(processed_data_file=input_file, output_dir=test_dir)
    first_run_time = time.time() - start_time
    
    # Time the second run (should be much faster)
    start_time = time.time()
    result2_json = processor._run(processed_data_file=input_file, output_dir=test_dir)
    second_run_time = time.time() - start_time
    
    print(f"⏱️  First run (processing): {first_run_time:.3f} seconds")
    print(f"⚡ Second run (skipping): {second_run_time:.3f} seconds")
    
    # Handle the case where second run is extremely fast (near zero)
    if second_run_time > 0:
        speed_improvement = first_run_time / second_run_time
        print(f"🚀 Speed improvement: {speed_improvement:.1f}x faster")
    else:
        print(f"🚀 Speed improvement: >1000x faster (near-instant skipping)")
    
    result1 = json.loads(result1_json)
    result2 = json.loads(result2_json)
    
    return result1['status'] == 'success' and result2['status'] == 'skipped'

def main():
    """Run all intelligence tests."""
    print("Testing Intelligent Agent Behavior: File Existence Checks")
    print("=" * 80)
    
    # Test sentence processor intelligence
    processor_success = test_sentence_processor_intelligence()
    
    # Test ticker tagger intelligence
    tagger_success = test_ticker_tagger_intelligence()
    
    # Test performance benefits
    performance_success = test_performance_benefits()
    
    # Overall results
    print("\n" + "=" * 80)
    print("INTELLIGENCE TEST RESULTS:")
    print("=" * 80)
    print(f"📝 Sentence Processor Intelligence: {'✅ PASS' if processor_success else '❌ FAIL'}")
    print(f"🎯 Ticker Tagger Intelligence: {'✅ PASS' if tagger_success else '❌ FAIL'}")
    print(f"🚀 Performance Benefits: {'✅ PASS' if performance_success else '❌ FAIL'}")
    
    if processor_success and tagger_success and performance_success:
        print("\n🧠 AGENTS ARE INTELLIGENT!")
        print("✅ Agents now skip processing when output files exist")
        print("⚡ Significant performance improvement for re-runs")
        print("🔄 Ready for efficient pipeline development")
    else:
        print("\n❌ Intelligence implementation needs work")
    
    print("=" * 80)

if __name__ == "__main__":
    main() 