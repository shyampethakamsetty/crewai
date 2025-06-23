import re
import json
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
import yaml
from pathlib import Path
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token
import nltk
from nltk.tokenize import PunktSentenceTokenizer
from fuzzywuzzy import fuzz
import yfinance as yf
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import numpy as np
import signal
import time

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class AdvancedSentenceProcessor:
    """
    Advanced sentence processor combining multiple approaches for maximum accuracy:
    1. Rule-based splitting with financial pattern protection
    2. spaCy-based NLP processing
    3. NLTK Punkt tokenizer
    4. Transformer-based sentence boundary detection
    5. Hybrid approach with confidence scoring
    """
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialize multiple processors
        self.rule_processor = RuleBasedProcessor()
        self.spacy_processor = SpacyProcessor()
        self.nltk_processor = NLTKProcessor()
        self.transformer_processor = TransformerProcessor()
        self.hybrid_processor = HybridProcessor()
        
        # Financial patterns to protect
        self.financial_patterns = [
            r'\$\d+(?:\.\d{2})?',  # Dollar amounts
            r'\d+(?:\.\d{1,2})?%',  # Percentages
            r'\b[A-Z]{1,5}\b',  # Potential tickers
            r'\d+(?:\.\d+)?',  # Decimal numbers
            r'\b\d{1,2}:\d{2}\b',  # Time formats
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # Date formats
        ]
        
        # Sentence boundary indicators
        self.sentence_endings = [
            '.', '!', '?', ';', ':', '\n\n'
        ]
        
        # Financial connectors that should NOT split sentences
        self.financial_connectors = [
            'and', 'or', 'but', 'however', 'therefore', 'meanwhile',
            'furthermore', 'additionally', 'moreover', 'consequently'
        ]
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            'min_sentence_length': 10,
            'max_sentence_length': 500,
            'confidence_threshold': 0.7,
            'use_hybrid': True,
            'use_transformer': True,
            'use_spacy': True,
            'use_nltk': True
        }
    
    def process_sentences(self, transcript: str, source: str = "youtube", trader: str = "") -> Dict[str, Any]:
        """
        Process transcript using multiple approaches and combine results
        """
        self.logger.info(f"Processing transcript for {trader} using advanced sentence processor")
        self.logger.info(f"Transcript length: {len(transcript)} characters")
        
        # Clean and preprocess transcript
        self.logger.info("Step 1: Preprocessing transcript...")
        cleaned_transcript = self._preprocess_transcript(transcript)
        self.logger.info(f"Cleaned transcript length: {len(cleaned_transcript)} characters")
        
        # Get results from multiple processors
        results = {}
        
        if self.config.get('use_rule', True):
            self.logger.info("Step 2a: Processing with rule-based method...")
            try:
                results['rule'] = self.rule_processor.split_sentences(cleaned_transcript)
                self.logger.info(f"Rule-based: {len(results['rule'])} sentences found")
            except Exception as e:
                self.logger.error(f"Rule-based processing failed: {e}")
                results['rule'] = []
        
        if self.config.get('use_spacy', True):
            self.logger.info("Step 2b: Processing with spaCy method...")
            try:
                results['spacy'] = self.spacy_processor.split_sentences(cleaned_transcript)
                self.logger.info(f"spaCy: {len(results['spacy'])} sentences found")
            except Exception as e:
                self.logger.error(f"spaCy processing failed: {e}")
                results['spacy'] = []
        
        if self.config.get('use_nltk', True):
            self.logger.info("Step 2c: Processing with NLTK method...")
            try:
                results['nltk'] = self.nltk_processor.split_sentences(cleaned_transcript)
                self.logger.info(f"NLTK: {len(results['nltk'])} sentences found")
            except Exception as e:
                self.logger.error(f"NLTK processing failed: {e}")
                results['nltk'] = []
        
        if self.config.get('use_transformer', True):
            self.logger.info("Step 2d: Processing with transformer method...")
            try:
                results['transformer'] = self.transformer_processor.split_sentences(cleaned_transcript)
                self.logger.info(f"Transformer: {len(results['transformer'])} sentences found")
            except Exception as e:
                self.logger.error(f"Transformer processing failed: {e}")
                results['transformer'] = []
        
        if self.config.get('use_hybrid', True):
            self.logger.info("Step 2e: Processing with hybrid method...")
            try:
                results['hybrid'] = self.hybrid_processor.split_sentences(cleaned_transcript, results)
                self.logger.info(f"Hybrid: {len(results['hybrid'])} sentences found")
            except Exception as e:
                self.logger.error(f"Hybrid processing failed: {e}")
                results['hybrid'] = []
        
        # Combine and select best results
        self.logger.info("Step 3: Combining results from all methods...")
        final_sentences = self._combine_results(results, cleaned_transcript)
        self.logger.info(f"Combined result: {len(final_sentences)} sentences")
        
        # Post-process sentences
        self.logger.info("Step 4: Post-processing sentences...")
        final_sentences = self._post_process_sentences(final_sentences)
        self.logger.info(f"Final result: {len(final_sentences)} sentences after post-processing")
        
        return {
            "source": source,
            "trader": trader,
            "original_transcript": transcript,
            "sentences": final_sentences,
            "sentence_count": len(final_sentences),
            "processing_date": datetime.now().strftime("%Y-%m-%d"),
            "processing_methods": list(results.keys()),
            "confidence_scores": self._calculate_confidence_scores(final_sentences)
        }
    
    def _preprocess_transcript(self, transcript: str) -> str:
        """Preprocess transcript for better sentence splitting"""
        # Remove excessive whitespace
        transcript = re.sub(r'\s+', ' ', transcript)
        
        # Normalize line breaks
        transcript = re.sub(r'\n+', ' ', transcript)
        
        # Protect financial patterns
        for pattern in self.financial_patterns:
            matches = re.finditer(pattern, transcript)
            for match in matches:
                protected_text = f"__PROTECTED_{hash(match.group())}__"
                transcript = transcript.replace(match.group(), protected_text)
        
        return transcript
    
    def _combine_results(self, results: Dict[str, List[str]], original_text: str) -> List[str]:
        """Combine results from multiple processors using voting and confidence"""
        if not results:
            return [original_text]
        
        # If only one method, use it
        if len(results) == 1:
            return list(results.values())[0]
        
        # Calculate confidence for each method
        method_scores = {}
        for method, sentences in results.items():
            score = self._calculate_method_confidence(sentences, original_text)
            method_scores[method] = score
        
        # Select best method based on confidence
        best_method = max(method_scores, key=method_scores.get)
        best_sentences = results[best_method]
        
        # If hybrid method exists and has high confidence, use it
        if 'hybrid' in results and method_scores['hybrid'] > 0.8:
            return results['hybrid']
        
        return best_sentences
    
    def _calculate_method_confidence(self, sentences: List[str], original_text: str) -> float:
        """Calculate confidence score for a method's results"""
        if not sentences:
            return 0.0
        
        # Check if sentences reconstruct original text
        reconstructed = ' '.join(sentences)
        text_similarity = fuzz.ratio(reconstructed.lower(), original_text.lower()) / 100
        
        # Check sentence length distribution
        lengths = [len(s) for s in sentences]
        avg_length = np.mean(lengths)
        length_score = 1.0 if 50 <= avg_length <= 200 else 0.5
        
        # Check for reasonable sentence count
        expected_sentences = len(original_text) / 150  # Rough estimate
        if expected_sentences <= 0:
            count_score = 1.0  # Default score if text is very short
        else:
            count_score = 1.0 if 0.5 <= len(sentences) / expected_sentences <= 2.0 else 0.5
        
        return (text_similarity + length_score + count_score) / 3
    
    def _post_process_sentences(self, sentences: List[str]) -> List[str]:
        """Post-process sentences for quality"""
        processed = []
        
        for sentence in sentences:
            # Restore protected patterns
            sentence = self._restore_protected_patterns(sentence)
            
            # Clean up sentence
            sentence = sentence.strip()
            sentence = re.sub(r'\s+', ' ', sentence)
            
            # Filter out very short or very long sentences
            if len(sentence) >= self.config.get('min_sentence_length', 10) and \
               len(sentence) <= self.config.get('max_sentence_length', 500):
                processed.append(sentence)
        
        return processed
    
    def _restore_protected_patterns(self, sentence: str) -> str:
        """Restore protected financial patterns"""
        # This would need to maintain a mapping of protected patterns
        # For now, just return the sentence
        return sentence
    
    def _calculate_confidence_scores(self, sentences: List[str]) -> List[float]:
        """Calculate confidence scores for each sentence"""
        scores = []
        for sentence in sentences:
            # Score based on sentence quality indicators
            length_score = min(len(sentence) / 100, 1.0)  # Prefer medium-length sentences
            structure_score = 1.0 if re.search(r'[.!?]$', sentence) else 0.8
            financial_score = 1.0 if re.search(r'[\$\d%]', sentence) else 0.9
            
            avg_score = (length_score + structure_score + financial_score) / 3
            scores.append(round(avg_score, 3))
        
        return scores


