#!/usr/bin/env python3
"""
YouTube Mass Channel Transcript Collector
Optimized for processing 179+ channels with efficient batching and progress tracking
"""

import http.client
import json
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration settings
RATE_LIMIT_CONFIG = {
    'process_all_channels_at_once': True,  # Process all channels in one API call
    'video_batch_size': 75,      # Process 75 videos per transcript batch (optimized based on testing)
    'apify_request_delay': 2,    # Seconds between Apify requests
    'max_apify_retries': 3,      # Maximum retry attempts for Apify
    'request_timeout': 30,       # Timeout for HTTP requests
}

def load_channel_ids_from_json():
    """
    Load all channel IDs from the config/channels.json file
    """
    try:
        channels_file = "config/channels.json"
        if not os.path.exists(channels_file):
            print(f"❌ Channels file not found: {channels_file}")
            return []
        
        with open(channels_file, 'r', encoding='utf-8') as f:
            channels_data = json.load(f)
        
        # Extract channel IDs from the JSON structure
        channel_ids = []
        for channel in channels_data:
            if 'channel_id' in channel:
                channel_ids.append(channel['channel_id'])
        
        print(f"✅ Loaded {len(channel_ids)} channels from {channels_file}")
        return channel_ids
        
    except Exception as e:
        print(f"❌ Error loading channels: {e}")
        return []

def get_apify_token():
    """Get Apify API token from environment variables"""
    token = os.getenv('APIFY_API_TOKEN')
    if not token:
        raise ValueError("APIFY_API_TOKEN not found in environment variables")
    return token

