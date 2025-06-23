import json
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import time

from .parallel_processor import ParallelSentenceProcessor

class ParallelSentenceProcessorTool:
    """
    CrewAI tool for parallel sentence processing that splits transcripts into chunks
    and processes them concurrently for significantly improved performance.
    """
    
    def __init__(self, config_path: str = None, max_workers: int = None):
        self.logger = logging.getLogger(__name__)
        self.processor = ParallelSentenceProcessor(config_path, max_workers)
        
        # Output directory setup
        self.output_dir = Path("output") / datetime.now().strftime("%Y%m%d")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Stats tracking
        self.stats_file = self.output_dir / "parallel_processing_stats.json"
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load existing processing statistics"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load stats: {e}")
        
        return {
            "total_transcripts_processed": 0,
            "total_sentences_generated": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "chunks_processed": 0,
            "workers_used": self.processor.max_workers,
            "last_processed": None
        }
    
    def _save_stats(self):
        """Save processing statistics"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save stats: {e}")
    
    def _update_stats(self, result: Dict[str, Any]):
        """Update processing statistics"""
        self.stats["total_transcripts_processed"] += 1
        self.stats["total_sentences_generated"] += result.get("sentence_count", 0)
        self.stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        self.stats["chunks_processed"] += result.get("chunks_processed", 0)
        self.stats["workers_used"] = result.get("workers_used", self.processor.max_workers)
        self.stats["last_processed"] = datetime.now().isoformat()
        
        # Calculate average processing time
        if self.stats["total_transcripts_processed"] > 0:
            self.stats["average_processing_time"] = (
                self.stats["total_processing_time"] / self.stats["total_transcripts_processed"]
            )
        
        self._save_stats()
    
    def process_transcript(self, transcript: str, source: str = "youtube", trader: str = "") -> Dict[str, Any]:
        """
        Process transcript using parallel sentence processing
        
        Args:
            transcript: The transcript text to process
            source: Source of the transcript (default: "youtube")
            trader: Name of the trader/speaker (default: "")
        
        Returns:
            Dictionary containing processed sentences and metadata
        """
        self.logger.info(f"Starting parallel sentence processing for {trader}")
        
        # Check if output already exists (intelligent processing)
        output_file = self.output_dir / f"parallel_sentences_{trader.replace(' ', '_')}.json"
        
        if output_file.exists():
            self.logger.info(f"Output file already exists for {trader}, loading existing results")
            try:
                with open(output_file, 'r') as f:
                    existing_result = json.load(f)
                
                # Update stats with existing data
                self._update_stats(existing_result)
                
                return {
                    "status": "success",
                    "message": f"Loaded existing parallel processing results for {trader}",
                    "data": existing_result,
                    "processing_time": 0.0,
                    "from_cache": True
                }
            except Exception as e:
                self.logger.warning(f"Could not load existing results: {e}")
        
        # Process transcript in parallel
        start_time = time.time()
        
        try:
            result = self.processor.process_sentences(transcript, source, trader)
            
            # Save results
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            processing_time = time.time() - start_time
            
            # Update statistics
            self._update_stats(result)
            
            self.logger.info(f"Parallel processing completed for {trader}")
            self.logger.info(f"Generated {result['sentence_count']} sentences in {processing_time:.2f} seconds")
            self.logger.info(f"Used {result['workers_used']} workers to process {result['chunks_processed']} chunks")
            
            return {
                "status": "success",
                "message": f"Successfully processed transcript for {trader} using parallel processing",
                "data": result,
                "processing_time": processing_time,
                "from_cache": False
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Parallel processing failed for {trader}: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "status": "error",
                "message": error_msg,
                "processing_time": processing_time,
                "from_cache": False
            }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return {
            "stats": self.stats,
            "current_workers": self.processor.max_workers,
            "output_directory": str(self.output_dir)
        }
    
    def configure_workers(self, max_workers: int) -> Dict[str, Any]:
        """Configure the number of parallel workers"""
        if max_workers < 1:
            return {
                "status": "error",
                "message": "Number of workers must be at least 1"
            }
        
        # Reinitialize processor with new worker count
        config_path = getattr(self.processor, 'config_path', None)
        self.processor = ParallelSentenceProcessor(config_path, max_workers)
        
        self.stats["workers_used"] = max_workers
        self._save_stats()
        
        return {
            "status": "success",
            "message": f"Configured parallel processor with {max_workers} workers",
            "workers": max_workers
        }
    
    def get_available_outputs(self) -> Dict[str, Any]:
        """Get list of available processed outputs"""
        outputs = []
        
        if self.output_dir.exists():
            for file in self.output_dir.glob("parallel_sentences_*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    
                    outputs.append({
                        "file": file.name,
                        "trader": data.get("trader", "unknown"),
                        "sentence_count": data.get("sentence_count", 0),
                        "processing_date": data.get("processing_date", ""),
                        "processing_method": data.get("processing_method", ""),
                        "chunks_processed": data.get("chunks_processed", 0),
                        "workers_used": data.get("workers_used", 0),
                        "processing_time": data.get("processing_time_seconds", 0)
                    })
                except Exception as e:
                    self.logger.warning(f"Could not read output file {file}: {e}")
        
        return {
            "status": "success",
            "outputs": outputs,
            "total_outputs": len(outputs)
        }


# CrewAI Tool Function
def parallel_sentence_processing_tool(transcript: str, source: str = "youtube", trader: str = "") -> str:
    """
    CrewAI tool function for parallel sentence processing
    
    Args:
        transcript: The transcript text to process
        source: Source of the transcript (default: "youtube")
        trader: Name of the trader/speaker (default: "")
    
    Returns:
        JSON string with processing results
    """
    # Initialize tool (in practice, this would be a singleton)
    tool = ParallelSentenceProcessorTool()
    
    # Process transcript
    result = tool.process_transcript(transcript, source, trader)
    
    # Return as JSON string for CrewAI
    return json.dumps(result, indent=2)


# Example usage and testing
if __name__ == "__main__":
    # Test the parallel processor
    test_transcript = """
    Apple stock is trading at $150.50 today. The company reported strong earnings growth of 15% year-over-year. 
    AAPL has been performing well in the market. The CEO mentioned that iPhone sales increased by 20% this quarter. 
    Analysts are bullish on the stock with a target price of $175. The market cap is now over $2.5 trillion. 
    Investors are excited about the new product launches scheduled for Q4. The stock price has increased by 25% this year.
    """
    
    tool = ParallelSentenceProcessorTool(max_workers=4)
    
    # Test processing
    result = tool.process_transcript(test_transcript, "youtube", "TestTrader")
    print(json.dumps(result, indent=2))
    
    # Test stats
    stats = tool.get_processing_stats()
    print("\nProcessing Stats:")
    print(json.dumps(stats, indent=2))
    
    # Test available outputs
    outputs = tool.get_available_outputs()
    print("\nAvailable Outputs:")
    print(json.dumps(outputs, indent=2)) 