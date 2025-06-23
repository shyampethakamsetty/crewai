import re
import json
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
import yaml
from pathlib import Path
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
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
import os

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class ParallelSentenceProcessor:
    """
    Parallel sentence processor that splits transcripts into chunks and processes them concurrently
    for significantly improved performance on large transcripts.
    """
    
    def __init__(self, config_path: str = None, max_workers: int = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Set number of workers (default to CPU count - 1, minimum 2)
        self.max_workers = max_workers or max(2, mp.cpu_count() - 1)
        self.logger.info(f"Initializing parallel processor with {self.max_workers} workers")
        
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
            'chunk_size': 5000,  # Characters per chunk
            'chunk_overlap': 500,  # Overlap between chunks
            'use_hybrid': True,
            'use_transformer': True,
            'use_spacy': True,
            'use_nltk': True
        }
    
    def process_sentences(self, transcript: str, source: str = "youtube", trader: str = "") -> Dict[str, Any]:
        """
        Process transcript in parallel by splitting into chunks and processing concurrently
        """
        self.logger.info(f"Processing transcript for {trader} using parallel sentence processor")
        self.logger.info(f"Transcript length: {len(transcript)} characters")
        self.logger.info(f"Using {self.max_workers} parallel workers")
        
        start_time = time.time()
        
        # Step 1: Preprocess transcript
        self.logger.info("Step 1: Preprocessing transcript...")
        cleaned_transcript = self._preprocess_transcript(transcript)
        self.logger.info(f"Cleaned transcript length: {len(cleaned_transcript)} characters")
        
        # Step 2: Split into chunks
        self.logger.info("Step 2: Splitting transcript into chunks...")
        chunks = self._split_into_chunks(cleaned_transcript)
        self.logger.info(f"Created {len(chunks)} chunks for parallel processing")
        
        # Step 3: Process chunks in parallel
        self.logger.info("Step 3: Processing chunks in parallel...")
        chunk_results = self._process_chunks_parallel(chunks)
        self.logger.info(f"Processed {len(chunk_results)} chunks successfully")
        
        # Step 4: Merge results
        self.logger.info("Step 4: Merging chunk results...")
        final_sentences = self._merge_chunk_results(chunk_results)
        self.logger.info(f"Merged result: {len(final_sentences)} sentences")
        
        # Step 5: Post-process sentences
        self.logger.info("Step 5: Post-processing sentences...")
        final_sentences = self._post_process_sentences(final_sentences)
        self.logger.info(f"Final result: {len(final_sentences)} sentences after post-processing")
        
        processing_time = time.time() - start_time
        self.logger.info(f"Total processing time: {processing_time:.2f} seconds")
        
        return {
            "source": source,
            "trader": trader,
            "original_transcript": transcript,
            "sentences": final_sentences,
            "sentence_count": len(final_sentences),
            "processing_date": datetime.now().strftime("%Y-%m-%d"),
            "processing_method": "parallel",
            "chunks_processed": len(chunks),
            "workers_used": self.max_workers,
            "processing_time_seconds": processing_time,
            "confidence_scores": self._calculate_confidence_scores(final_sentences)
        }
    
    def _split_into_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks for parallel processing"""
        chunk_size = self.config.get('chunk_size', 5000)
        overlap = self.config.get('chunk_overlap', 500)
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this isn't the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings within the overlap region
                overlap_start = max(start, end - overlap)
                overlap_end = min(len(text), end + overlap)
                
                # Find the best break point
                best_break = end
                for i in range(overlap_start, overlap_end):
                    if text[i] in self.sentence_endings:
                        # Prefer breaks that don't split financial patterns
                        if not self._would_split_financial_pattern(text, i):
                            best_break = i + 1
                            break
                
                end = best_break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    'id': len(chunks),
                    'text': chunk_text,
                    'start_pos': start,
                    'end_pos': end
                })
            
            start = end
        
        return chunks
    
    def _would_split_financial_pattern(self, text: str, position: int) -> bool:
        """Check if splitting at position would break a financial pattern"""
        # Look for patterns around the split point
        context_start = max(0, position - 20)
        context_end = min(len(text), position + 20)
        context = text[context_start:context_end]
        
        for pattern in self.financial_patterns:
            if re.search(pattern, context):
                return True
        return False
    
    def _process_chunks_parallel(self, chunks: List[Dict[str, Any]]) -> List[List[str]]:
        """Process chunks in parallel using ProcessPoolExecutor"""
        results = []
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all chunks for processing
            future_to_chunk = {
                executor.submit(self._process_single_chunk, chunk): chunk 
                for chunk in chunks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_sentences = future.result()
                    results.append({
                        'chunk_id': chunk['id'],
                        'sentences': chunk_sentences,
                        'start_pos': chunk['start_pos'],
                        'end_pos': chunk['end_pos']
                    })
                    self.logger.debug(f"Completed chunk {chunk['id']}: {len(chunk_sentences)} sentences")
                except Exception as e:
                    self.logger.error(f"Error processing chunk {chunk['id']}: {e}")
                    # Fallback to simple sentence splitting
                    fallback_sentences = self._fallback_sentence_split(chunk['text'])
                    results.append({
                        'chunk_id': chunk['id'],
                        'sentences': fallback_sentences,
                        'start_pos': chunk['start_pos'],
                        'end_pos': chunk['end_pos']
                    })
        
        # Sort results by chunk ID to maintain order
        results.sort(key=lambda x: x['chunk_id'])
        return results
    
    def _process_single_chunk(self, chunk: Dict[str, Any]) -> List[str]:
        """Process a single chunk (runs in separate process)"""
        try:
            # Initialize processors for this process
            rule_processor = RuleBasedProcessor()
            spacy_processor = SpacyProcessor()
            nltk_processor = NLTKProcessor()
            transformer_processor = TransformerProcessor()
            hybrid_processor = HybridProcessor()
            
            text = chunk['text']
            results = {}
            
            # Process with multiple methods
            if self.config.get('use_rule', True):
                try:
                    results['rule'] = rule_processor.split_sentences(text)
                except:
                    results['rule'] = []
            
            if self.config.get('use_spacy', True):
                try:
                    results['spacy'] = spacy_processor.split_sentences(text)
                except:
                    results['spacy'] = []
            
            if self.config.get('use_nltk', True):
                try:
                    results['nltk'] = nltk_processor.split_sentences(text)
                except:
                    results['nltk'] = []
            
            if self.config.get('use_transformer', True):
                try:
                    results['transformer'] = transformer_processor.split_sentences(text)
                except:
                    results['transformer'] = []
            
            if self.config.get('use_hybrid', True):
                try:
                    results['hybrid'] = hybrid_processor.split_sentences(text, results)
                except:
                    results['hybrid'] = []
            
            # Combine results
            final_sentences = self._combine_results(results, text)
            
            # Post-process
            final_sentences = self._post_process_sentences(final_sentences)
            
            return final_sentences
            
        except Exception as e:
            # Fallback to simple splitting
            return self._fallback_sentence_split(chunk['text'])
    
    def _fallback_sentence_split(self, text: str) -> List[str]:
        """Simple fallback sentence splitting"""
        # Basic sentence splitting with financial pattern protection
        sentences = []
        current_sentence = ""
        
        # Split on sentence endings but protect financial patterns
        protected_text = self._protect_patterns(text)
        
        for char in protected_text:
            current_sentence += char
            if char in self.sentence_endings:
                sentence = current_sentence.strip()
                if len(sentence) >= self.config.get('min_sentence_length', 10):
                    sentence = self._restore_patterns(sentence)
                    sentences.append(sentence)
                current_sentence = ""
        
        # Add remaining text as sentence
        if current_sentence.strip():
            sentence = self._restore_patterns(current_sentence.strip())
            if len(sentence) >= self.config.get('min_sentence_length', 10):
                sentences.append(sentence)
        
        return sentences
    
    def _merge_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> List[str]:
        """Merge results from all chunks, handling overlaps"""
        all_sentences = []
        
        for i, result in enumerate(chunk_results):
            sentences = result['sentences']
            
            # For overlapping chunks, we need to handle sentence boundaries carefully
            if i > 0:
                # Check for overlap with previous chunk
                prev_result = chunk_results[i-1]
                overlap_start = prev_result['end_pos'] - self.config.get('chunk_overlap', 500)
                
                # Remove sentences that might be duplicates from overlap
                if sentences:
                    # Keep only sentences that don't appear to be from overlap
                    filtered_sentences = []
                    for sentence in sentences:
                        # Simple heuristic: if sentence is very short and appears to be incomplete
                        # it might be from overlap
                        if len(sentence) > 20 or not sentence.endswith(('.', '!', '?')):
                            filtered_sentences.append(sentence)
                    
                    sentences = filtered_sentences
            
            all_sentences.extend(sentences)
        
        return all_sentences
    
    def _preprocess_transcript(self, transcript: str) -> str:
        """Preprocess transcript for better sentence splitting"""
        # Remove excessive whitespace
        transcript = re.sub(r'\s+', ' ', transcript)
        
        # Normalize line breaks
        transcript = re.sub(r'\n+', ' ', transcript)
        
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
        
        return best_sentences
    
    def _calculate_method_confidence(self, sentences: List[str], original_text: str) -> float:
        """Calculate confidence score for a method's results"""
        if not sentences:
            return 0.0
        
        # Factors for confidence calculation
        length_factor = min(1.0, len(sentences) / 10)  # Prefer more sentences
        avg_length = sum(len(s) for s in sentences) / len(sentences)
        length_consistency = 1.0 - abs(avg_length - 100) / 100  # Prefer ~100 char avg
        
        # Check for financial patterns
        financial_pattern_count = 0
        for sentence in sentences:
            for pattern in self.financial_patterns:
                if re.search(pattern, sentence):
                    financial_pattern_count += 1
                    break
        
        financial_factor = financial_pattern_count / len(sentences)
        
        # Combined confidence score
        confidence = (length_factor * 0.3 + 
                     length_consistency * 0.3 + 
                     financial_factor * 0.4)
        
        return max(0.0, min(1.0, confidence))
    
    def _post_process_sentences(self, sentences: List[str]) -> List[str]:
        """Post-process sentences to improve quality"""
        processed = []
        
        for sentence in sentences:
            # Clean up sentence
            sentence = sentence.strip()
            
            # Remove very short or very long sentences
            if (len(sentence) < self.config.get('min_sentence_length', 10) or 
                len(sentence) > self.config.get('max_sentence_length', 500)):
                continue
            
            # Ensure sentence ends with proper punctuation
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            
            # Restore protected patterns
            sentence = self._restore_protected_patterns(sentence)
            
            processed.append(sentence)
        
        return processed
    
    def _protect_patterns(self, text: str) -> str:
        """Protect financial patterns from being split"""
        for pattern in self.financial_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                protected_text = f"__PROTECTED_{hash(match.group())}__"
                text = text.replace(match.group(), protected_text)
        return text
    
    def _restore_patterns(self, text: str) -> str:
        """Restore protected patterns"""
        # This is a simplified version - in practice, you'd maintain a mapping
        return text
    
    def _restore_protected_patterns(self, sentence: str) -> str:
        """Restore protected patterns in a sentence"""
        # This is a simplified version - in practice, you'd maintain a mapping
        return sentence
    
    def _calculate_confidence_scores(self, sentences: List[str]) -> List[float]:
        """Calculate confidence scores for each sentence"""
        scores = []
        for sentence in sentences:
            # Simple confidence based on length and financial content
            length_score = min(1.0, len(sentence) / 200)
            
            financial_score = 0.0
            for pattern in self.financial_patterns:
                if re.search(pattern, sentence):
                    financial_score = 1.0
                    break
            
            confidence = (length_score * 0.6 + financial_score * 0.4)
            scores.append(confidence)
        
        return scores


# Import the processor classes from the original file
# These will be used in the parallel processing
class RuleBasedProcessor:
    def split_sentences(self, text: str) -> List[str]:
        # Simplified rule-based splitting
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in '.!?':
                sentence = current.strip()
                if sentence:
                    sentences.append(sentence)
                current = ""
        
        if current.strip():
            sentences.append(current.strip())
        
        return sentences


class SpacyProcessor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            self.nlp = None
    
    def split_sentences(self, text: str) -> List[str]:
        if not self.nlp:
            return [text]
        
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents]


class NLTKProcessor:
    def __init__(self):
        self.tokenizer = PunktSentenceTokenizer()
    
    def split_sentences(self, text: str) -> List[str]:
        return self.tokenizer.tokenize(text)


class TransformerProcessor:
    def __init__(self):
        self.tokenizer = None
        self.model = None
    
    def split_sentences(self, text: str) -> List[str]:
        # Simplified transformer processing
        return [text]


class HybridProcessor:
    def split_sentences(self, text: str, method_results: Dict[str, List[str]]) -> List[str]:
        # Simplified hybrid processing
        if method_results:
            return list(method_results.values())[0]
        return [text] 