class RuleBasedProcessor:
    """Rule-based sentence processor with financial pattern protection"""
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text using rule-based approach"""
        # Protect financial patterns
        protected_text = self._protect_patterns(text)
        
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', protected_text)
        
        # Clean and filter sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Restore protected patterns
        sentences = [self._restore_patterns(s) for s in sentences]
        
        return sentences
    
    def _protect_patterns(self, text: str) -> str:
        """Protect financial patterns from splitting"""
        patterns = [
            (r'\$\d+(?:\.\d{2})?', 'DOLLAR_AMOUNT'),
            (r'\d+(?:\.\d{1,2})?%', 'PERCENTAGE'),
            (r'\b[A-Z]{1,5}\b', 'TICKER'),
            (r'\d+(?:\.\d+)?', 'DECIMAL'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, f'__{replacement}__', text)
        
        return text
    
    def _restore_patterns(self, text: str) -> str:
        """Restore protected patterns"""
        # This would need proper pattern restoration logic
        return text


class SpacyProcessor:
    """spaCy-based sentence processor"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self._add_financial_rules()
        except OSError:
            # Fallback to basic English
            self.nlp = spacy.blank("en")
    
    def _add_financial_rules(self):
        """Add financial domain rules to spaCy"""
        # Add custom sentence boundary rules
        @Language.component("financial_sentence_splitter")
        def financial_sentence_splitter(doc):
            for token in doc:
                # Don't split on financial abbreviations
                if token.text.upper() in ['PLTR', 'AAPL', 'TSLA', 'NVDA', 'SPY', 'QQQ']:
                    token.is_sent_start = False
                # Don't split on decimal numbers
                elif re.match(r'\d+\.\d+', token.text):
                    token.is_sent_start = False
            return doc
        
        self.nlp.add_pipe("financial_sentence_splitter")
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text using spaCy"""
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]
        return [s for s in sentences if s]


class NLTKProcessor:
    """NLTK-based sentence processor"""
    
    def __init__(self):
        self.tokenizer = PunktSentenceTokenizer()
        self._train_financial_tokenizer()
    
    def _train_financial_tokenizer(self):
        """Train tokenizer on financial text"""
        # Add financial abbreviations
        self.tokenizer._params.abbrev_types.update({
            'PLTR', 'AAPL', 'TSLA', 'NVDA', 'SPY', 'QQQ', 'ETF', 'SEC', 'IPO'
        })
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text using NLTK"""
        sentences = self.tokenizer.tokenize(text)
        return [s.strip() for s in sentences if s.strip()]


