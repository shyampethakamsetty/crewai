from crewai.tools import BaseTool
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
import json
import os
import re
from datetime import datetime
from pathlib import Path

class DataProcessorInput(BaseModel):
    """Input schema for Data Processor Tool."""
    raw_data_file: str = Field(default="output/raw_youtube_data.json", description="Path to raw data file from YouTube collection")
    transcripts_dir: str = Field(default="transcripts/", description="Directory containing transcript files")
    output_dir: str = Field(default="output", description="Output directory for saving processed files")

class DataProcessorTool(BaseTool):
    name: str = "Data Processor and Formatter"
    description: str = (
        "Processes, cleans, and standardizes collected data from raw files, "
        "saves processed output to files, and returns processing statistics."
    )
    args_schema: Type[BaseModel] = DataProcessorInput

    def _run(self, raw_data_file: str = "output/raw_youtube_data.json", transcripts_dir: str = "transcripts/", output_dir: str = "output") -> str:
        """Execute data processing from raw data files."""
        try:
            # Check if output file already exists
            processed_file = f"{output_dir}/youtube_processed.json"
            if os.path.exists(processed_file):
                # Load existing file and return skip status
                existing_stats = self._get_existing_file_stats(processed_file)
                return json.dumps({
                    "status": "skipped",
                    "reason": "Output file already exists",
                    "processing_time": datetime.now().isoformat(),
                    "processed_file": processed_file,
                    "output_directory": output_dir,
                    "existing_statistics": existing_stats,
                    "summary": f"Skipped processing - found existing file with {existing_stats.get('total_videos_collected', 0)} videos"
                }, indent=2)
            
            # Load raw data from file (now from the date-based directory)
            raw_data = self._load_raw_data(f"{output_dir}/raw_youtube_data.json")
            if not raw_data:
                return json.dumps({
                    "status": "error",
                    "error": "Could not load raw data file",
                    "processing_time": datetime.now().isoformat()
                })
            
            # Process the data into simplified normalized structure
            normalized_data = self._create_simplified_normalized_data(raw_data)
            
            # Save normalized data
            self._save_simplified_data_with_stats(normalized_data, raw_data, processed_file)
            
            # Generate basic statistics
            stats = self._generate_basic_statistics(raw_data)
            
            return json.dumps({
                "status": "success",
                "processing_time": datetime.now().isoformat(),
                "processed_file": processed_file,
                "output_directory": output_dir,
                "total_transcript_hours": stats["total_transcript_hours"],
                "total_videos_collected": stats["total_videos_collected"],
                "total_transcripts_collected": stats["total_transcripts_collected"],
                "summary": f"Processed {stats['total_videos_collected']} videos with {stats['total_transcripts_collected']} transcripts"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "processing_time": datetime.now().isoformat()
            })

    def _load_raw_data(self, raw_data_file: str) -> Dict:
        """Load raw data from file."""
        try:
            with open(raw_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading raw data file {raw_data_file}: {e}")
            return None

    def _get_existing_file_stats(self, output_file: str) -> Dict:
        """Get statistics from existing output file."""
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # Extract statistics from the existing file structure
            if isinstance(existing_data, dict):
                return {
                    "total_videos_collected": existing_data.get("total_videos_collected", 0),
                    "total_transcripts_collected": existing_data.get("total_transcripts_collected", 0),
                    "total_transcript_hours": existing_data.get("total_transcript_hours", 0.0),
                    "data_records": len(existing_data.get("data", []))
                }
            else:
                return {"error": "Invalid file format", "total_videos_collected": 0}
        except Exception as e:
            return {"error": f"Could not read existing file: {str(e)}", "total_videos_collected": 0}

    def _create_simplified_normalized_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Create simplified normalized data structure with only source, trader, data."""
        normalized_records = []
        
        # raw_data is now a list directly (no metadata wrapper)
        for item in raw_data:
            channel_info = item.get("channel_info", {})
            transcript_data = item.get("transcript_data", {})
            
            # Only include records with available transcripts
            if transcript_data.get("transcript_available", False):
                transcript_text = transcript_data.get("transcript_only_text", "")
                if transcript_text:
                    # Create simplified normalized record
                    normalized_record = {
                        "source": "youtube",
                        "trader": channel_info.get("channel_name", "Unknown Channel"),
                        "data": transcript_text
                    }
                    
                    normalized_records.append(normalized_record)
        
        return normalized_records

    def _save_simplified_data_with_stats(self, normalized_data: List[Dict], raw_data: List[Dict], output_file: str):
        """Save simplified normalized data to file with statistics included."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate statistics from raw data for accuracy
        stats = self._generate_basic_statistics(raw_data)
        
        # Create the final structure with data and statistics
        final_data = {
            "data": normalized_data,
            "total_transcript_hours": stats["total_transcript_hours"],
            "total_videos_collected": stats["total_videos_collected"],
            "total_transcripts_collected": stats["total_transcripts_collected"]
        }
        
        # Save with statistics included
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)

    def _generate_basic_statistics(self, raw_data: List[Dict]) -> Dict:
        """Generate basic statistics - only the three requested metrics."""
        total_videos = len(raw_data)
        total_transcripts = 0
        total_duration_seconds = 0
        
        for item in raw_data:
            # Check transcript availability
            transcript_data = item.get("transcript_data", {})
            if transcript_data.get("transcript_available", False):
                total_transcripts += 1
            
            # Calculate total duration
            video_info = item.get("video_info", {})
            duration = video_info.get("duration", "")
            if duration:
                total_duration_seconds += self._parse_duration_to_seconds(duration)
        
        return {
            "total_videos_collected": total_videos,
            "total_transcripts_collected": total_transcripts,
            "total_transcript_hours": round(total_duration_seconds / 3600, 2)
        }

    def _parse_duration_to_seconds(self, duration_str: str) -> int:
        """Parse YouTube duration string to seconds."""
        try:
            # Handle PT format (PT1H2M3S) or simple format (1:02:03)
            if duration_str.startswith('PT'):
                # Parse PT format
                import re
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

    def _process_youtube_data(self, raw_data: Dict) -> Dict:
        """Process and normalize YouTube data."""
        processed = {
            "metadata": {
                "collection_time": raw_data.get("collection_time"),
                "total_videos": raw_data.get("total_videos", 0),
                "processing_time": datetime.now().isoformat(),
                "data_version": "1.0"
            },
            "channels": [],
            "videos": [],
            "statistics": {}
        }
        
        # Process each video
        for item in raw_data.get("data", []):
            # Extract and normalize channel info
            channel_info = self._normalize_channel_info(item.get("channel_info", {}))
            
            # Extract and normalize video info
            video_info = self._normalize_video_info(item.get("video_info", {}))
            
            # Process transcript data
            transcript_data = item.get("transcript_data", {})
            transcript_stats = self._process_transcript_data(transcript_data, video_info["video_id"])
            
            # Add to processed data
            processed["channels"].append(channel_info)
            processed["videos"].append({
                **video_info,
                "transcript_stats": transcript_stats
            })
        
        # Remove duplicates and generate statistics
        processed["channels"] = self._deduplicate_channels(processed["channels"])
        processed["statistics"] = self._generate_statistics(processed)
        
        return processed

    def _normalize_channel_info(self, channel_info: Dict) -> Dict:
        """Normalize channel information."""
        return {
            "channel_id": channel_info.get("channel_id", "").strip(),
            "channel_name": self._clean_text(channel_info.get("channel_name", "")),
            "platform": "youtube"
        }

    def _normalize_video_info(self, video_info: Dict) -> Dict:
        """Normalize video information."""
        return {
            "video_id": video_info.get("video_id", "").strip(),
            "title": self._clean_text(video_info.get("title", "")),
            "published_date": video_info.get("published_date"),
            "channel_name": self._clean_text(video_info.get("channel_name", "")),
            "channel_id": video_info.get("channel_id", "").strip(),
            "video_url": video_info.get("video_url", ""),
            "view_count": self._normalize_number(video_info.get("view_count")),
            "like_count": self._normalize_number(video_info.get("like_count")),
            "duration": self._normalize_duration(video_info.get("duration")),
            "thumbnail_url": video_info.get("thumbnail_url", "")
        }

    def _process_transcript_data(self, transcript_data: Dict, video_id: str) -> Dict:
        """Process transcript data and save full text separately."""
        transcript_text = transcript_data.get("transcript_only_text", "")
        
        # Calculate statistics
        stats = {
            "available": transcript_data.get("transcript_available", False),
            "length": transcript_data.get("transcript_length", 0),
            "word_count": len(transcript_text.split()) if transcript_text else 0,
            "character_count": len(transcript_text) if transcript_text else 0,
            "estimated_reading_time_minutes": round(len(transcript_text.split()) / 200, 1) if transcript_text else 0
        }
        
        # Save full transcript to separate file if available
        if transcript_text and stats["available"]:
            transcript_file = f"transcripts/{video_id}_transcript.txt"
            self._save_transcript_file(transcript_text, transcript_file)
            stats["transcript_file"] = transcript_file
        
        return stats

    def _save_transcript_file(self, transcript_text: str, file_path: str):
        """Save full transcript text to separate file."""
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Clean and save transcript
            cleaned_text = self._clean_transcript_text(transcript_text)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
                
        except Exception as e:
            print(f"Warning: Could not save transcript file {file_path}: {e}")

    def _clean_transcript_text(self, text: str) -> str:
        """Clean transcript text."""
        if not text:
            return ""
        
        # Remove excessive newlines
        text = re.sub(r'\n+', '\n', text)
        
        # Remove excessive spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove music/sound annotations
        text = re.sub(r'\[Music\]|\[Applause\]|\[Laughter\]', '', text)
        
        # Clean up quotes and special characters
        text = text.replace('\\"', '"')
        text = text.replace('\\n', '\n')
        
        return text.strip()

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text fields."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might cause issues
        text = text.replace('\\"', '"')
        text = text.replace('\\n', ' ')
        
        return text.strip()

    def _normalize_number(self, value) -> int:
        """Normalize numeric values."""
        if value is None:
            return 0
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def _normalize_duration(self, duration) -> str:
        """Normalize duration format."""
        if not duration or duration == "Unknown":
            return "00:00"
        
        # If it's already in MM:SS or HH:MM:SS format, return as is
        if isinstance(duration, str) and re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', duration):
            return duration
        
        return str(duration)

    def _deduplicate_channels(self, channels: List[Dict]) -> List[Dict]:
        """Remove duplicate channels."""
        seen = set()
        unique_channels = []
        
        for channel in channels:
            channel_id = channel.get("channel_id")
            if channel_id and channel_id not in seen:
                seen.add(channel_id)
                unique_channels.append(channel)
        
        return unique_channels

    def _generate_statistics(self, processed_data: Dict) -> Dict:
        """Generate comprehensive statistics."""
        videos = processed_data["videos"]
        channels = processed_data["channels"]
        
        # Basic counts
        total_videos = len(videos)
        total_channels = len(channels)
        
        # Transcript statistics
        videos_with_transcripts = sum(1 for v in videos if v["transcript_stats"]["available"])
        total_words = sum(v["transcript_stats"]["word_count"] for v in videos)
        avg_words_per_video = round(total_words / total_videos, 1) if total_videos > 0 else 0
        
        # View statistics
        total_views = sum(v["view_count"] for v in videos)
        avg_views = round(total_views / total_videos, 1) if total_videos > 0 else 0
        
        return {
            "collection": {
                "total_videos": total_videos,
                "total_channels": total_channels,
                "success_rate": round((videos_with_transcripts / total_videos) * 100, 1) if total_videos > 0 else 0
            },
            "transcripts": {
                "available": videos_with_transcripts,
                "availability_rate": round((videos_with_transcripts / total_videos) * 100, 1) if total_videos > 0 else 0,
                "total_words": total_words,
                "avg_words_per_video": avg_words_per_video
            },
            "engagement": {
                "total_views": total_views,
                "avg_views_per_video": avg_views,
                "total_likes": sum(v["like_count"] for v in videos)
            }
        } 