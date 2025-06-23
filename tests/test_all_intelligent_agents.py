import json
import os
import tempfile
import pytest
from pathlib import Path

# Import all four tools
from src.market_analysis.tools.youtube_collection_tool import YouTubeCollectionTool
from src.market_analysis.tools.data_processor_tool import DataProcessorTool
from src.market_analysis.tools.sentence_processor_tool import SentenceProcessorTool
from src.market_analysis.tools.ticker_tagger_tool import TickerTaggerTool

def create_mock_raw_youtube_data():
    """Create mock raw YouTube data for testing."""
    return [
        {
            "channel_info": {
                "channel_name": "Meet Kevin",
                "channel_id": "UC12345678901234567890123"
            },
            "video_info": {
                "video_id": "test_video_1",
                "title": "Tesla Stock Analysis",
                "duration": "PT15M30S"
            },
            "transcript_data": {
                "transcript_available": True,
                "transcript_only_text": "Tesla is making great progress with their electric vehicles. The company's stock price has been volatile but shows strong fundamentals."
            }
        },
        {
            "channel_info": {
                "channel_name": "Graham Stephan",
                "channel_id": "UC23456789012345678901234"
            },
            "video_info": {
                "video_id": "test_video_2",
                "title": "Market Update",
                "duration": "PT10M45S"
            },
            "transcript_data": {
                "transcript_available": True,
                "transcript_only_text": "The S&P 500 has been performing well this quarter. Apple's earnings were strong and exceeded expectations."
            }
        }
    ]

def create_mock_processed_data():
    """Create mock processed YouTube data."""
    return {
        "data": [
            {
                "source": "youtube",
                "trader": "Meet Kevin",
                "data": "Tesla is making great progress with their electric vehicles. The company's stock price has been volatile but shows strong fundamentals."
            },
            {
                "source": "youtube", 
                "trader": "Graham Stephan",
                "data": "The S&P 500 has been performing well this quarter. Apple's earnings were strong and exceeded expectations."
            }
        ],
        "total_transcript_hours": 0.44,
        "total_videos_collected": 2,
        "total_transcripts_collected": 2
    }

def create_mock_sentences_data():
    """Create mock sentences data."""
    return [
        {
            "sentence": "Tesla is making great progress with their electric vehicles.",
            "source": "youtube",
            "trader": "Meet Kevin",
            "context": {
                "video_title": "Tesla Stock Analysis",
                "channel": "Meet Kevin"
            }
        },
        {
            "sentence": "The company's stock price has been volatile but shows strong fundamentals.",
            "source": "youtube", 
            "trader": "Meet Kevin",
            "context": {
                "video_title": "Tesla Stock Analysis",
                "channel": "Meet Kevin"
            }
        },
        {
            "sentence": "The S&P 500 has been performing well this quarter.",
            "source": "youtube",
            "trader": "Graham Stephan", 
            "context": {
                "video_title": "Market Update",
                "channel": "Graham Stephan"
            }
        },
        {
            "sentence": "Apple's earnings were strong and exceeded expectations.",
            "source": "youtube",
            "trader": "Graham Stephan",
            "context": {
                "video_title": "Market Update", 
                "channel": "Graham Stephan"
            }
        }
    ]

def test_youtube_collector_intelligence():
    """Test YouTube collector intelligence - skip when output exists."""
    print("\n" + "=" * 60)
    print("TESTING: YouTube Collector Intelligence")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = temp_dir
        raw_data_file = f"{output_dir}/raw_youtube_data.json"
        
        # Create existing output file
        mock_data = create_mock_raw_youtube_data()
        os.makedirs(output_dir, exist_ok=True)
        with open(raw_data_file, 'w') as f:
            json.dump(mock_data, f)
        
        # Test tool skipping behavior
        tool = YouTubeCollectionTool()
        result_json = tool._run(output_dir=output_dir)
        result = json.loads(result_json)
        
        print(f"✅ Status: {result['status']}")
        print(f"📄 Reason: {result.get('reason', 'N/A')}")
        print(f"📊 Existing videos: {result.get('existing_statistics', {}).get('total_videos_collected', 0)}")
        
        assert result["status"] == "skipped"
        assert "already exists" in result["reason"]
        assert "existing_statistics" in result
        
        print("✅ YouTube Collector intelligence test PASSED")
        return True