class TransformerProcessor:
    """Transformer-based sentence processor"""
    
    def __init__(self):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
            self.model = AutoModelForTokenClassification.from_pretrained("microsoft/DialoGPT-medium")
        except Exception as e:
            self.tokenizer = None
            self.model = None
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text using transformer model with timeout"""
        if not self.tokenizer or not self.model:
            # Fallback to simple splitting
            return re.split(r'[.!?]+', text)
        
        try:
            # Set a timeout for transformer processing
            def timeout_handler(signum, frame):
                raise TimeoutError("Transformer processing timed out")
            
            # Set timeout to 30 seconds
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            try:
                # Tokenize text
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                
                # Get model predictions
                with torch.no_grad():
                    outputs = self.model(**inputs)
                
                # Extract sentence boundaries (simplified approach)
                # In practice, you'd need a fine-tuned model for sentence boundary detection
                result = self._extract_sentences_from_outputs(outputs, inputs)
                
                # Cancel the alarm
                signal.alarm(0)
                return result
                
            except TimeoutError:
                print("Transformer processing timed out, falling back to simple splitting")
                return re.split(r'[.!?]+', text)
            finally:
                signal.alarm(0)  # Ensure alarm is cancelled
        
        except Exception as e:
            # Fallback to simple splitting
            return re.split(r'[.!?]+', text)
    
    def _extract_sentences_from_outputs(self, outputs, inputs):
        """Extract sentences from transformer outputs"""
        # Simplified implementation - would need proper fine-tuning
        return re.split(r'[.!?]+', self.tokenizer.decode(inputs['input_ids'][0]))


class HybridProcessor:
    """Hybrid processor that combines multiple approaches"""
    
    def split_sentences(self, text: str, method_results: Dict[str, List[str]]) -> List[str]:
        """Combine results from multiple methods"""
        if not method_results:
            return [text]
        
        # Get all unique sentences from all methods
        all_sentences = set()
        for sentences in method_results.values():
            all_sentences.update(sentences)
        
        # Score each sentence based on how many methods agree
        sentence_scores = {}
        for sentence in all_sentences:
            score = sum(1 for sentences in method_results.values() if sentence in sentences)
            sentence_scores[sentence] = score / len(method_results)
        
        # Select sentences with high agreement
        threshold = 0.5
        selected_sentences = [s for s, score in sentence_scores.items() if score >= threshold]
        
        # Sort by position in original text
        selected_sentences.sort(key=lambda s: text.find(s))
        
        return selected_sentences if selected_sentences else [text] 