#!/usr/bin/env python3
"""
Test script for the Financial Context-Aware Sentence Processor Tool
Tests Phase 1 of the advanced pipeline implementation.
"""

import sys
import os
import json

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from market_analysis.tools.sentence_processor_tool import SentenceProcessorTool

def create_sample_processed_data():
    """Create sample processed data file to simulate previous agent output."""
    
    # Sample data structure matching youtube_processed.json format
    sample_data = {
        "data": [
            {
                "source": "youtube",
                "trader": "meet_kevin",
                "data": "What's up everyone, Meet Kevin here! Tesla just destroyed earnings expectations last night. They reported $31.2 billion in revenue versus the street estimate of $29.8 billion. That's a solid 4.7% beat! I'm super bullish on TSLA right now. Looking at the technicals, we finally broke above that stubborn $250 resistance with massive volume. This breakout looks legit. My target for Tesla is $295 over the next 2-3 months. Key support to watch is $245 and $235 on any pullback. Now switching to Apple - AAPL had a mixed quarter. iPhone revenue was actually down 2% year-over-year, but services revenue grew 16%. The China situation is still a headwind. I'm neutral on Apple here. The stock is hovering around $185 support. If we break below, next support is at $175."
            },
            {
                "source": "youtube", 
                "trader": "graham_stephan",
                "data": "Hey everyone, Graham here! I want to share my thoughts on my recent Tesla and Apple positions. I've been adding to TSLA on weakness - bought more shares at $220 last month. Tesla's energy business is exploding and FSD is making real progress. I think this company will be worth significantly more in 5-10 years. For Apple, it's been my largest individual holding for years. Currently sitting at about 12% of my portfolio."
            }
        ],
        "total_transcript_hours": 2.5,
        "total_videos_collected": 10,
        "total_transcripts_collected": 2
    }
    
    # Create test directory and file
    test_dir = "tests/sample_data"
    os.makedirs(test_dir, exist_ok=True)
    
    test_file = f"{test_dir}/youtube_processed.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    return test_file

def test_file_based_processing():
    """Test the file-based processing workflow."""
    
    # Create sample processed data file
    test_input_file = create_sample_processed_data()
    test_output_dir = "tests/sample_data"
    
    # Initialize the tool
    processor = SentenceProcessorTool()
    
    # Process using file-based workflow
    result_json = processor._run(
        processed_data_file=test_input_file,
        output_dir=test_output_dir
    )
    
    # Parse and display results
    result = json.loads(result_json)
    
    print("=" * 80)
    print("PHASE 1: FILE-BASED SENTENCE PROCESSOR TEST")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Input File: {result.get('input_file', 'N/A')}")
    print(f"Output File: {result.get('output_file', 'N/A')}")
    print(f"Processing Time: {result['processing_time']}")
    print()
    
    if result['status'] == 'success':
        stats = result.get('statistics', {})
        print("PROCESSING STATISTICS:")
        print("-" * 50)
        print(f"Total Records Processed: {stats.get('total_records', 0)}")
        print(f"Total Sentences Generated: {stats.get('total_sentences', 0)}")
        print(f"Average Sentences per Record: {stats.get('avg_sentences_per_record', 0)}")
        
        channel_breakdown = stats.get('channel_breakdown', {})
        print("\nChannel Breakdown:")
        for channel, data in channel_breakdown.items():
            print(f"  {channel}: {data['records']} records, {data['sentences']} sentences")
        
        print(f"\nSummary: {result.get('summary', 'N/A')}")
        
        # Verify output file was created
        output_file = result.get('output_file')
        if output_file and os.path.exists(output_file):
            print(f"✓ Output file created successfully: {output_file}")
            
            # Load and examine output file structure
            with open(output_file, 'r', encoding='utf-8') as f:
                sentence_data = json.load(f)
            
            print("\nOUTPUT FILE STRUCTURE:")
            print("-" * 30)
            print(f"Data records: {len(sentence_data.get('data', []))}")
            print(f"Original statistics preserved: {'original_statistics' in sentence_data}")
            print(f"Sentence processing date: {sentence_data.get('sentence_processing_date', 'N/A')}")
            
            # Show sample sentences from first record
            if sentence_data.get('data'):
                first_record = sentence_data['data'][0]
                sentences = first_record.get('sentences', [])
                print(f"\nSample sentences from {first_record.get('trader', 'Unknown')} ({len(sentences)} total):")
                for i, sentence in enumerate(sentences[:3], 1):  # Show first 3
                    print(f"  {i}. {sentence}")
                if len(sentences) > 3:
                    print(f"  ... and {len(sentences)-3} more sentences")
        else:
            print(f"❌ Output file not found: {output_file}")
            return False
        
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        return False
    
    return True

def test_edge_cases():
    """Test edge cases for financial content."""
    
    edge_cases = [
        {
            "name": "Financial Abbreviations",
            "text": "The P/E ratio is 25.3. Q3 earnings vs. Q2 were strong. CEO John Smith said revenue was up."
        },
        {
            "name": "Decimal Numbers",
            "text": "Stock price moved from $125.50 to $127.25. Volume was 2.3 million shares traded."
        },
        {
            "name": "Ticker Symbols",
            "text": "AAPL closed at $185.50. TSLA rallied 5.2% today. MSFT and GOOGL both beat estimates."
        }
    ]
    
    processor = SentenceProcessorTool()
    
    print("\n" + "=" * 80)
    print("EDGE CASES TESTING")  
    print("=" * 80)
    
    for case in edge_cases:
        print(f"\nTesting: {case['name']}")
        print(f"Input: {case['text']}")
        
        result_json = processor._run(case['text'], "test_channel")
        result = json.loads(result_json)
        
        if result['status'] == 'success':
            print(f"Output ({len(result['sentences'])} sentences):")
            for i, sentence in enumerate(result['sentences'], 1):
                print(f"  {i}. {sentence}")
        else:
            print(f"❌ Error: {result.get('error')}")

def main():
    """Run all tests."""
    print("Testing Phase 1: Financial Context-Aware Sentence Processor")
    print("=" * 80)
    
    # Test file-based processing workflow
    success = test_file_based_processing()
    
    # Test edge cases
    test_edge_cases()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ PHASE 1 TESTING COMPLETED SUCCESSFULLY")
        print("📁 File-based workflow verified")
        print("📊 Sentence processing statistics generated")
        print("🔄 Ready to proceed to Phase 2: Ticker Tagging with Context Inheritance")
    else:
        print("❌ PHASE 1 TESTING FAILED")
    print("=" * 80)

if __name__ == "__main__":
    main() 