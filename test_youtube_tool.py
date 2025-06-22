#!/usr/bin/env python3
"""
Test script for YouTube Collection Tool
"""

import sys
import os
sys.path.append('src')

from market_analysis.tools.youtube_collection_tool import YouTubeCollectionTool

def test_youtube_tool():
    """Test the YouTube collection tool with sample data"""
    
    # Test channel IDs (from your channels.json)
    test_channel_ids = [
        "UCSDJl5c-AvvQvgsnKB4QKOA",  # Lee Lowell - The Smart Option Seller
        "UC9kVkLPTdjaj4shvCFfoA9g",  # Fat Cat
        "UCu5zHoiswVlyeR3T-W6e_hA"   # Maverick Trading
    ]
    
    print("🧪 Testing YouTube Collection Tool...")
    print(f"📺 Testing with {len(test_channel_ids)} channels")
    print(f"⏰ Time range: Last 24 hours")
    print(f"📦 Batch size: 75 videos")
    print("-" * 50)
    
    try:
        # Create tool instance
        tool = YouTubeCollectionTool()
        
        # Test the tool
        result = tool._run(
            channel_ids=test_channel_ids,
            hours_back=24,
            video_batch_size=75
        )
        
        print("✅ Tool execution completed!")
        print(f"📄 Result type: {type(result)}")
        print(f"📄 Result length: {len(result)}")
        print(f"📄 First 500 chars: {result[:500]}...")
        
        # Parse the JSON result
        import json
        parsed_result = json.loads(result)
        print(f"📊 Status: {parsed_result.get('status')}")
        print(f"📊 Total videos: {parsed_result.get('total_videos')}")
        
        if parsed_result.get('status') == 'success':
            data = parsed_result.get('data', [])
            print(f"📊 Data items: {len(data)}")
            if data:
                print(f"📊 First video: {data[0].get('video_info', {}).get('title', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_youtube_tool() 