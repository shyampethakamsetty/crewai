# src/data_collection/tools/youtube_collection_tool.py
from crewai.tools import BaseTool
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
import json
import os
import time
import http.client
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class YouTubeCollectionInput(BaseModel):
    """Input schema for YouTube Collection Tool."""
    validated_config_file: str = Field(default="output/validated_config.json", description="Path to validated configuration file")
    hours_back: int = Field(default=24, description="Hours back to collect videos from")
    video_batch_size: int = Field(default=75, description="Number of videos per batch")

class YouTubeCollectionTool(BaseTool):
    name: str = "YouTube Data Collector"
    description: str = (
        "Collects YouTube video data and transcripts from configured channels, "
        "saves raw data to files, and returns collection statistics."
    )
    args_schema: Type[BaseModel] = YouTubeCollectionInput

    def _run(self, validated_config_file: str = "output/validated_config.json", hours_back: int = 24, video_batch_size: int = 75) -> str:
        """Execute YouTube data collection from validated config file."""
        try:
            # Load validated configuration
            config_data = self._load_validated_config(validated_config_file)
            if not config_data:
                return json.dumps({
                    "status": "error",
                    "error": "Could not load validated configuration",
                    "collection_time": datetime.now().isoformat()
                })
            
            # Extract channel IDs
            channel_ids = [ch["channel_id"] for ch in config_data.get("channels", []) if ch.get("active", True)]
            
            if not channel_ids:
                return json.dumps({
                    "status": "error",
                    "error": "No active channels found in configuration",
                    "collection_time": datetime.now().isoformat()
                })
            
            # Collect YouTube data
            results = self._collect_youtube_data(channel_ids, hours_back, video_batch_size)
            
            if not results:
                return json.dumps({
                    "status": "error",
                    "error": "YouTube collection returned no results",
                    "collection_time": datetime.now().isoformat()
                })
            
            # Save raw data to file
            raw_data_file = "output/raw_youtube_data.json"
            collection_stats = self._save_raw_data_and_get_stats(results, raw_data_file)
            
            return json.dumps({
                "status": "success",
                "collection_time": datetime.now().isoformat(),
                "raw_data_file": raw_data_file,
                "transcripts_directory": "transcripts/",
                "statistics": collection_stats,
                "summary": f"Collected {collection_stats['total_videos']} videos from {collection_stats['total_channels']} channels"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "collection_time": datetime.now().isoformat()
            })

    def _load_validated_config(self, config_file: str) -> Dict:
        """Load validated configuration from file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config file {config_file}: {e}")
            return None

    def _save_raw_data_and_get_stats(self, results: List[Dict], output_file: str) -> Dict:
        """Save raw collection data to file and return statistics."""
        try:
            # Create output directory
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for saving (without full transcripts)
            raw_data = {
                "metadata": {
                    "collection_time": datetime.now().isoformat(),
                    "data_version": "1.0",
                    "source": "youtube_collection_tool"
                },
                "data": []
            }
            
            # Process results and calculate statistics
            total_videos = 0
            total_transcripts = 0
            total_channels = set()
            total_words = 0
            
            for item in results:
                # Remove full transcript text before saving
                processed_item = self._convert_to_json_serializable(item)
                raw_data["data"].append(processed_item)
                
                # Calculate statistics
                if "video_info" in item:
                    total_videos += 1
                    if "channel_id" in item.get("video_info", {}):
                        total_channels.add(item["video_info"]["channel_id"])
                
                if "transcript_stats" in processed_item:
                    stats = processed_item["transcript_stats"]
                    if stats.get("available", False):
                        total_transcripts += 1
                        total_words += stats.get("word_count", 0)
            
            # Save raw data
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
            # Return statistics
            return {
                "total_videos": total_videos,
                "total_channels": len(total_channels),
                "total_transcripts": total_transcripts,
                "transcript_availability_rate": round((total_transcripts / total_videos) * 100, 1) if total_videos > 0 else 0,
                "total_words": total_words,
                "avg_words_per_video": round(total_words / total_videos, 1) if total_videos > 0 else 0,
                "raw_data_file_size": os.path.getsize(output_file) if os.path.exists(output_file) else 0
            }
            
        except Exception as e:
            print(f"Error saving raw data: {e}")
            return {
                "total_videos": 0,
                "total_channels": 0,
                "total_transcripts": 0,
                "error": str(e)
            }

    def _convert_to_json_serializable(self, data):
        """Convert data to JSON serializable format."""
        if isinstance(data, list):
            return [self._convert_to_json_serializable(item) for item in data]
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Skip full transcript text to reduce payload size
                if key == "transcript_only_text":
                    # Save transcript to separate file and add statistics
                    if value and isinstance(value, str):
                        video_id = data.get("video_info", {}).get("video_id", "unknown")
                        transcript_stats = self._save_transcript_and_get_stats(value, video_id)
                        result["transcript_stats"] = transcript_stats
                    continue
                result[key] = self._convert_to_json_serializable(value)
            return result
        elif hasattr(data, 'isoformat'):  # datetime objects
            return data.isoformat()
        else:
            return data

    def _save_transcript_and_get_stats(self, transcript_text: str, video_id: str) -> dict:
        """Save transcript to file and return statistics."""
        try:
            # Create transcripts directory
            transcript_dir = "transcripts"
            os.makedirs(transcript_dir, exist_ok=True)
            
            # Save transcript to file
            transcript_file = os.path.join(transcript_dir, f"{video_id}_transcript.txt")
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(transcript_text)
            
            # Calculate statistics
            word_count = len(transcript_text.split()) if transcript_text else 0
            char_count = len(transcript_text) if transcript_text else 0
            estimated_reading_time = round(word_count / 200, 1) if word_count > 0 else 0
            
            return {
                "available": True,
                "word_count": word_count,
                "character_count": char_count,
                "estimated_reading_time_minutes": estimated_reading_time,
                "transcript_file": transcript_file,
                "file_size_bytes": len(transcript_text.encode('utf-8'))
            }
            
        except Exception as e:
            print(f"Warning: Could not save transcript for {video_id}: {e}")
            return {
                "available": False,
                "word_count": 0,
                "character_count": 0,
                "estimated_reading_time_minutes": 0,
                "error": str(e)
            }

    def _collect_youtube_data(self, channel_ids: List[str], hours_back: int, video_batch_size: int) -> List[Dict]:
        """Core YouTube collection logic (adapted from your existing code)."""
        try:
            # Get Apify token
            apify_token = self._get_apify_token()
            
            all_results = []
            total_videos = 0
            total_transcripts = 0
            
            # Step 1: Get videos from ALL channels at once
            print(f"📡 Fetching videos from {len(channel_ids)} channels...")
            videos = self._get_channel_videos_batch(channel_ids, hours_back, apify_token)
            total_videos = len(videos) if videos else 0
            
            if not videos:
                print("❌ No videos found")
                return []
            
            # Step 2: Process videos in batches for transcripts
            video_ids = [video['video_id'] for video in videos]
            
            for j in range(0, len(video_ids), video_batch_size):
                video_batch = video_ids[j:j + video_batch_size]
                video_batch_num = (j // video_batch_size) + 1
                video_total_batches = (len(video_ids) + video_batch_size - 1) // video_batch_size
                
                print(f"📝 Processing video batch {video_batch_num}/{video_total_batches} ({len(video_batch)} videos)")
                
                # Get transcripts for this batch
                transcript_results = self._run_transcript_scraper_batch(video_batch, apify_token)
                
                if transcript_results:
                    transcript_map = self._format_transcript_data_batch(transcript_results, video_batch)
                    
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
                if j + video_batch_size < len(video_ids):
                    print(f"  ⏳ Waiting 2 seconds...")
                    time.sleep(2)
            
            print(f"📊 Collection complete: {total_videos} videos, {total_transcripts} transcripts")
            return all_results
            
        except Exception as e:
            print(f"❌ Error in _collect_youtube_data: {e}")
            return []

    def _get_apify_token(self) -> str:
        """Get Apify API token from environment variables"""
        token = os.getenv('APIFY_API_TOKEN')
        if not token:
            raise ValueError("APIFY_API_TOKEN not found in environment variables")
        return token

    def _get_channel_videos_batch(self, channel_ids: List[str], hours_back: int, apify_token: str) -> List[Dict]:
        """Get recent videos from a batch of YouTube channels"""
        print(f"📡 Fetching videos from {len(channel_ids)} channels...")
        
        # Calculate the date filter
        cutoff_date = (datetime.utcnow() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')
        
        # Prepare channel URLs
        channel_urls = []
        for channel_id in channel_ids:
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
        url = f"/v2/acts/streamers~youtube-channel-scraper/run-sync-get-dataset-items?token={apify_token}"
        
        print(f"🚀 Starting batch channel scraper for {len(channel_ids)} channels...")
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

    def _run_transcript_scraper_batch(self, video_ids_batch: List[str], apify_token: str) -> List[Dict]:
        """Run transcript scraper for a batch of video IDs"""
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

    def _format_transcript_data_batch(self, transcript_results: List[Dict], video_ids: List[str]) -> Dict[str, Dict]:
        """Format batch transcript data and match with video IDs"""
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