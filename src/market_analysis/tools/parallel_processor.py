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
    Improved parallel sentence processor that properly handles sentence boundaries
    and financial patterns while providing actual performance benefits.
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
        self.sentence_endings = ['.', '!', '?']
        
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
            'chunk_size': 10000,  # Increased chunk size
            'chunk_overlap': 1000,  # Increased overlap
            'min_chunk_size': 5000,  # Minimum chunk size
            'use_hybrid': True,
            'use_transformer': False,  # Disable heavy processing
            'use_spacy': True,
            'use_nltk': True
        }
    
    def process_sentences(self, transcript: str, source: str = "youtube", trader: str = "") -> Dict[str, Any]:
        """
        Process transcript using improved parallel processing
        """
        self.logger.info(f"Processing transcript for {trader} using improved parallel processor")
        self.logger.info(f"Transcript length: {len(transcript)} characters")
        
        start_time = time.time()
        
        # For smaller transcripts, use sequential processing
        if len(transcript) < self.config.get('min_chunk_size', 5000):
            self.logger.info("Transcript too small for parallel processing, using sequential")
            return self._process_sequential(transcript, source, trader)
        
        # Step 1: Preprocess transcript
        self.logger.info("Step 1: Preprocessing transcript...")
        cleaned_transcript = self._preprocess_transcript(transcript)
        
        # Step 2: Split into chunks with proper sentence boundaries
        self.logger.info("Step 2: Splitting transcript into chunks...")
        chunks = self._split_into_chunks_improved(cleaned_transcript)
        self.logger.info(f"Created {len(chunks)} chunks for parallel processing")
        
        # Step 3: Process chunks in parallel
        self.logger.info("Step 3: Processing chunks in parallel...")
        chunk_results = self._process_chunks_parallel(chunks)
        
        # Step 4: Merge results with improved logic
        self.logger.info("Step 4: Merging chunk results...")
        final_sentences = self._merge_chunk_results_improved(chunk_results, cleaned_transcript)
        
        # Step 5: Post-process sentences
        self.logger.info("Step 5: Post-processing sentences...")
        final_sentences = self._post_process_sentences(final_sentences)
        
        processing_time = time.time() - start_time
        self.logger.info(f"Total processing time: {processing_time:.2f} seconds")
        
        return {
            "source": source,
            "trader": trader,
            "original_transcript": transcript,
            "sentences": final_sentences,
            "sentence_count": len(final_sentences),
            "processing_date": datetime.now().strftime("%Y-%m-%d"),
            "processing_method": "parallel_improved",
            "chunks_processed": len(chunks),
            "workers_used": self.max_workers,
            "processing_time_seconds": processing_time,
            "confidence_scores": self._calculate_confidence_scores(final_sentences)
        }
    
    def _process_sequential(self, transcript: str, source: str, trader: str) -> Dict[str, Any]:
        """Fallback to sequential processing for small transcripts"""
        start_time = time.time()
        
        # Use simple but effective sentence splitting
        sentences = self._simple_sentence_split(transcript)
        
        processing_time = time.time() - start_time
        
        return {
            "source": source,
            "trader": trader,
            "original_transcript": transcript,
            "sentences": sentences,
            "sentence_count": len(sentences),
            "processing_date": datetime.now().strftime("%Y-%m-%d"),
            "processing_method": "sequential",
            "chunks_processed": 1,
            "workers_used": 1,
            "processing_time_seconds": processing_time,
            "confidence_scores": self._calculate_confidence_scores(sentences)
        }
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """Simple but effective sentence splitting"""
        # Clean up the text
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Split on sentence endings with better logic
        sentences = []
        current = ""
        
        # Split on periods, exclamation marks, and question marks
        # But be careful about abbreviations and numbers
        i = 0
        while i < len(text):
            char = text[i]
            current += char
            
            if char in self.sentence_endings:
                # Check if this is a real sentence ending
                if self._is_real_sentence_ending(text, i):
                    sentence = current.strip()
                    if len(sentence) >= self.config.get('min_sentence_length', 10):
                        sentences.append(sentence)
                    current = ""
            
            i += 1
        
        # Add remaining text
        if current.strip() and len(current.strip()) >= self.config.get('min_sentence_length', 10):
            sentences.append(current.strip())
        
        return sentences
    
    def _is_real_sentence_ending(self, text: str, pos: int) -> bool:
        """Check if a period/exclamation/question mark is a real sentence ending"""
        if pos >= len(text) - 1:
            return True
        
        # Look ahead to see what comes after
        next_char = text[pos + 1]
        
        # If next character is whitespace followed by uppercase, it's likely a sentence end
        if next_char.isspace():
            # Find the next non-whitespace character
            next_non_space = pos + 1
            while next_non_space < len(text) and text[next_non_space].isspace():
                next_non_space += 1
            
            if next_non_space < len(text):
                next_char = text[next_non_space]
                # If it's uppercase, it's likely a new sentence
                if next_char.isupper():
                    return True
        
        # Check for common abbreviations that shouldn't end sentences
        # Look back a few characters to see if this is an abbreviation
        if pos >= 2:
            # Common abbreviations
            abbrevs = ['Mr', 'Mrs', 'Dr', 'Prof', 'Inc', 'Ltd', 'Corp', 'Co', 'vs', 'etc', 'i.e', 'e.g']
            for abbrev in abbrevs:
                if pos >= len(abbrev):
                    start = pos - len(abbrev)
                    if text[start:pos].lower() == abbrev.lower():
                        return False
        
        # Check for numbers (like 1.5, 2.3, etc.)
        if pos >= 1 and text[pos-1].isdigit():
            # Look ahead to see if there are more digits
            if pos + 1 < len(text) and text[pos+1].isdigit():
                return False
        
        return True
    
    def _split_into_chunks_improved(self, text: str) -> List[Dict[str, Any]]:
        """Improved chunk splitting that respects sentence boundaries"""
        chunk_size = self.config.get('chunk_size', 10000)
        overlap = self.config.get('chunk_overlap', 1000)
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this isn't the last chunk, find a good break point
            if end < len(text):
                # Look for sentence endings within the overlap region
                overlap_start = max(start, end - overlap)
                overlap_end = min(len(text), end + overlap)
                
                # Find the best sentence boundary
                best_break = end
                for i in range(overlap_start, overlap_end):
                    if text[i] in self.sentence_endings:
                        # Look ahead to make sure we're at a complete sentence
                        next_char_pos = i + 1
                        while next_char_pos < len(text) and text[next_char_pos].isspace():
                            next_char_pos += 1
                        
                        # If next character is uppercase or end of text, it's a good break
                        if (next_char_pos >= len(text) or 
                            text[next_char_pos].isupper() or 
                            text[next_char_pos] in ['"', "'", '(']):
                            best_break = next_char_pos
                            break
                
                end = best_break
            
            chunk_text = text[start:end].strip()
            if chunk_text and len(chunk_text) >= self.config.get('min_sentence_length', 10):
                chunks.append({
                    'id': len(chunks),
                    'text': chunk_text,
                    'start_pos': start,
                    'end_pos': end
                })
            
            start = end
        
        return chunks
    
    def _process_chunks_parallel(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process chunks in parallel with improved error handling"""
        results = []
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all chunks for processing
            future_to_chunk = {
                executor.submit(self._process_single_chunk_improved, chunk): chunk 
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
                except Exception as e:
                    self.logger.error(f"Error processing chunk {chunk['id']}: {e}")
                    # Fallback to simple splitting
                    fallback_sentences = self._simple_sentence_split(chunk['text'])
                    results.append({
                        'chunk_id': chunk['id'],
                        'sentences': fallback_sentences,
                        'start_pos': chunk['start_pos'],
                        'end_pos': chunk['end_pos']
                    })
        
        # Sort results by chunk ID to maintain order
        results.sort(key=lambda x: x['chunk_id'])
        return results
    
    def _process_single_chunk_improved(self, chunk: Dict[str, Any]) -> List[str]:
        """Process a single chunk using the original models"""
        try:
            text = chunk['text']
            
            # Initialize all the original processors for this process
            rule_processor = RuleBasedProcessor()
            spacy_processor = SpacyProcessor()
            nltk_processor = NLTKProcessor()
            transformer_processor = TransformerProcessor()
            hybrid_processor = HybridProcessor()
            
            results = {}
            
            # Process with multiple methods (like the original)
            if self.config.get('use_rule', True):
                try:
                    results['rule'] = rule_processor.split_sentences(text)
                except Exception as e:
                    self.logger.debug(f"Rule-based processing failed: {e}")
                    results['rule'] = []
            
            if self.config.get('use_spacy', True):
                try:
                    results['spacy'] = spacy_processor.split_sentences(text)
                except Exception as e:
                    self.logger.debug(f"spaCy processing failed: {e}")
                    results['spacy'] = []
            
            if self.config.get('use_nltk', True):
                try:
                    results['nltk'] = nltk_processor.split_sentences(text)
                except Exception as e:
                    self.logger.debug(f"NLTK processing failed: {e}")
                    results['nltk'] = []
            
            if self.config.get('use_transformer', False):  # Keep disabled for performance
                try:
                    results['transformer'] = transformer_processor.split_sentences(text)
                except Exception as e:
                    self.logger.debug(f"Transformer processing failed: {e}")
                    results['transformer'] = []
            
            if self.config.get('use_hybrid', True):
                try:
                    results['hybrid'] = hybrid_processor.split_sentences(text, results)
                except Exception as e:
                    self.logger.debug(f"Hybrid processing failed: {e}")
                    results['hybrid'] = []
            
            # Combine results using the original logic
            final_sentences = self._combine_results(results, text)
            
            # Post-process sentences
            final_sentences = self._post_process_sentences(final_sentences)
            
            return final_sentences
            
        except Exception as e:
            # Fallback to simple splitting if all else fails
            self.logger.warning(f"All model processing failed, using fallback: {e}")
            return self._simple_sentence_split(chunk['text'])
    
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
    
    def _merge_chunk_results_improved(self, chunk_results: List[Dict[str, Any]], original_text: str) -> List[str]:
        """Improved merging of chunk results"""
        all_sentences = []
        
        for i, result in enumerate(chunk_results):
            sentences = result['sentences']
            
            # For overlapping chunks, remove duplicates
            if i > 0:
                prev_result = chunk_results[i-1]
                overlap_start = prev_result['end_pos'] - self.config.get('chunk_overlap', 1000)
                
                # Remove sentences that might be from overlap
                filtered_sentences = []
                for sentence in sentences:
                    # Check if this sentence appears in the previous chunk
                    is_duplicate = False
                    for prev_sentence in prev_result['sentences']:
                        if self._sentences_similar(sentence, prev_sentence):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        filtered_sentences.append(sentence)
                
                sentences = filtered_sentences
            
            all_sentences.extend(sentences)
        
        return all_sentences
    
    def _sentences_similar(self, sentence1: str, sentence2: str, threshold: float = 0.8) -> bool:
        """Check if two sentences are similar (for duplicate detection)"""
        # Simple similarity check
        words1 = set(sentence1.lower().split())
        words2 = set(sentence2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity > threshold
    
    def _preprocess_transcript(self, transcript: str) -> str:
        """Preprocess transcript for better sentence splitting"""
        # Remove excessive whitespace
        transcript = re.sub(r'\s+', ' ', transcript)
        
        # Normalize line breaks
        transcript = re.sub(r'\n+', ' ', transcript)
        
        return transcript
    
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
            
            processed.append(sentence)
        
        return processed
    
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


# Improved processor classes that actually use the models
class RuleBasedProcessor:
    def split_sentences(self, text: str) -> List[str]:
        """Rule-based sentence splitting with financial pattern protection"""
        sentences = []
        current = ""
        
        # Protect financial patterns first
        protected_text = self._protect_patterns(text)
        
        for char in protected_text:
            current += char
            if char in '.!?':
                sentence = current.strip()
                if sentence:
                    # Restore patterns and add sentence
                    sentence = self._restore_patterns(sentence)
                    sentences.append(sentence)
                current = ""
        
        if current.strip():
            sentence = self._restore_patterns(current.strip())
            sentences.append(sentence)
        
        return sentences
    
    def _protect_patterns(self, text: str) -> str:
        """Protect financial patterns from being split"""
        patterns = [
            r'\$\d+(?:\.\d{2})?',  # Dollar amounts
            r'\d+(?:\.\d{1,2})?%',  # Percentages
            r'\b[A-Z]{1,5}\b',  # Potential tickers
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                protected_text = f"__PROTECTED_{hash(match.group())}__"
                text = text.replace(match.group(), protected_text)
        return text
    
    def _restore_patterns(self, text: str) -> str:
        """Restore protected patterns"""
        # This is a simplified version - in practice, you'd maintain a mapping
        return text


class SpacyProcessor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self._add_financial_rules()
        except Exception as e:
            print(f"Could not load spaCy model: {e}")
            self.nlp = None
    
    def _add_financial_rules(self):
        """Add financial-specific rules to spaCy"""
        if not self.nlp:
            return
        
        # Add custom sentence boundary detection for financial text
        @Language.component("financial_sentence_splitter")
        def financial_sentence_splitter(doc):
            # Custom logic for financial text
            for token in doc:
                # Don't split on periods in numbers or abbreviations
                if token.text == '.':
                    if token.i > 0 and token.nbor(-1).like_num:
                        continue
                    if token.i < len(doc) - 1 and token.nbor(1).is_title:
                        token.is_sent_start = True
            return doc
        
        if "financial_sentence_splitter" not in self.nlp.pipe_names:
            self.nlp.add_pipe("financial_sentence_splitter", before="parser")
    
    def split_sentences(self, text: str) -> List[str]:
        if not self.nlp:
            return [text]
        
        try:
            doc = self.nlp(text)
            return [sent.text.strip() for sent in doc.sents]
        except Exception as e:
            print(f"spaCy processing failed: {e}")
            return [text]


class NLTKProcessor:
    def __init__(self):
        try:
            self.tokenizer = PunktSentenceTokenizer()
            self._train_financial_tokenizer()
        except Exception as e:
            print(f"Could not initialize NLTK: {e}")
            self.tokenizer = None
    
    def _train_financial_tokenizer(self):
        """Train tokenizer on financial text patterns"""
        try:
            # Add financial abbreviations to prevent false splits
            financial_abbrevs = [
                'Mr.', 'Mrs.', 'Dr.', 'Prof.', 'Inc.', 'Ltd.', 'Corp.', 'Co.',
                'vs.', 'etc.', 'i.e.', 'e.g.', 'U.S.', 'U.K.', 'A.M.', 'P.M.'
            ]
            
            for abbrev in financial_abbrevs:
                self.tokenizer._params.abbrev_types.add(abbrev.lower())
        except Exception as e:
            print(f"Could not train NLTK tokenizer: {e}")
    
    def split_sentences(self, text: str) -> List[str]:
        if not self.tokenizer:
            return [text]
        
        try:
            return self.tokenizer.tokenize(text)
        except Exception as e:
            print(f"NLTK processing failed: {e}")
            return [text]


class TransformerProcessor:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        # Disable transformer for now as it's too heavy for parallel processing
    
    def split_sentences(self, text: str) -> List[str]:
        # Return simple split for now
        return [text]


class HybridProcessor:
    def split_sentences(self, text: str, method_results: Dict[str, List[str]]) -> List[str]:
        """Hybrid approach that combines multiple methods"""
        if not method_results:
            return [text]
        
        # If only one method, use it
        if len(method_results) == 1:
            return list(method_results.values())[0]
        
        # Combine results using voting
        all_sentences = []
        for sentences in method_results.values():
            all_sentences.extend(sentences)
        
        # Remove duplicates and sort by position in text
        unique_sentences = []
        seen = set()
        
        for sentence in all_sentences:
            sentence_lower = sentence.lower().strip()
            if sentence_lower not in seen and len(sentence.strip()) > 10:
                seen.add(sentence_lower)
                unique_sentences.append(sentence.strip())
        
        return unique_sentences 