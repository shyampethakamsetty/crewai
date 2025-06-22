# src/data_collection/tools/config_loader_tool.py
from crewai.tools import BaseTool
from typing import Type, List, Dict
from pydantic import BaseModel, Field
import json
import os
from datetime import datetime
from pathlib import Path

class ConfigLoaderInput(BaseModel):
    """Input schema for Config Loader Tool."""
    config_path: str = Field(default="config/channels.json", description="Path to the configuration file")

class ConfigLoaderTool(BaseTool):
    name: str = "Configuration Loader and Validator"
    description: str = (
        "Loads and validates data collection configuration from JSON files, "
        "saves validated config to output file, and returns summary statistics."
    )
    args_schema: Type[BaseModel] = ConfigLoaderInput

    def _run(self, config_path: str = "config/channels.json") -> str:
        """Load and validate configuration, save to file, return statistics."""
        try:
            # Load configuration
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate and process configuration
            validated_config = self._validate_configuration(config_data)
            
            # Save validated configuration to output file
            output_file = "output/validated_config.json"
            self._save_validated_config(validated_config, output_file)
            
            # Generate statistics
            stats = self._generate_config_statistics(validated_config)
            
            return json.dumps({
                "status": "success",
                "validation_time": datetime.now().isoformat(),
                "config_file_path": output_file,
                "statistics": stats,
                "summary": f"Successfully validated {stats['total_channels']} channels"
            }, indent=2)
            
        except FileNotFoundError:
            return json.dumps({
                "status": "error",
                "error": f"Configuration file not found: {config_path}",
                "validation_time": datetime.now().isoformat()
            })
        except json.JSONDecodeError as e:
            return json.dumps({
                "status": "error", 
                "error": f"Invalid JSON in config file: {str(e)}",
                "validation_time": datetime.now().isoformat()
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": f"Configuration validation failed: {str(e)}",
                "validation_time": datetime.now().isoformat()
            })

    def _validate_configuration(self, config_data: Dict) -> Dict:
        """Validate and normalize configuration data."""
        validated = {
            "metadata": {
                "validation_time": datetime.now().isoformat(),
                "source_file": "config/channels.json",
                "version": "1.0"
            },
            "channels": [],
            "parameters": {
                "default_hours_back": 24,
                "default_batch_size": 75,
                "max_retries": 3
            }
        }
        
        # Handle both list format and object with channels key
        channels = []
        if isinstance(config_data, list):
            # Direct list format (current channels.json)
            channels = config_data
        elif isinstance(config_data, dict) and "channels" in config_data:
            # Object with channels key
            channels = config_data.get("channels", [])
        else:
            # Fallback
            channels = []
        
        # Process channels
        for channel in channels:
            if self._is_valid_channel(channel):
                validated_channel = {
                    "channel_id": channel.get("channel_id", "").strip(),
                    "channel_name": channel.get("name", channel.get("channel_name", "")).strip(),
                    "platform": "youtube",
                    "active": channel.get("active", True),
                    "validated": True
                }
                validated["channels"].append(validated_channel)
        
        return validated

    def _is_valid_channel(self, channel: Dict) -> bool:
        """Validate individual channel configuration."""
        if not isinstance(channel, dict):
            return False
        
        channel_id = channel.get("channel_id", "").strip()
        if not channel_id:
            return False
        
        # Basic YouTube channel ID validation
        if len(channel_id) != 24 or not channel_id.startswith(('UC', 'UU', 'UL')):
            return False
        
        return True

    def _save_validated_config(self, validated_config: Dict, output_file: str):
        """Save validated configuration to output file."""
        # Create output directory if it doesn't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(validated_config, f, indent=2, ensure_ascii=False)

    def _generate_config_statistics(self, validated_config: Dict) -> Dict:
        """Generate configuration statistics."""
        channels = validated_config.get("channels", [])
        
        return {
            "total_channels": len(channels),
            "active_channels": sum(1 for c in channels if c.get("active", True)),
            "validated_channels": sum(1 for c in channels if c.get("validated", False)),
            "validation_success_rate": round((len(channels) / max(len(channels), 1)) * 100, 1),
            "platforms": ["youtube"],  # Currently only YouTube
            "ready_for_collection": len(channels) > 0
        }