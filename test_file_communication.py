#!/usr/bin/env python3
"""
Test script for file-based communication pattern
"""

import sys
import os
import json
sys.path.append('src')

from market_analysis.tools.config_loader_tool import ConfigLoaderTool
from market_analysis.tools.youtube_collection_tool import YouTubeCollectionTool
from market_analysis.tools.data_processor_tool import DataProcessorTool

def test_file_communication_pattern():
    """Test the complete file-based communication flow"""
    
    print("🧪 Testing File-Based Communication Pattern")
    print("=" * 60)
    
    # Step 1: Test Configuration Loading
    print("\n📋 Step 1: Testing Configuration Loading...")
    config_tool = ConfigLoaderTool()
    config_result = config_tool._run("config/channels.json")
    config_data = json.loads(config_result)
    
    print(f"✅ Config Status: {config_data['status']}")
    if config_data['status'] == 'success':
        print(f"📊 Statistics: {config_data['statistics']}")
        print(f"📁 Config File: {config_data['config_file_path']}")
        
        # Step 2: Test YouTube Collection (using config file)
        print("\n📺 Step 2: Testing YouTube Collection...")
        youtube_tool = YouTubeCollectionTool()
        youtube_result = youtube_tool._run(
            validated_config_file=config_data['config_file_path'],
            hours_back=24,
            video_batch_size=75
        )
        youtube_data = json.loads(youtube_result)
        
        print(f"✅ YouTube Status: {youtube_data['status']}")
        if youtube_data['status'] == 'success':
            print(f"📊 Statistics: {youtube_data['statistics']}")
            print(f"📁 Raw Data File: {youtube_data['raw_data_file']}")
            print(f"📁 Transcripts Dir: {youtube_data['transcripts_directory']}")
            
            # Step 3: Test Data Processing (using raw data file)
            print("\n🔄 Step 3: Testing Data Processing...")
            processor_tool = DataProcessorTool()
            processor_result = processor_tool._run(
                raw_data_file=youtube_data['raw_data_file'],
                transcripts_dir=youtube_data['transcripts_directory']
            )
            processor_data = json.loads(processor_result)
            
            print(f"✅ Processing Status: {processor_data['status']}")
            if processor_data['status'] == 'success':
                print(f"📊 Statistics: {processor_data['statistics']}")
                print(f"📁 Processed Data: {processor_data['processed_data_file']}")
                print(f"📁 Report File: {processor_data['processing_report_file']}")
                
                # Final Summary
                print("\n🎉 Complete Flow Test Results:")
                print("-" * 40)
                print(f"Config: {config_data['statistics']['total_channels']} channels")
                print(f"Collection: {youtube_data['statistics']['total_videos']} videos")
                print(f"Processing: {processor_data['statistics']['records_processed']} records")
                print(f"Data Quality: {processor_data['statistics']['data_quality']}")
                
                # File sizes
                print("\n📊 File Sizes:")
                for file_path in [
                    config_data['config_file_path'],
                    youtube_data['raw_data_file'],
                    processor_data['processed_data_file']
                ]:
                    if os.path.exists(file_path):
                        size_kb = round(os.path.getsize(file_path) / 1024, 2)
                        print(f"  {file_path}: {size_kb} KB")
                
                return True
            else:
                print(f"❌ Processing failed: {processor_data.get('error', 'Unknown error')}")
        else:
            print(f"❌ YouTube collection failed: {youtube_data.get('error', 'Unknown error')}")
    else:
        print(f"❌ Config loading failed: {config_data.get('error', 'Unknown error')}")
    
    return False

if __name__ == "__main__":
    success = test_file_communication_pattern()
    if success:
        print("\n✅ File-based communication pattern working perfectly!")
        print("🚀 Ready for CrewAI integration!")
    else:
        print("\n❌ File-based communication pattern needs fixes") 