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

class DataProcessorTool(BaseTool):
    name: str = "Data Processor and Formatter"
    description: str = (
        "Processes, cleans, and standardizes collected data from raw files, "
        "saves processed output to files, and returns processing statistics."
    )
    args_schema: Type[BaseModel] = DataProcessorInput

    def _run(self, raw_data_file: str = "output/raw_youtube_data.json", transcripts_dir: str = "transcripts/") -> str:
        """Execute data processing from raw data files."""
        try:
            # Load raw data from file
            raw_data = self._load_raw_data(raw_data_file)
            if not raw_data:
                return json.dumps({
                    "status": "error",
                    "error": "Could not load raw data file",
                    "processing_time": datetime.now().isoformat()
                })
            
            # Process the data
            processed_data = self._process_youtube_data(raw_data)
            
            # Save processed data to files
            processed_file = "output/processed_data.json"
            report_file = "output/processing_report.json"
            
            self._save_processed_data(processed_data, processed_file)
            processing_report = self._generate_processing_report(processed_data, raw_data)
            self._save_processing_report(processing_report, report_file)
            
            # Generate summary statistics
            summary_stats = self._generate_summary_statistics(processed_data)
            
            return json.dumps({
                "status": "success",
                "processing_time": datetime.now().isoformat(),
                "processed_data_file": processed_file,
                "processing_report_file": report_file,
                "statistics": summary_stats,
                "summary": f"Processed {summary_stats['records_processed']} records with {summary_stats['data_quality']} quality"
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

    def _save_processing_report(self, report: Dict, report_file: str):
        """Save processing report to file."""
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def _generate_processing_report(self, processed_data: Dict, raw_data: Dict) -> Dict:
        """Generate comprehensive processing report."""
        return {
            "processing_metadata": {
                "processing_time": datetime.now().isoformat(),
                "processor_version": "1.0",
                "raw_data_source": raw_data.get("metadata", {}).get("source", "unknown")
            },
            "data_transformation": {
                "raw_records": len(raw_data.get("data", [])),
                "processed_records": len(processed_data.get("videos", [])),
                "transformation_success_rate": round((len(processed_data.get("videos", [])) / max(len(raw_data.get("data", [])), 1)) * 100, 1)
            },
            "quality_metrics": processed_data.get("statistics", {}),
            "file_outputs": {
                "processed_data": "output/processed_data.json",
                "transcripts_directory": "transcripts/",
                "report_file": "output/processing_report.json"
            }
        }

    def _generate_summary_statistics(self, processed_data: Dict) -> Dict:
        """Generate summary statistics for the response."""
        stats = processed_data.get("statistics", {})
        
        return {
            "records_processed": stats.get("collection", {}).get("total_videos", 0),
            "channels_processed": stats.get("collection", {}).get("total_channels", 0),
            "transcripts_available": stats.get("transcripts", {}).get("available", 0),
            "transcript_availability_rate": f"{stats.get('transcripts', {}).get('availability_rate', 0)}%",
            "total_words_processed": stats.get("transcripts", {}).get("total_words", 0),
            "data_quality": "high" if stats.get("transcripts", {}).get("availability_rate", 0) > 80 else "medium",
            "processing_success": True
        }

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

    def _save_processed_data(self, processed_data: Dict, output_file: str):
        """Save processed data to file."""
        # Create directory if it doesn't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False) 