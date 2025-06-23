import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import yaml

from .advanced_sentence_processor import AdvancedSentenceProcessor
from .advanced_ticker_tagger import AdvancedTickerTagger

class AdvancedDataProcessor:
    """
    Advanced data processor that integrates multiple approaches for maximum accuracy.
    Combines advanced sentence processing and ticker tagging with comprehensive validation.
    """
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialize advanced processors
        self.sentence_processor = AdvancedSentenceProcessor(config_path)
        self.ticker_tagger = AdvancedTickerTagger(config_path)
        
        # Performance tracking
        self.processing_stats = {
            'total_processed': 0,
            'successful_processing': 0,
            'failed_processing': 0,
            'average_confidence': 0.0,
            'processing_times': []
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            'output_dir': 'output',
            'backup_original': True,
            'validation_enabled': True,
            'confidence_threshold': 0.7,
            'max_retries': 3
        }
    
    def process_youtube_data(self, input_file: str, output_dir: str = None) -> Dict[str, Any]:
        """Process YouTube data with advanced sentence processing and ticker tagging"""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting advanced processing of {input_file}")
            
            # Load input data
            self.logger.info("Step 1: Loading input data...")
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.info(f"Loaded {len(data.get('data', []))} records from input file")
            
            # Process each transcript
            processed_data = []
            data_items = data.get('data', [])
            
            self.logger.info(f"Step 2: Processing {len(data_items)} transcripts...")
            for i, item in enumerate(data_items):
                self.logger.info(f"Processing item {i+1}/{len(data_items)}: {item.get('trader', 'Unknown')}")
                
                processed_item = self._process_single_transcript(item)
                if processed_item:
                    processed_data.append(processed_item)
                    self.logger.info(f"Successfully processed item {i+1}")
                else:
                    self.logger.warning(f"Failed to process item {i+1}")
            
            # Prepare output data
            self.logger.info("Step 3: Preparing output data...")
            output_data = {
                "data": processed_data,
                "original_statistics": data.get('statistics', {}),
                "advanced_processing_date": datetime.now().strftime("%Y-%m-%d"),
                "advanced_processing_time": datetime.now().isoformat(),
                "processing_stats": self.processing_stats,
                "config_used": self.config
            }
            
            # Save output
            self.logger.info("Step 4: Saving output file...")
            if output_dir:
                output_path = Path(output_dir) / f"advanced_processed_{datetime.now().strftime('%Y%m%d')}.json"
            else:
                output_path = Path("output") / f"advanced_processed_{datetime.now().strftime('%Y%m%d')}.json"
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_stats['total_processed'] += 1
            self.processing_stats['successful_processing'] += 1
            self.processing_stats['processing_times'].append(processing_time)
            self.processing_stats['average_confidence'] = self._calculate_average_confidence(processed_data)
            
            self.logger.info(f"Advanced processing completed successfully. Output saved to {output_path}")
            
            return {
                "status": "success",
                "output_file": str(output_path),
                "processing_time": processing_time,
                "records_processed": len(processed_data),
                "confidence_score": self.processing_stats['average_confidence']
            }
            
        except Exception as e:
            self.logger.error(f"Advanced processing failed: {str(e)}")
            self.processing_stats['total_processed'] += 1
            self.processing_stats['failed_processing'] += 1
            
            return {
                "status": "error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _process_single_transcript(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single transcript with advanced methods"""
        try:
            transcript = item.get('data', '')
            source = item.get('source', 'youtube')
            trader = item.get('trader', '')
            
            self.logger.info(f"Processing transcript for {trader} - Step 1: Sentence processing")
            # Step 1: Advanced sentence processing
            sentence_results = self.sentence_processor.process_sentences(
                transcript, source, trader
            )
            
            self.logger.info(f"Processing transcript for {trader} - Step 2: Ticker tagging")
            # Step 2: Advanced ticker tagging
            ticker_results = self.ticker_tagger.tag_sentences(
                sentence_results.get('sentences', []), source, trader
            )
            
            self.logger.info(f"Processing transcript for {trader} - Step 3: Combining results")
            # Step 3: Combine and validate results
            combined_results = self._combine_results(sentence_results, ticker_results, item)
            
            self.logger.info(f"Processing transcript for {trader} - Step 4: Quality validation")
            # Step 4: Quality validation
            if self.config.get('validation_enabled', True):
                combined_results = self._validate_results(combined_results)
            
            return combined_results
            
        except Exception as e:
            self.logger.error(f"Error processing transcript for {trader}: {str(e)}")
            return None
    
    def _combine_results(self, sentence_results: Dict[str, Any], 
                        ticker_results: Dict[str, Any], 
                        original_item: Dict[str, Any]) -> Dict[str, Any]:
        """Combine sentence and ticker results"""
        return {
            "source": original_item.get('source', 'youtube'),
            "trader": original_item.get('trader', ''),
            "original_transcript": original_item.get('transcript', ''),
            "sentences": sentence_results.get('sentences', []),
            "sentence_count": sentence_results.get('sentence_count', 0),
            "processing_date": datetime.now().strftime("%Y-%m-%d"),
            "tagged_sentences": ticker_results.get('tagged_sentences', []),
            "ticker_summary": ticker_results.get('ticker_summary', {}),
            "sentence_confidence": sentence_results.get('confidence_scores', []),
            "ticker_confidence": ticker_results.get('confidence_scores', {}),
            "processing_methods": {
                "sentence_processing": sentence_results.get('processing_methods', []),
                "ticker_tagging": list(ticker_results.get('confidence_scores', {}).keys())
            }
        }
    
    def _validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate processing results for quality"""
        validation_results = {
            "sentence_quality": self._validate_sentences(results.get('sentences', [])),
            "ticker_quality": self._validate_tickers(results.get('tagged_sentences', [])),
            "overall_quality": 0.0
        }
        
        # Calculate overall quality score
        sentence_score = validation_results['sentence_quality'].get('score', 0.0)
        ticker_score = validation_results['ticker_quality'].get('score', 0.0)
        validation_results['overall_quality'] = (sentence_score + ticker_score) / 2
        
        results['validation'] = validation_results
        return results
    
    def _validate_sentences(self, sentences: List[str]) -> Dict[str, Any]:
        """Validate sentence quality"""
        if not sentences:
            return {"score": 0.0, "issues": ["No sentences found"]}
        
        issues = []
        score = 1.0
        
        # Check sentence lengths
        lengths = [len(s) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        
        if avg_length < 20:
            issues.append("Sentences too short")
            score -= 0.2
        elif avg_length > 300:
            issues.append("Sentences too long")
            score -= 0.2
        
        # Check for proper sentence endings
        proper_endings = sum(1 for s in sentences if s.strip().endswith(('.', '!', '?')))
        ending_ratio = proper_endings / len(sentences)
        
        if ending_ratio < 0.8:
            issues.append("Many sentences lack proper endings")
            score -= 0.3
        
        # Check for financial content
        financial_words = ['stock', 'trading', 'price', 'market', 'options', 'shares']
        financial_sentences = sum(1 for s in sentences 
                                if any(word in s.lower() for word in financial_words))
        financial_ratio = financial_sentences / len(sentences)
        
        if financial_ratio < 0.3:
            issues.append("Low financial content")
            score -= 0.1
        
        return {
            "score": max(0.0, score),
            "issues": issues,
            "metrics": {
                "avg_length": avg_length,
                "ending_ratio": ending_ratio,
                "financial_ratio": financial_ratio
            }
        }
    
    def _validate_tickers(self, tagged_sentences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate ticker tagging quality"""
        if not tagged_sentences:
            return {"score": 0.0, "issues": ["No tagged sentences found"]}
        
        issues = []
        score = 1.0
        
        # Count tickers
        all_tickers = set()
        sentences_with_tickers = 0
        
        for sentence in tagged_sentences:
            tickers = sentence.get('all_tickers', [])
            if tickers:
                sentences_with_tickers += 1
                all_tickers.update(tickers)
        
        ticker_ratio = sentences_with_tickers / len(tagged_sentences)
        
        if ticker_ratio < 0.1:
            issues.append("Very few sentences have tickers")
            score -= 0.3
        elif ticker_ratio > 0.8:
            issues.append("Too many sentences have tickers (possible over-tagging)")
            score -= 0.2
        
        # Check for common false positives
        false_positives = ['THE', 'AND', 'FOR', 'ARE', 'ALL']
        false_positive_count = sum(1 for ticker in all_tickers if ticker in false_positives)
        
        if false_positive_count > 0:
            issues.append(f"Found {false_positive_count} potential false positive tickers")
            score -= 0.2 * false_positive_count
        
        return {
            "score": max(0.0, score),
            "issues": issues,
            "metrics": {
                "ticker_ratio": ticker_ratio,
                "unique_tickers": len(all_tickers),
                "false_positives": false_positive_count
            }
        }
    
    def _calculate_average_confidence(self, processed_data: List[Dict[str, Any]]) -> float:
        """Calculate average confidence across all processed data"""
        if not processed_data:
            return 0.0
        
        total_confidence = 0.0
        count = 0
        
        for item in processed_data:
            validation = item.get('validation', {})
            overall_quality = validation.get('overall_quality', 0.0)
            total_confidence += overall_quality
            count += 1
        
        return total_confidence / count if count > 0 else 0.0
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.processing_stats,
            "success_rate": (self.processing_stats['successful_processing'] / 
                           max(1, self.processing_stats['total_processed'])),
            "avg_processing_time": (sum(self.processing_stats['processing_times']) / 
                                  max(1, len(self.processing_stats['processing_times'])))
        }
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.processing_stats = {
            'total_processed': 0,
            'successful_processing': 0,
            'failed_processing': 0,
            'average_confidence': 0.0,
            'processing_times': []
        } 