# src/data_collection/main.py
import os
from datetime import datetime
from market_analysis.crew import DataCollectionCrew
from market_analysis.utils.crewai_logger import CrewAILogger

def run():
    """Run the simplified data collection crew with comprehensive logging."""
    # Generate date-based directory names (date only, no time)
    date_now = datetime.now().strftime("%Y%m%d")
    output_dir = f"output/{date_now}"
    logs_dir = f"logs/{date_now}"
    
    # Create date-based directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Initialize the advanced logger
    logger = CrewAILogger(enable_console=True, log_dir=logs_dir)
    
    inputs = {
        'youtube_config_file': 'config/youtube_configuration.yaml',
        'output_file': f'{output_dir}/collected_data.json',
        'output_dir': output_dir,
        'logs_dir': logs_dir,
        'date_now': date_now
    }
    
    try:
        # Capture all CrewAI verbose output using the improved logger
        with logger.capture_crewai_output():
            # Log configuration
            logger.log_configuration(inputs)
            
            # Run the crew
            result = DataCollectionCrew().crew().kickoff(inputs=inputs)
            
            # Log results
            logger.log_results(result, inputs['output_file'])
        
        print(f"\n🎉 Data collection completed!")
        print(f"Results saved to: {inputs['output_file']}")
        print(f"Output directory: {output_dir}")
        print(f"Logs directory: {logs_dir}")
        print(f"Detailed logs saved to: {logger.get_log_filepath()}")
        
    except Exception as e:
        logger.log_error(e, "main run function")
        print(f"\n❌ Error during data collection: {str(e)}")
        print(f"Check logs at: {logger.get_log_filepath()}")
        raise
    
if __name__ == "__main__":
    run()