import re
import json
import logging
from typing import List, Dict, Any, Tuple, Set
from datetime import datetime
import yaml
from pathlib import Path
import spacy
from spacy.tokens import Doc, Token
from spacy.matcher import Matcher
import yfinance as yf
from fuzzywuzzy import fuzz
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import numpy as np
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

class AdvancedTickerTagger:
    """
    Advanced ticker tagger combining multiple approaches for maximum accuracy:
    1. Rule-based regex matching with word boundaries
    2. spaCy NER with custom patterns
    3. Fuzzy matching with company names
    4. BERT-based sequence labeling
    5. Multi-source data validation
    6. Context-aware disambiguation
    """
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialize multiple taggers
        self.regex_tagger = RegexTickerTagger()
        self.spacy_tagger = SpacyTickerTagger()
        self.fuzzy_tagger = FuzzyTickerTagger()
        self.bert_tagger = BERTTickerTagger()
        self.context_tagger = ContextAwareTickerTagger()
        
        # Load comprehensive asset mapping
        self.asset_mapping = self._load_comprehensive_asset_mapping()
        
        # Financial context words
        self.financial_context_words = {
            'trading', 'stock', 'shares', 'price', 'market', 'options',
            'put', 'call', 'strike', 'expiration', 'premium', 'volume',
            'earnings', 'revenue', 'profit', 'loss', 'dividend', 'split',
            'ipo', 'merger', 'acquisition', 'analyst', 'rating', 'target'
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            'confidence_threshold': 0.7,
            'use_regex': True,
            'use_spacy': True,
            'use_fuzzy': True,
            'use_bert': True,
            'use_context': True,
            'validate_with_yahoo': True,
            'max_fuzzy_ratio': 85
        }
    
    def _load_comprehensive_asset_mapping(self) -> Dict[str, List[str]]:
        """Load comprehensive asset mapping from multiple sources"""
        mapping = {}
        
        # Load from config file
        config_path = Path("config/asset_mapping.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                for category, assets in config_data.items():
                    for asset in assets:
                        if isinstance(asset, dict):
                            ticker = asset.get('ticker', '')
                            aliases = asset.get('aliases', [])
                            if ticker:
                                mapping[ticker] = aliases
                        elif isinstance(asset, str):
                            # Assume it's a ticker
                            mapping[asset] = [asset]
        
        # Add common tickers that might be missing
        common_tickers = {
            'PLTR': ['palantir', 'palanteer', 'palenter'],
            'AAPL': ['apple', 'appl'],
            'TSLA': ['tesla'],
            'NVDA': ['nvidia'],
            'MSFT': ['microsoft'],
            'GOOGL': ['google', 'alphabet'],
            'AMZN': ['amazon'],
            'META': ['facebook', 'meta'],
            'SPY': ['spdr s&p 500 etf', 'spyder'],
            'QQQ': ['invesco qqq trust', 'nasdaq etf'],
            'IWM': ['ishares russell 2000 etf'],
            'VTI': ['vanguard total stock market etf'],
            'VOO': ['vanguard s&p 500 etf'],
            'ARKK': ['ark innovation etf'],
            'TQQQ': ['proshares ultrapro qqq'],
            'SQQQ': ['proshares ultrapro short qqq'],
            'SOXL': ['direxion daily semiconductor bull 3x'],
            'SOXS': ['direxion daily semiconductor bear 3x']
        }
        
        for ticker, aliases in common_tickers.items():
            if ticker not in mapping:
                mapping[ticker] = aliases
            else:
                # Merge aliases
                existing_aliases = mapping[ticker]
                mapping[ticker] = list(set(existing_aliases + aliases))
        
        return mapping
    
    def tag_sentences(self, sentences: List[Dict[str, Any]], source: str = "youtube", trader: str = "") -> Dict[str, Any]:
        """
        Tag sentences with tickers using multiple approaches
        """
        self.logger.info(f"Tagging {len(sentences)} sentences for {trader} using advanced ticker tagger")
        
        tagged_sentences = []
        all_tickers = set()
        ticker_counts = {}
        
        for sentence_data in sentences:
            sentence_id = sentence_data.get('sentence_id', len(tagged_sentences) + 1)
            sentence_text = sentence_data.get('sentence', '')
            
            # Get tickers from multiple methods
            ticker_results = {}
            
            if self.config.get('use_regex', True):
                ticker_results['regex'] = self.regex_tagger.extract_tickers(sentence_text, self.asset_mapping)
            
            if self.config.get('use_spacy', True):
                ticker_results['spacy'] = self.spacy_tagger.extract_tickers(sentence_text, self.asset_mapping)
            
            if self.config.get('use_fuzzy', True):
                ticker_results['fuzzy'] = self.fuzzy_tagger.extract_tickers(sentence_text, self.asset_mapping)
            
            if self.config.get('use_bert', True):
                ticker_results['bert'] = self.bert_tagger.extract_tickers(sentence_text, self.asset_mapping)
            
            if self.config.get('use_context', True):
                ticker_results['context'] = self.context_tagger.extract_tickers(sentence_text, self.asset_mapping)
            
            # Combine and validate tickers
            final_tickers = self._combine_ticker_results(ticker_results, sentence_text)
            
            # Validate tickers with external sources if enabled
            if self.config.get('validate_with_yahoo', True):
                final_tickers = self._validate_tickers(final_tickers)
            
            # Update statistics
            for ticker in final_tickers:
                all_tickers.add(ticker)
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
            
            # Create tagged sentence
            tagged_sentence = {
                "sentence_id": sentence_id,
                "sentence": sentence_text,
                "direct_tickers": final_tickers,
                "inherited_tickers": [],  # Will be filled by inheritance logic
                "all_tickers": final_tickers,
                "has_tickers": len(final_tickers) > 0,
                "confidence_scores": self._calculate_ticker_confidence(ticker_results, final_tickers)
            }
            
            tagged_sentences.append(tagged_sentence)
        
        # Apply ticker inheritance logic
        tagged_sentences = self._apply_ticker_inheritance(tagged_sentences)
        
        return {
            "source": source,
            "trader": trader,
            "original_transcript": sentences[0].get('original_transcript', '') if sentences else '',
            "sentences": [s.get('sentence', '') for s in sentences],
            "sentence_count": len(sentences),
            "processing_date": datetime.now().strftime("%Y-%m-%d"),
            "tagged_sentences": tagged_sentences,
            "ticker_summary": {
                "total_sentences": len(sentences),
                "sentences_with_tickers": len([s for s in tagged_sentences if s['has_tickers']]),
                "sentences_with_inheritance": len([s for s in tagged_sentences if s['inherited_tickers']]),
                "unique_tickers": list(all_tickers),
                "ticker_counts": ticker_counts
            }
        }
    
    def _combine_ticker_results(self, ticker_results: Dict[str, List[str]], sentence_text: str) -> List[str]:
        """Combine ticker results from multiple methods using voting"""
        if not ticker_results:
            return []
        
        # Count occurrences of each ticker across methods
        ticker_votes = {}
        for method, tickers in ticker_results.items():
            for ticker in tickers:
                if ticker not in ticker_votes:
                    ticker_votes[ticker] = {'count': 0, 'methods': []}
                ticker_votes[ticker]['count'] += 1
                ticker_votes[ticker]['methods'].append(method)
        
        # Select tickers with sufficient agreement
        min_agreement = max(1, len(ticker_results) // 2)  # At least half of methods agree
        final_tickers = []
        
        for ticker, votes in ticker_votes.items():
            if votes['count'] >= min_agreement:
                # Additional confidence check for single-method matches
                if votes['count'] == 1:
                    method = votes['methods'][0]
                    if method in ['spacy', 'bert']:  # Higher confidence methods
                        final_tickers.append(ticker)
                else:
                    final_tickers.append(ticker)
        
        return list(set(final_tickers))  # Remove duplicates
    
    def _validate_tickers(self, tickers: List[str]) -> List[str]:
        """Validate tickers using external sources"""
        validated_tickers = []
        
        def validate_single_ticker(ticker):
            try:
                # Try to get info from Yahoo Finance
                stock = yf.Ticker(ticker)
                info = stock.info
                if info and 'regularMarketPrice' in info:
                    return ticker
            except:
                pass
            return None
        
        # Validate tickers in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ticker = {executor.submit(validate_single_ticker, ticker): ticker for ticker in tickers}
            for future in as_completed(future_to_ticker):
                result = future.result()
                if result:
                    validated_tickers.append(result)
        
        return validated_tickers if validated_tickers else tickers  # Fallback to original if validation fails
    
    def _apply_ticker_inheritance(self, tagged_sentences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply ticker inheritance logic"""
        current_context_tickers = []
        
        for sentence in tagged_sentences:
            # Add direct tickers to context
            if sentence['direct_tickers']:
                current_context_tickers = sentence['direct_tickers']
            else:
                # Inherit from previous context
                sentence['inherited_tickers'] = current_context_tickers.copy()
                sentence['all_tickers'] = list(set(sentence['direct_tickers'] + sentence['inherited_tickers']))
                sentence['has_tickers'] = len(sentence['all_tickers']) > 0
        
        return tagged_sentences
    
    def _calculate_ticker_confidence(self, ticker_results: Dict[str, List[str]], final_tickers: List[str]) -> Dict[str, float]:
        """Calculate confidence scores for ticker detection methods"""
        confidence_scores = {}
        
        for method, tickers in ticker_results.items():
            if not tickers:
                confidence_scores[method] = 0.0
                continue
            
            # Calculate precision and recall
            true_positives = len(set(tickers) & set(final_tickers))
            precision = true_positives / len(tickers) if tickers else 0
            recall = true_positives / len(final_tickers) if final_tickers else 1
            
            # F1 score
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            confidence_scores[method] = round(f1, 3)
        
        return confidence_scores


class RegexTickerTagger:
    """Rule-based regex ticker tagger with word boundaries"""
    
    def extract_tickers(self, text: str, asset_mapping: Dict[str, List[str]]) -> List[str]:
        """Extract tickers using regex with word boundaries"""
        tickers = []
        
        for ticker, aliases in asset_mapping.items():
            # Create pattern with word boundaries for each alias
            for alias in aliases:
                # Use word boundaries to avoid false positives
                pattern = r'\b' + re.escape(alias) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    tickers.append(ticker)
                    break  # Found this ticker, move to next
        
        return list(set(tickers))  # Remove duplicates


class SpacyTickerTagger:
    """spaCy-based ticker tagger with custom NER"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self._add_ticker_patterns()
        except OSError:
            self.nlp = spacy.blank("en")
    
    def _add_ticker_patterns(self):
        """Add custom ticker patterns to spaCy"""
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        
        # Add patterns for common tickers
        patterns = [
            {"label": "TICKER", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{1,5}$"}}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "palantir"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "apple"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "tesla"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "nvidia"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "microsoft"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "google"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "amazon"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "facebook"}]},
            {"label": "COMPANY", "pattern": [{"LOWER": "meta"}]},
        ]
        
        ruler.add_patterns(patterns)
    
    def extract_tickers(self, text: str, asset_mapping: Dict[str, List[str]]) -> List[str]:
        """Extract tickers using spaCy NER"""
        doc = self.nlp(text)
        tickers = []
        
        for ent in doc.ents:
            if ent.label_ in ["TICKER", "COMPANY"]:
                # Map entity text to ticker symbol
                ticker = self._map_entity_to_ticker(ent.text, asset_mapping)
                if ticker:
                    tickers.append(ticker)
        
        return list(set(tickers))
    
    def _map_entity_to_ticker(self, entity_text: str, asset_mapping: Dict[str, List[str]]) -> str:
        """Map entity text to ticker symbol"""
        entity_lower = entity_text.lower()
        
        for ticker, aliases in asset_mapping.items():
            if entity_lower in [alias.lower() for alias in aliases]:
                return ticker
        
        return None


class FuzzyTickerTagger:
    """Fuzzy matching ticker tagger"""
    
    def extract_tickers(self, text: str, asset_mapping: Dict[str, List[str]]) -> List[str]:
        """Extract tickers using fuzzy matching"""
        tickers = []
        text_lower = text.lower()
        
        for ticker, aliases in asset_mapping.items():
            for alias in aliases:
                # Use fuzzy matching for company names
                ratio = fuzz.partial_ratio(text_lower, alias.lower())
                if ratio >= 85:  # High confidence threshold
                    tickers.append(ticker)
                    break
        
        return list(set(tickers))


class BERTTickerTagger:
    """BERT-based ticker tagger"""
    
    def __init__(self):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
            self.model = AutoModelForTokenClassification.from_pretrained("bert-base-uncased")
        except Exception as e:
            self.tokenizer = None
            self.model = None
    
    def extract_tickers(self, text: str, asset_mapping: Dict[str, List[str]]) -> List[str]:
        """Extract tickers using BERT model"""
        if not self.tokenizer or not self.model:
            return []
        
        try:
            # Tokenize text
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            # Get model predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Extract tickers from predictions (simplified)
            # In practice, you'd need a fine-tuned model for ticker detection
            return self._extract_tickers_from_outputs(outputs, inputs, asset_mapping)
        
        except Exception as e:
            return []
    
    def _extract_tickers_from_outputs(self, outputs, inputs, asset_mapping):
        """Extract tickers from BERT outputs"""
        # Simplified implementation - would need proper fine-tuning
        tokens = self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
        tickers = []
        
        for token in tokens:
            if token.upper() in asset_mapping:
                tickers.append(token.upper())
        
        return list(set(tickers))


class ContextAwareTickerTagger:
    """Context-aware ticker tagger"""
    
    def __init__(self):
        self.financial_context_words = {
            'trading', 'stock', 'shares', 'price', 'market', 'options',
            'put', 'call', 'strike', 'expiration', 'premium', 'volume',
            'earnings', 'revenue', 'profit', 'loss', 'dividend', 'split'
        }
    
    def extract_tickers(self, text: str, asset_mapping: Dict[str, List[str]]) -> List[str]:
        """Extract tickers with context validation"""
        # First, get potential tickers using regex
        potential_tickers = []
        for ticker, aliases in asset_mapping.items():
            for alias in aliases:
                pattern = r'\b' + re.escape(alias) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    potential_tickers.append(ticker)
                    break
        
        # Validate with context
        validated_tickers = []
        text_lower = text.lower()
        
        for ticker in potential_tickers:
            if self._has_financial_context(text_lower):
                validated_tickers.append(ticker)
        
        return validated_tickers
    
    def _has_financial_context(self, text: str) -> bool:
        """Check if text has financial context"""
        words = set(text.split())
        return bool(words & self.financial_context_words) 