def get_channel_videos_batch(channel_ids_batch: list, hours_back: int = 24):
    """
    Get recent videos from a batch of YouTube channels
    """
    print(f"📡 Fetching videos from {len(channel_ids_batch)} channels...")
    
    # Calculate the date filter
    cutoff_date = (datetime.utcnow() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')
    
    # Prepare channel URLs
    channel_urls = []
    for channel_id in channel_ids_batch:
        channel_url = f"https://www.youtube.com/channel/{channel_id}"
        channel_urls.append({"url": channel_url})
    
    # Prepare the input for the channel scraper
    payload = json.dumps({
        "startUrls": channel_urls,
        "maxResults": 20,  # Reduced to 20 videos per channel for efficiency
        "oldestPostDate": cutoff_date,
        "sortVideosBy": "NEWEST"
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Use the sync endpoint
    url = f"/v2/acts/streamers~youtube-channel-scraper/run-sync-get-dataset-items?token={get_apify_token()}"
    
    print(f"🚀 Starting batch channel scraper for {len(channel_ids_batch)} channels...")
    print(f"📅 Filtering videos published after: {cutoff_date}")
    
    conn = http.client.HTTPSConnection("api.apify.com")
    conn.request("POST", url, payload, headers)
    res = conn.getresponse()
    data = res.read()
    
    if res.status not in [200, 201]:
        print(f"❌ Error from Apify API: {res.status} - {data.decode('utf-8')}")
        return []
    
    try:
        results = json.loads(data.decode("utf-8"))
        print(f"✅ Retrieved {len(results)} video items")
        
        # Filter videos by date
        videos = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        for item in results:
            try:
                if item.get('type') == 'video':
                    published_str = item.get('publishedAt', '')
                    if published_str:
                        published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                        published_date_naive = published_date.replace(tzinfo=None)
                    else:
                        published_date_naive = datetime.utcnow()
                    
                    if published_date_naive >= cutoff_time:
                        video_info = {
                            'video_id': item.get('id', ''),
                            'title': item.get('title', 'Unknown Title'),
                            'published_date': published_date_naive,
                            'channel_name': item.get('channelName', 'Unknown Channel'),
                            'channel_id': item.get('channelId', ''),
                            'video_url': item.get('url', ''),
                            'view_count': item.get('viewCount', 0),
                            'like_count': item.get('likeCount', 0),
                            'duration': item.get('duration', 'Unknown'),
                            'thumbnail_url': item.get('thumbnailUrl', '')
                        }
                        videos.append(video_info)
                        
            except Exception as e:
                print(f"  ❌ Error parsing video item: {e}")
                continue
        
        print(f"📊 Found {len(videos)} videos from the last {hours_back} hours")
        return videos
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON response: {e}")
        return []

def run_transcript_scraper_batch(video_ids_batch: list, apify_token: str):
    """
    Run transcript scraper for a batch of video IDs
    """
    conn = http.client.HTTPSConnection("api.apify.com")
    
    # Prepare video URLs for batch processing
    video_urls = []
    for video_id in video_ids_batch:
        video_urls.append({"url": f"https://www.youtube.com/watch?v={video_id}"})
    
    # Prepare the input for the transcript extractor
    payload = json.dumps({
        "youtubeUrl": video_urls,
        "transcriptOnly": True
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Use the sync endpoint
    url = f"/v2/acts/dz_omar~youtube-transcript-extractor/run-sync-get-dataset-items?token={apify_token}"
    
    print(f"🚀 Extracting transcripts for {len(video_ids_batch)} videos...")
    
    conn.request("POST", url, payload, headers)
    res = conn.getresponse()
    data = res.read()
    
    if res.status not in [200, 201]:
        print(f"❌ Error from Apify API: {res.status} - {data.decode('utf-8')}")
        return None
    
    try:
        results = json.loads(data.decode("utf-8"))
        return results
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON response: {e}")
        return None

def format_transcript_data_batch(transcript_results, video_ids):
    """
    Format batch transcript data and match with video IDs
    """
    if not transcript_results:
        return {}
    
    transcript_map = {}
    
    for item in transcript_results:
        try:
            video_url = item.get('VideoURL', '')
            video_id = video_url.split('/')[-1] if video_url else ''
            
            if video_id:
                transcript_data = {
                    "transcript_available": item.get('hasTranscript', False),
                    "transcript_length": len(item.get('timestamps', [])),
                    "transcript_only_text": item.get('transcriptText', '')
                }
                transcript_map[video_id] = transcript_data
                
        except Exception as e:
            print(f"    ❌ Error parsing transcript item: {e}")
            continue
    
    # Create entries for videos without transcripts
    for video_id in video_ids:
        if video_id not in transcript_map:
            transcript_map[video_id] = {
                "transcript_available": False,
                "transcript_length": 0,
                "transcript_only_text": ""
            }
    
    return transcript_map

def main():
    """Main function optimized for mass channel processing"""
    hours_back = 24
    
    print(f"🎬 YouTube Mass Channel Transcript Collector")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚙️ Video batch size: {RATE_LIMIT_CONFIG['video_batch_size']}")
    print("-" * 60)
    
    # Load channel IDs from JSON file
    channel_ids = load_channel_ids_from_json()
    if not channel_ids:
        print("❌ No channels loaded. Exiting.")
        return
    
    print(f"📺 Total Channels: {len(channel_ids)}")
    print(f"⏰ Time range: Last {hours_back} hours")
    print("-" * 60)
    
    try:
        apify_token = get_apify_token()
        print("✅ Apify token retrieved")
        
        all_results = []
        total_videos = 0
        total_transcripts = 0
        
        # Step 1: Get videos from ALL channels at once
        print(f"\n📡 Step 1: Fetching videos from ALL {len(channel_ids)} channels at once...")
        videos = get_channel_videos_batch(channel_ids, hours_back)
        total_videos = len(videos)
        
        if not videos:
            print("❌ No videos found")
            return
        
        # Step 2: Process videos in batches for transcripts
        video_ids = [video['video_id'] for video in videos]
        
        for j in range(0, len(video_ids), RATE_LIMIT_CONFIG['video_batch_size']):
            video_batch = video_ids[j:j + RATE_LIMIT_CONFIG['video_batch_size']]
            video_batch_num = (j // RATE_LIMIT_CONFIG['video_batch_size']) + 1
            video_total_batches = (len(video_ids) + RATE_LIMIT_CONFIG['video_batch_size'] - 1) // RATE_LIMIT_CONFIG['video_batch_size']
            
            print(f"\n📝 Step 2: Processing video batch {video_batch_num}/{video_total_batches} ({len(video_batch)} videos)")
            
            # Get transcripts for this batch
            transcript_results = run_transcript_scraper_batch(video_batch, apify_token)
            
            if transcript_results:
                transcript_map = format_transcript_data_batch(transcript_results, video_batch)
                
                # Combine with video info
                for video_info in videos:
                    if video_info['video_id'] in video_batch:
                        video_id = video_info['video_id']
                        transcript_data = transcript_map.get(video_id)
                        
                        if transcript_data and transcript_data['transcript_available']:
                            total_transcripts += 1
                        
                        combined_data = {
                            'channel_info': {
                                'channel_id': video_info['channel_id'],
                                'channel_name': video_info['channel_name']
                            },
                            'video_info': video_info,
                            'transcript_data': transcript_data
                        }
                        all_results.append(combined_data)
            
            # Rate limiting between video batches
            if j + RATE_LIMIT_CONFIG['video_batch_size'] < len(video_ids):
                print(f"  ⏳ Waiting {RATE_LIMIT_CONFIG['apify_request_delay']} seconds...")
                time.sleep(RATE_LIMIT_CONFIG['apify_request_delay'])
        
        # Save results
        print(f"\n💾 Saving results...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"youtube_mass_channel_transcripts_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
        
        # Final summary
        print(f"\n" + "=" * 60)
        print(f"📊 MASS COLLECTION COMPLETE")
        print(f"=" * 60)
        print(f"📺 Channels Processed: {len(channel_ids)}")
        print(f"🎬 Total Videos Found: {total_videos}")
        print(f"✅ Successful Transcripts: {total_transcripts}")
        print(f"📈 Success Rate: {(total_transcripts/total_videos*100):.1f}%" if total_videos > 0 else "0%")
        print(f"💾 Results saved to: {output_file}")
        print(f"⏱️ Total time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 