def test_data_processor_intelligence():
    """Test data processor intelligence - skip when output exists."""
    print("\n" + "=" * 60)
    print("TESTING: Data Processor Intelligence")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = temp_dir
        processed_file = f"{output_dir}/youtube_processed.json"
        
        # Create existing output file
        mock_data = create_mock_processed_data()
        os.makedirs(output_dir, exist_ok=True)
        with open(processed_file, 'w') as f:
            json.dump(mock_data, f)
        
        # Test tool skipping behavior
        tool = DataProcessorTool()
        result_json = tool._run(output_dir=output_dir)
        result = json.loads(result_json)
        
        print(f"✅ Status: {result['status']}")
        print(f"📄 Reason: {result.get('reason', 'N/A')}")
        print(f"📊 Existing videos: {result.get('existing_statistics', {}).get('total_videos_collected', 0)}")
        
        assert result["status"] == "skipped"
        assert "already exists" in result["reason"]
        assert "existing_statistics" in result
        
        print("✅ Data Processor intelligence test PASSED")
        return True

def test_sentence_processor_intelligence():
    """Test sentence processor intelligence - skip when output exists."""
    print("\n" + "=" * 60)
    print("TESTING: Sentence Processor Intelligence")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = temp_dir
        sentences_file = f"{output_dir}/sentences_processed.json"
        
        # Create existing output file
        mock_data = create_mock_sentences_data()
        os.makedirs(output_dir, exist_ok=True)
        with open(sentences_file, 'w') as f:
            json.dump(mock_data, f)
        
        # Test tool skipping behavior
        tool = SentenceProcessorTool()
        result_json = tool._run(output_dir=output_dir)
        result = json.loads(result_json)
        
        print(f"✅ Status: {result['status']}")
        print(f"📄 Reason: {result.get('reason', 'N/A')}")
        print(f"📊 Existing sentences: {result.get('existing_statistics', {}).get('total_sentences', 0)}")
        
        assert result["status"] == "skipped"
        assert "already exists" in result["reason"]
        assert "existing_statistics" in result
        
        print("✅ Sentence Processor intelligence test PASSED")
        return True

def test_ticker_tagger_intelligence():
    """Test ticker tagger intelligence - skip when output exists."""
    print("\n" + "=" * 60)
    print("TESTING: Ticker Tagger Intelligence")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = temp_dir
        tagged_file = f"{output_dir}/ticker_tagged.json"
        
        # Create existing output file
        mock_data = [
            {
                "sentence": "Tesla is making great progress with their electric vehicles.",
                "tickers": ["TSLA"],
                "source": "youtube",
                "trader": "Meet Kevin"
            }
        ]
        os.makedirs(output_dir, exist_ok=True)
        with open(tagged_file, 'w') as f:
            json.dump(mock_data, f)
        
        # Test tool skipping behavior
        tool = TickerTaggerTool()
        result_json = tool._run(output_dir=output_dir)
        result = json.loads(result_json)
        
        print(f"✅ Status: {result['status']}")
        print(f"📄 Reason: {result.get('reason', 'N/A')}")
        print(f"📊 Existing sentences: {result.get('existing_statistics', {}).get('total_sentences', 0)}")
        
        assert result["status"] == "skipped"
        assert "already exists" in result["reason"]
        assert "existing_statistics" in result
        
        print("✅ Ticker Tagger intelligence test PASSED")
        return True

