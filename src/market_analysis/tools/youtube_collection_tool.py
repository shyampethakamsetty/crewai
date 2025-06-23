# src/data_collection/tools/youtube_collection_tool.py
from crewai.tools import BaseTool
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
import json
import os
import time
import http.client
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import re

# Load environment variables
load_dotenv()

class YouTubeCollectionInput(BaseModel):
    """Input schema for YouTube Collection Tool."""
    config_file: str = Field(default="config/youtube_configuration.yaml", description="Path to YouTube configuration file")
    hours_back_override: int = Field(default=None, description="Override hours back from config (optional)")
    video_batch_size_override: int = Field(default=None, description="Override video batch size from config (optional)")
    output_dir: str = Field(default="output", description="Output directory for saving files")

class YouTubeCollectionTool(BaseTool):
    name: str = "YouTube Data Collector"
    description: str = (
        "Collects YouTube video data and transcripts from configured channels, "
        "saves raw data to files, and returns collection statistics."
    )
    args_schema: Type[BaseModel] = YouTubeCollectionInput

    def _run(self, config_file: str = "config/youtube_configuration.yaml", hours_back_override: int = None, video_batch_size_override: int = None, output_dir: str = "output") -> str:
        """Execute YouTube data collection from YAML configuration file."""
        try:
            # Check if output file already exists
            raw_data_file = f"{output_dir}/raw_youtube_data.json"
            if os.path.exists(raw_data_file):
                # Load existing file and return skip status
                existing_stats = self._get_existing_file_stats(raw_data_file)
                return json.dumps({
                    "status": "skipped",
                    "reason": "Output file already exists",
                    "collection_time": datetime.now().isoformat(),
                    "raw_data_file": raw_data_file,
                    "output_directory": output_dir,
                    "existing_statistics": existing_stats,
                    "summary": f"Skipped collection - found existing file with {existing_stats.get('total_videos_collected', 0)} videos"
                }, indent=2)
            
            # Load and validate YouTube configuration
            config_data = self._load_youtube_config(config_file)
            if not config_data:
                return json.dumps({
                    "status": "error",
                    "error": "Could not load YouTube configuration",
                    "collection_time": datetime.now().isoformat()
                })
            
            # Get enabled channels with their specific settings
            channel_configs = self._get_enabled_channels_with_settings(config_data)
            
            if not channel_configs:
                return json.dumps({
                    "status": "error",
                    "error": "No enabled channels found in configuration",
                    "collection_time": datetime.now().isoformat()
                })
            
            # Apply global overrides if provided
            global_settings = config_data.get("global_settings", {})
            hours_back = hours_back_override or global_settings.get("hours_back", 24)
            video_batch_size = video_batch_size_override or global_settings.get("video_batch_size", 75)
            
            # Collect YouTube data with enhanced configuration
            results = self._collect_youtube_data_enhanced(channel_configs, hours_back, video_batch_size, config_data)
            
            if not results:
                return json.dumps({
                    "status": "error",
                    "error": "YouTube collection returned no results",
                    "collection_time": datetime.now().isoformat()
                })
            
            # Save raw data to file with embedded transcripts in date-based directory
            collection_stats = self._save_raw_data_with_transcripts_and_get_stats(results, raw_data_file)
            
            return json.dumps({
                "status": "success",
                "collection_time": datetime.now().isoformat(),
                "raw_data_file": raw_data_file,
                "output_directory": output_dir,
                "statistics": collection_stats,
                "summary": f"Collected {collection_stats['total_videos_collected']} videos from {collection_stats['total_transcripts_collected']} transcripts"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "collection_time": datetime.now().isoformat()
            })

    def _load_youtube_config(self, config_file: str) -> Dict:
        """Load YouTube configuration from YAML file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Validate the configuration structure
            if not self._validate_config_structure(config):
                print(f"Invalid configuration structure in {config_file}")
                return None
                
            return config
        except Exception as e:
            print(f"Error loading YAML config file {config_file}: {e}")
            return None
    
    def _validate_config_structure(self, config: Dict) -> bool:
        """Validate the basic structure of the configuration."""
        required_sections = ['global_settings', 'channels']
        
        for section in required_sections:
            if section not in config:
                print(f"Missing required section: {section}")
                return False
        
        # Validate channels structure
        channels = config.get('channels', [])
        if not isinstance(channels, list) or len(channels) == 0:
            print("Channels section must be a non-empty list")
            return False
            
        for i, channel in enumerate(channels):
            if not isinstance(channel, dict):
                print(f"Channel {i} must be a dictionary")
                return False
            if 'channel_id' not in channel:
                print(f"Channel {i} missing required 'channel_id' field")
                return False
            if not self._is_valid_youtube_channel_id(channel['channel_id']):
                print(f"Channel {i} has invalid YouTube channel ID: {channel['channel_id']}")
                return False
                
        return True
    
    def _is_valid_youtube_channel_id(self, channel_id: str) -> bool:
        """Validate YouTube channel ID format."""
        if not isinstance(channel_id, str):
            return False
        channel_id = channel_id.strip()
        return len(channel_id) == 24 and channel_id.startswith(('UC', 'UU', 'UL'))
    
    def _get_enabled_channels_with_settings(self, config_data: Dict) -> List[Dict]:
        """Extract enabled channels with their settings."""
        channels = config_data.get("channels", [])
        
        enabled_channels = []
        
        for channel in channels:
            if not channel.get("enabled", True):
                continue
                
            # Simple channel configuration
            channel_config = {
                "channel_id": channel["channel_id"],
                "name": channel.get("name", "")
            }
            
            enabled_channels.append(channel_config)
            
        return enabled_channels

    def _get_existing_file_stats(self, output_file: str) -> Dict:
        """Get statistics from existing output file."""
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # Calculate stats from existing data
            total_videos = len(existing_data) if isinstance(existing_data, list) else 0
            total_transcripts = 0
            total_duration_seconds = 0
            
            if isinstance(existing_data, list):
                for item in existing_data:
                    # Check transcript data
                    transcript_data = item.get("transcript_data", {})
                    if transcript_data.get("transcript_available", False):
                        total_transcripts += 1
                    
                    # Parse duration
                    duration = item.get("video_info", {}).get("duration", "")
                    if duration:
                        total_duration_seconds += self._parse_duration_to_seconds(duration)
            
            return {
                "total_videos_collected": total_videos,
                "total_transcripts_collected": total_transcripts,
                "total_transcript_hours": round(total_duration_seconds / 3600, 2)
            }
        except Exception as e:
            return {"error": f"Could not read existing file: {str(e)}", "total_videos_collected": 0}

    def _save_raw_data_with_transcripts_and_get_stats(self, results: List[Dict], output_file: str) -> Dict:
        """Save raw collection data with embedded transcripts to file and return statistics."""
        try:
            # Create output directory
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for saving (no metadata, just the data array)
            processed_data = []
            
            # Process results and calculate statistics
            total_videos = 0
            total_transcripts = 0
            total_duration_seconds = 0
            
            for item in results:
                # Keep full transcript text in the data (don't remove it)
                processed_item = self._convert_to_json_serializable_with_transcripts(item)
                processed_data.append(processed_item)
                
                # Calculate statistics
                if "video_info" in item:
                    total_videos += 1
                    
                    # Parse duration for total hours calculation
                    duration = item.get("video_info", {}).get("duration", "")
                    if duration:
                        total_duration_seconds += self._parse_duration_to_seconds(duration)
                
                # Check transcript data
                transcript_data = item.get("transcript_data", {})
                if transcript_data.get("transcript_available", False):
                    total_transcripts += 1
            
            # Save raw data with embedded transcripts (no metadata wrapper)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            
            # Return only the requested statistics
            return {
                "total_videos_collected": total_videos,
                "total_transcripts_collected": total_transcripts,
                "total_transcript_hours": round(total_duration_seconds / 3600, 2)
            }
            
        except Exception as e:
            print(f"Error saving raw data: {e}")
            return {
                "total_videos_collected": 0,
                "total_transcripts_collected": 0,
                "total_transcript_hours": 0.0,
                "error": str(e)
            }

    def _convert_to_json_serializable_with_transcripts(self, data):
        """Convert data to JSON serializable format while keeping transcripts."""
        if isinstance(data, list):
            return [self._convert_to_json_serializable_with_transcripts(item) for item in data]
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Keep transcript text in the data (don't remove it)
                result[key] = self._convert_to_json_serializable_with_transcripts(value)
            return result
        elif hasattr(data, 'isoformat'):  # datetime objects
            return data.isoformat()
        else:
            return data

    def _parse_duration_to_seconds(self, duration_str: str) -> int:
        """Parse YouTube duration string to seconds."""
        try:
            # Handle PT format (PT1H2M3S) or simple format (1:02:03)
            if duration_str.startswith('PT'):
                # Parse PT format
                duration_str = duration_str[2:]  # Remove 'PT'
                hours = minutes = seconds = 0
                
                # Extract hours
                if 'H' in duration_str:
                    hours_match = re.search(r'(\d+)H', duration_str)
                    if hours_match:
                        hours = int(hours_match.group(1))
                
                # Extract minutes
                if 'M' in duration_str:
                    minutes_match = re.search(r'(\d+)M', duration_str)
                    if minutes_match:
                        minutes = int(minutes_match.group(1))
                
                # Extract seconds
                if 'S' in duration_str:
                    seconds_match = re.search(r'(\d+)S', duration_str)
                    if seconds_match:
                        seconds = int(seconds_match.group(1))
                
                return hours * 3600 + minutes * 60 + seconds
            
            else:
                # Handle simple format (H:MM:SS or M:SS)
                parts = duration_str.split(':')
                if len(parts) == 3:  # H:MM:SS
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:  # M:SS
                    return int(parts[0]) * 60 + int(parts[1])
                else:
                    return int(parts[0])  # Just seconds
                    
        except Exception:
            return 0

    def _collect_youtube_data_enhanced(self, channel_configs: List[Dict], default_hours_back: int, video_batch_size: int, full_config: Dict) -> List[Dict]:
        """Collect YouTube data using simplified configuration."""
        # Extract channel IDs from the simplified config
        channel_ids = [ch["channel_id"] for ch in channel_configs]
        
        # Use the existing collection method
        results = self._collect_youtube_data(channel_ids, default_hours_back, video_batch_size)
        
        # Add basic channel names to results if available
        for result in results:
            channel_id = result.get("video_info", {}).get("channel_id")
            if channel_id:
                # Find the channel name from our config
                for ch_config in channel_configs:
                    if ch_config["channel_id"] == channel_id:
                        result["channel_config"] = {
                            "name": ch_config["name"]
                        }
                        break
        
        return results
    


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