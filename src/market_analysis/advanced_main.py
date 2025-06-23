#!/usr/bin/env python3
"""
Advanced Market Analysis Pipeline
Combines multiple approaches for maximum accuracy in sentence processing and ticker tagging.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime
import yaml
import json

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from market_analysis.tools.advanced_data_processor import AdvancedDataProcessor
from market_analysis.tools.advanced_sentence_processor import AdvancedSentenceProcessor
from market_analysis.tools.advanced_ticker_tagger import AdvancedTickerTagger
from market_analysis.utils.crewai_logger import CrewAILogger

def setup_advanced_logging(config_path: str = None):
    """Setup advanced logging configuration"""
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            log_config = config.get('logging', {})
    else:
        log_config = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'logs/advanced_processing.log'
        }
    
    # Create logs directory
    log_file = Path(log_config.get('file', 'logs/advanced_processing.log'))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def install_required_packages():
    """Install required packages for advanced processing"""
    required_packages = [
        'spacy',
        'nltk',
        'fuzzywuzzy',
        'yfinance',
        'transformers',
        'torch',
        'numpy',
        'requests'
    ]
    
    print("Installing required packages for advanced processing...")
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} already installed")
        except ImportError:
            print(f"Installing {package}...")
            os.system(f"pip install {package}")
    
    # Download spaCy model
    try:
        import spacy
        spacy.load("en_core_web_sm")
        print("✓ spaCy model already downloaded")
    except OSError:
        print("Downloading spaCy model...")
        os.system("python -m spacy download en_core_web_sm")
    
    # Download NLTK data
    try:
        import nltk
        nltk.data.find('tokenizers/punkt')
        print("✓ NLTK data already downloaded")
    except LookupError:
        print("Downloading NLTK data...")
        import nltk
        nltk.download('punkt')

def run_advanced_processing(input_file: str, config_path: str = None, output_dir: str = None):
    """Run the advanced processing pipeline"""
    logger = logging.getLogger(__name__)
    
    # Setup logging
    setup_advanced_logging(config_path)
    
    # Install required packages
    install_required_packages()
    
    logger.info("Starting Advanced Market Analysis Pipeline")
    logger.info(f"Input file: {input_file}")
    logger.info(f"Config file: {config_path}")
    logger.info(f"Output directory: {output_dir}")
    
    try:
        # Initialize advanced data processor
        processor = AdvancedDataProcessor(config_path)
        
        # Process the data
        start_time = datetime.now()
        result = processor.process_youtube_data(input_file, output_dir)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if result['status'] == 'success':
            logger.info("SUCCESS: Advanced processing completed successfully!")
            logger.info(f"Output file: {result['output_file']}")
            logger.info(f"Processing time: {processing_time:.2f} seconds")
            logger.info(f"Records processed: {result['records_processed']}")
            logger.info(f"Confidence score: {result['confidence_score']:.3f}")
            
            # Print processing statistics
            stats = processor.get_processing_stats()
            logger.info("STATISTICS:")
            logger.info(f"  Total processed: {stats['total_processed']}")
            logger.info(f"  Success rate: {stats['success_rate']:.2%}")
            logger.info(f"  Average confidence: {stats['average_confidence']:.3f}")
            logger.info(f"  Average processing time: {stats['avg_processing_time']:.2f}s")
            
            return result
        else:
            logger.error(f"ERROR: Processing failed: {result['error']}")
            return result
            
    except Exception as e:
        logger.error(f"ERROR: Advanced processing failed with exception: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "processing_time": (datetime.now() - start_time).total_seconds()
        }

def run_individual_components(input_file: str, config_path: str = None):
    """Run individual components for testing"""
    logger = logging.getLogger(__name__)
    
    setup_advanced_logging(config_path)
    
    try:
        # Load input data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Test sentence processor
        logger.info("Testing Advanced Sentence Processor...")
        sentence_processor = AdvancedSentenceProcessor(config_path)
        
        for item in data.get('data', [])[:1]:  # Test with first item
            transcript = item.get('transcript', '')
            source = item.get('source', 'youtube')
            trader = item.get('trader', '')
            
            sentence_result = sentence_processor.process_sentences(transcript, source, trader)
            logger.info(f"Sentence processing result: {len(sentence_result.get('sentences', []))} sentences")
            logger.info(f"Processing methods used: {sentence_result.get('processing_methods', [])}")
            
            # Test ticker tagger
            logger.info("Testing Advanced Ticker Tagger...")
            ticker_tagger = AdvancedTickerTagger(config_path)
            
            sentences_data = []
            for i, sentence in enumerate(sentence_result.get('sentences', [])):
                sentences_data.append({
                    'sentence_id': i + 1,
                    'sentence': sentence
                })
            
            ticker_result = ticker_tagger.tag_sentences(sentences_data, source, trader)
            logger.info(f"Ticker tagging result: {ticker_result.get('ticker_summary', {}).get('unique_tickers', [])}")
            
            return {
                "sentence_processing": sentence_result,
                "ticker_tagging": ticker_result
            }
            
    except Exception as e:
        logger.error(f"Component testing failed: {str(e)}")
        return {"error": str(e)}

def compare_methods(input_file: str, config_path: str = None):
    """Compare different processing methods"""
    logger = logging.getLogger(__name__)
    
    setup_advanced_logging(config_path)
    
    try:
        # Load input data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        item = data.get('data', [])[0]  # Use first item
        transcript = item.get('transcript', '')
        
        logger.info("Comparing different processing methods...")
        
        # Test different sentence processing methods
        sentence_processor = AdvancedSentenceProcessor(config_path)
        
        # Test with different configurations
        configs = {
            "rule_only": {"use_rule": True, "use_spacy": False, "use_nltk": False, "use_transformer": False, "use_hybrid": False},
            "spacy_only": {"use_rule": False, "use_spacy": True, "use_nltk": False, "use_transformer": False, "use_hybrid": False},
            "nltk_only": {"use_rule": False, "use_spacy": False, "use_nltk": True, "use_transformer": False, "use_hybrid": False},
            "hybrid": {"use_rule": True, "use_spacy": True, "use_nltk": True, "use_transformer": True, "use_hybrid": True}
        }
        
        results = {}
        for method_name, config in configs.items():
            logger.info(f"Testing {method_name}...")
            sentence_processor.config.update(config)
            result = sentence_processor.process_sentences(transcript, "youtube", "test")
            results[method_name] = {
                "sentence_count": len(result.get('sentences', [])),
                "processing_methods": result.get('processing_methods', []),
                "confidence_scores": result.get('confidence_scores', [])
            }
        
        # Compare results
        logger.info("METHOD COMPARISON RESULTS:")
        for method_name, result in results.items():
            avg_confidence = sum(result['confidence_scores']) / len(result['confidence_scores']) if result['confidence_scores'] else 0
            logger.info(f"  {method_name}: {result['sentence_count']} sentences, avg confidence: {avg_confidence:.3f}")
        
        return results
        
    except Exception as e:
        logger.error(f"Method comparison failed: {str(e)}")
        return {"error": str(e)}

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Advanced Market Analysis Pipeline")
    parser.add_argument("input_file", help="Input JSON file with YouTube data")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--test-components", action="store_true", help="Test individual components")
    parser.add_argument("--compare-methods", action="store_true", help="Compare different processing methods")
    parser.add_argument("--install-deps", action="store_true", help="Install required dependencies")
    
    args = parser.parse_args()
    
    if args.install_deps:
        install_required_packages()
        return
    
    if args.test_components:
        result = run_individual_components(args.input_file, args.config)
        print(json.dumps(result, indent=2))
        return
    
    if args.compare_methods:
        result = compare_methods(args.input_file, args.config)
        print(json.dumps(result, indent=2))
        return
    
    # Run full advanced processing
    result = run_advanced_processing(args.input_file, args.config, args.output)
    
    if result['status'] == 'success':
        print("SUCCESS: Advanced processing completed successfully!")
        print(f"Output file: {result['output_file']}")
        print(f"Processing time: {result['processing_time']:.2f} seconds")
        print(f"Confidence score: {result['confidence_score']:.3f}")
    else:
        print(f"ERROR: Processing failed: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main() 