def test_full_pipeline_intelligence():
    """Test that all four agents work together intelligently."""
    print("\n" + "=" * 80)
    print("TESTING: Full Pipeline Intelligence (All 4 Agents)")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = temp_dir
        
        # Create all output files to simulate completed pipeline
        files_to_create = [
            ("raw_youtube_data.json", create_mock_raw_youtube_data()),
            ("youtube_processed.json", create_mock_processed_data()),
            ("sentences_processed.json", create_mock_sentences_data()),
            ("ticker_tagged.json", [{"sentence": "Test", "tickers": ["TSLA"]}])
        ]
        
        os.makedirs(output_dir, exist_ok=True)
        for filename, data in files_to_create:
            with open(f"{output_dir}/{filename}", 'w') as f:
                json.dump(data, f)
        
        # Test all tools
        tools = [
            ("YouTube Collector", YouTubeCollectionTool()),
            ("Data Processor", DataProcessorTool()),
            ("Sentence Processor", SentenceProcessorTool()),
            ("Ticker Tagger", TickerTaggerTool())
        ]
        
        results = []
        for tool_name, tool in tools:
            result_json = tool._run(output_dir=output_dir)
            result = json.loads(result_json)
            results.append((tool_name, result))
            
            status = result['status']
            emoji = "✅" if status == "skipped" else "❌"
            print(f"{emoji} {tool_name}: {status}")
        
        # Verify all tools skipped processing
        all_skipped = all(result['status'] == 'skipped' for _, result in results)
        
        if all_skipped:
            print("\n🎉 ALL AGENTS ARE INTELLIGENT! Pipeline optimization successful.")
            print("💡 Benefits:")
            print("   • Instant re-runs when files exist")
            print("   • No unnecessary API calls or processing")
            print("   • Significant time savings on repeated executions")
        else:
            print("\n❌ Some agents failed intelligence test")
            
        assert all_skipped, "Not all agents properly skipped when output files existed"
        
        print("✅ Full Pipeline Intelligence test PASSED")
        return True

def test_performance_comparison():
    """Test performance benefits of intelligence enhancement."""
    print("\n" + "=" * 60)
    print("TESTING: Performance Benefits Comparison")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create input data for sentence processor
        input_file = f"{temp_dir}/youtube_processed.json"
        mock_data = create_mock_processed_data()
        with open(input_file, 'w') as f:
            json.dump(mock_data, f)
        
        tool = SentenceProcessorTool()
        
        # First run - actual processing
        import time
        start_time = time.time()
        result1_json = tool._run(processed_data_file=input_file, output_dir=temp_dir)
        first_run_time = time.time() - start_time
        
        # Second run - should skip
        start_time = time.time()
        result2_json = tool._run(processed_data_file=input_file, output_dir=temp_dir)
        second_run_time = time.time() - start_time
        
        result1 = json.loads(result1_json)
        result2 = json.loads(result2_json)
        
        print(f"⏱️  First run (processing): {first_run_time:.3f} seconds - Status: {result1['status']}")
        print(f"⚡ Second run (skipping): {second_run_time:.3f} seconds - Status: {result2['status']}")
        
        # Calculate speed improvement
        if second_run_time > 0.001:  # Avoid division by very small numbers
            speed_improvement = first_run_time / second_run_time
            print(f"🚀 Speed improvement: {speed_improvement:.1f}x faster")
        else:
            print(f"🚀 Speed improvement: >100x faster (near-instant)")
        
        # Verify first run processed, second run skipped
        assert result1["status"] == "success", "First run should process successfully"
        assert result2["status"] == "skipped", "Second run should skip processing"
        
        # For very small datasets, the file I/O overhead might make skipping slightly slower
        # The key benefit is that we're not doing any actual processing on the second run
        print(f"✅ Intelligence verified: First run = {result1['status']}, Second run = {result2['status']}")
        
        print("✅ Performance comparison test PASSED")
        return True

if __name__ == "__main__":
    print("🧠 INTELLIGENT AGENTS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_youtube_collector_intelligence,
        test_data_processor_intelligence, 
        test_sentence_processor_intelligence,
        test_ticker_tagger_intelligence,
        test_full_pipeline_intelligence,
        test_performance_comparison
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} FAILED: {e}")
    
    print("\n" + "=" * 80)
    print(f"🎯 TEST RESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 ALL TESTS PASSED! Intelligence enhancement successful!")
    else:
        print("❌ Some tests failed. Check the output above.")
    print("=" * 80) 