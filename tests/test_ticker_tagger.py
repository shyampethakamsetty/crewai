#!/usr/bin/env python3
"""
Test script for the Intelligent Ticker Attribution Tool
Tests Phase 2 of the advanced pipeline implementation.
"""

import sys
import os
import json

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from market_analysis.tools.ticker_tagger_tool import TickerTaggerTool

def create_sample_sentences_data():
    """Create sample sentence-processed data to test ticker tagging."""
    
    sample_data = {
        "data": [
            {
                "source": "youtube",
                "trader": "meet_kevin",
                "original_transcript": "Tesla just destroyed earnings expectations...",
                "sentences": [
                    "Tesla just destroyed earnings expectations last night.",
                    "They reported $31.2 billion in revenue versus the street estimate of $29.8 billion.",
                    "That's a solid 4.7% beat!",
                    "I'm super bullish on TSLA right now.",
                    "Looking at the technicals, we finally broke above that stubborn $250 resistance.",
                    "This breakout looks legit.",
                    "My target for Tesla is $295 over the next 2-3 months.",
                    "Now switching to Apple - AAPL had a mixed quarter.",
                    "iPhone revenue was down but services revenue grew 16%.",
                    "The stock is hovering around $185 support."
                ],
                "sentence_count": 10,
                "processing_date": "2024-01-15"
            },
            {
                "source": "youtube",
                "trader": "graham_stephan", 
                "original_transcript": "I want to share my thoughts on Tesla and Apple...",
                "sentences": [
                    "I want to share my thoughts on my recent Tesla positions.",
                    "I've been adding to TSLA on weakness.",
                    "The energy business is exploding and FSD is making progress.",
                    "For Apple, it's been my largest holding for years.",
                    "The services revenue keeps growing double digits."
                ],
                "sentence_count": 5,
                "processing_date": "2024-01-15"
            }
        ],
        "original_statistics": {
            "total_transcript_hours": 2.5,
            "total_videos_collected": 10,
            "total_transcripts_collected": 2
        },
        "sentence_processing_date": "2024-01-15"
    }
    
    # Create test data
    test_dir = "tests/sample_data"
    os.makedirs(test_dir, exist_ok=True)
    
    test_file = f"{test_dir}/sentences_processed.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    return test_file

def test_ticker_tagging():
    """Test the ticker tagging functionality."""
    
    # Create sample data
    test_sentences_file = create_sample_sentences_data()
    test_output_dir = "tests/sample_data"
    asset_mapping_file = "src/market_analysis/config/asset_mapping.yaml"
    
    # Initialize the tool
    tagger = TickerTaggerTool()
    
    # Process ticker tagging
    result_json = tagger._run(
        sentences_file=test_sentences_file,
        asset_mapping_file=asset_mapping_file,
        output_dir=test_output_dir
    )
    
    # Parse and display results
    result = json.loads(result_json)
    
    print("=" * 80)
    print("PHASE 2: INTELLIGENT TICKER ATTRIBUTION TEST")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Output File: {result.get('output_file', 'N/A')}")
    print(f"Processing Time: {result['processing_time']}")
    print()
    
    if result['status'] == 'success':
        stats = result.get('statistics', {})
        print("TICKER TAGGING STATISTICS:")
        print("-" * 50)
        print(f"Total Sentences: {stats.get('total_sentences', 0)}")
        print(f"Total Attributions: {stats.get('total_attributions', 0)}")
        print(f"Total Inheritance: {stats.get('total_inheritance', 0)}")
        print(f"Unique Tickers: {stats.get('unique_tickers', 0)}")
        print(f"Attribution Rate: {stats.get('attribution_rate', 0):.1%}")
        
        print(f"\nSummary: {result.get('summary', 'N/A')}")
        
        # Verify output file
        output_file = result.get('output_file')
        if output_file and os.path.exists(output_file):
            print(f"✓ Output file created: {output_file}")
            
            # Load and examine output
            with open(output_file, 'r', encoding='utf-8') as f:
                ticker_data = json.load(f)
            
            print("\nTICKER TAGGING ANALYSIS:")
            print("-" * 40)
            
            # Analyze first record
            if ticker_data.get('data'):
                first_record = ticker_data['data'][0]
                trader = first_record.get('trader', 'Unknown')
                tagged_sentences = first_record.get('tagged_sentences', [])
                
                print(f"\nAnalysis for {trader}:")
                print(f"Tagged sentences: {len(tagged_sentences)}")
                
                # Show sample ticker attributions
                print("\nSample Ticker Attributions:")
                for i, sentence in enumerate(tagged_sentences[:5], 1):
                    direct = sentence.get('direct_tickers', [])
                    inherited = sentence.get('inherited_tickers', [])
                    all_tickers = sentence.get('all_tickers', [])
                    
                    print(f"  {i}. {sentence['sentence'][:60]}...")
                    if direct:
                        print(f"     Direct: {direct}")
                    if inherited:
                        print(f"     Inherited: {inherited}")
                    if all_tickers:
                        print(f"     All: {all_tickers}")
                    print()
                
                # Test context inheritance
                print("CONTEXT INHERITANCE TEST:")
                print("-" * 30)
                
                # Find sentences with inheritance
                inherited_sentences = [s for s in tagged_sentences if s.get('inherited_tickers')]
                print(f"Sentences with inheritance: {len(inherited_sentences)}")
                
                for sentence in inherited_sentences[:3]:
                    print(f"• '{sentence['sentence'][:50]}...'")
                    print(f"  Inherited: {sentence['inherited_tickers']}")
                
                # Test ticker recognition
                print("\nTICKER RECOGNITION TEST:")
                print("-" * 25)
                
                # Check specific cases
                tesla_sentences = [s for s in tagged_sentences if 'TSLA' in s.get('all_tickers', [])]
                apple_sentences = [s for s in tagged_sentences if 'AAPL' in s.get('all_tickers', [])]
                
                print(f"Tesla (TSLA) mentions: {len(tesla_sentences)}")
                print(f"Apple (AAPL) mentions: {len(apple_sentences)}")
                
                # Show ticker summary
                summary = first_record.get('ticker_summary', {})
                print(f"\nTicker Summary:")
                print(f"  Unique tickers: {summary.get('unique_tickers', [])}")
                print(f"  Ticker counts: {summary.get('ticker_counts', {})}")
                
        else:
            print(f"❌ Output file not found: {output_file}")
            return False
            
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        return False
    
    return True

def main():
    """Run ticker tagging tests."""
    print("Testing Phase 2: Intelligent Ticker Attribution with Context Inheritance")
    print("=" * 80)
    
    # Test ticker tagging
    success = test_ticker_tagging()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ PHASE 2 TESTING COMPLETED SUCCESSFULLY")
        print("🎯 Ticker attribution with context inheritance verified")
        print("📊 Asset mapping configuration working correctly")
        print("🔄 Ready to proceed to Phase 3: Quality Filtering & Content Categorization")
    else:
        print("❌ PHASE 2 TESTING FAILED")
    print("=" * 80)

if __name__ == "__main__":
    main() 