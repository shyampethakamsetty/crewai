# src/data_collection/main.py
import os
from market_analysis.crew import DataCollectionCrew
from market_analysis.utils.crewai_logger import CrewAILogger

os.makedirs('output', exist_ok=True)

def run():
    """Run the data collection crew with comprehensive logging."""
    # Initialize the advanced logger
    logger = CrewAILogger(enable_console=True)
    
    inputs = {
        'config_path': 'config/channels.json',
        'hours_back': 24,
        'batch_size': 75,
        'video_batch_size': 75,
        'output_file': 'output/collected_data.json'
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
        
        print("\n🎉 Data collection completed!")
        print(f"Results saved to: {inputs['output_file']}")
        print(f"Detailed logs saved to: {logger.get_log_filepath()}")
        
    except Exception as e:
        logger.log_error(e, "main run function")
        print(f"\n❌ Error during data collection: {str(e)}")
        print(f"Check logs at: {logger.get_log_filepath()}")
        raise
    
if __name__ == "__main__":
    run()