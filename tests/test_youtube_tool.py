#!/usr/bin/env python3
"""
Test script for YouTube Collection Tool
"""

import sys
import os
sys.path.append('src')

from market_analysis.tools.youtube_collection_tool import YouTubeCollectionTool

def test_youtube_tool():
    """Test the YouTube collection tool with simplified configuration"""
    
    print("🧪 Testing YouTube Collection Tool...")
    print(f"📁 Using config: config/youtube_configuration.yaml")
    print(f"⏰ Time range: Last 24 hours")
    print(f"📦 Batch size: 75 videos")
    print("-" * 50)
    
    try:
        # Create tool instance
        tool = YouTubeCollectionTool()
        
        # Test the tool with simplified parameters
        result = tool._run(
            config_file="config/youtube_configuration.yaml"
        )
        
        print("✅ Tool execution completed!")
        print(f"📄 Result type: {type(result)}")
        print(f"📄 Result length: {len(result)}")
        print(f"📄 First 500 chars: {result[:500]}...")
        
        # Parse the JSON result
        import json
        parsed_result = json.loads(result)
        print(f"📊 Status: {parsed_result.get('status')}")
        
        if parsed_result.get('status') == 'success':
            statistics = parsed_result.get('statistics', {})
            print(f"📊 Total videos: {statistics.get('total_videos', 0)}")
            print(f"📊 Total channels: {statistics.get('total_channels', 0)}")
            print(f"📊 Total transcripts: {statistics.get('total_transcripts', 0)}")
            print(f"📊 Raw data file: {parsed_result.get('raw_data_file', 'N/A')}")
        else:
            print(f"❌ Error: {parsed_result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_youtube_tool() 