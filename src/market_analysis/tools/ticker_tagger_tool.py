from crewai.tools import BaseTool
from typing import Type, List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
import json
import yaml
import re
import os
from datetime import datetime
from pathlib import Path

class TickerTaggerInput(BaseModel):
    """Input schema for Ticker Tagger Tool."""
    sentences_file: str = Field(default="output/20250623/sentences_processed.json", description="Path to sentence-processed data")
    asset_mapping_file: str = Field(default="config/asset_mapping.yaml", description="Path to asset mapping config")
    output_dir: str = Field(default="output/20250623", description="Output directory")

class TickerTaggerTool(BaseTool):
    name: str = "Intelligent Ticker Attribution Tool"
    description: str = "Tags sentences with ticker symbols using context inheritance"
    args_schema: Type[BaseModel] = TickerTaggerInput

    def _run(self, sentences_file: str = "output/20250623/sentences_processed.json", 
             asset_mapping_file: str = "config/asset_mapping.yaml", 
             output_dir: str = "output/20250623") -> str:
        """Execute ticker tagging with context inheritance."""
        try:
            # Check if output file already exists
            output_file = f"{output_dir}/ticker_tagged.json"
            if os.path.exists(output_file):
                # Load existing file and return skip status
                existing_stats = self._get_existing_file_stats(output_file)
                return json.dumps({
                    "status": "skipped",
                    "reason": "Output file already exists",
                    "processing_time": datetime.now().isoformat(),
                    "input_file": sentences_file,
                    "asset_mapping_file": asset_mapping_file,
                    "output_file": output_file,
                    "existing_statistics": existing_stats,
                    "summary": f"Skipped processing - found existing file with {existing_stats.get('total_sentences', 0)} sentences tagged"
                }, indent=2)
            
            # Load data
            sentences_data = self._load_sentences_data(sentences_file)
            asset_mapping = self._load_asset_mapping(asset_mapping_file)
            
            if not sentences_data or not asset_mapping:
                return json.dumps({"status": "error", "error": "Could not load required files"})
            
            # Process ticker tagging
            ticker_tagged_data = self._process_ticker_tagging(sentences_data, asset_mapping)
            
            # Save results
            self._save_ticker_tagged_data(ticker_tagged_data, output_file)
            
            # Generate stats
            stats = self._generate_tagging_stats(ticker_tagged_data)
            
            return json.dumps({
                "status": "success",
                "processing_time": datetime.now().isoformat(),
                "output_file": output_file,
                "statistics": stats,
                "summary": f"Tagged {stats['total_sentences']} sentences with {stats['total_attributions']} ticker attributions"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    def _load_sentences_data(self, file_path: str) -> Dict:
        """Load sentence data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def _load_asset_mapping(self, file_path: str) -> Dict:
        """Load asset mapping."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except:
            return None

    def _process_ticker_tagging(self, sentences_data: Dict, asset_mapping: Dict) -> Dict:
        """Process ticker tagging for all records."""
        data_records = sentences_data.get("data", [])
        tagged_records = []
        
        for record in data_records:
            tagged_record = self._tag_record_sentences(record, asset_mapping)
            tagged_records.append(tagged_record)
        
        result = sentences_data.copy()
        result["data"] = tagged_records
        result["ticker_tagging_date"] = datetime.now().strftime('%Y-%m-%d')
        
        return result

    def _tag_record_sentences(self, record: Dict, asset_mapping: Dict) -> Dict:
        """Tag sentences in a single record with context inheritance."""
        sentences = record.get("sentences", [])
        tagged_sentences = []
        context_tickers = []  # Context stack for inheritance
        
        for i, sentence in enumerate(sentences):
            # Find direct ticker mentions
            direct_tickers = self._find_direct_tickers(sentence, asset_mapping)
            
            # Apply context inheritance if no direct mentions
            inherited_tickers = []
            if not direct_tickers and context_tickers:
                inherited_tickers = self._apply_inheritance(sentence, context_tickers)
            
            # Combine all tickers
            all_tickers = list(set(direct_tickers + inherited_tickers))
            
            # Update context for next sentences
            if direct_tickers:
                context_tickers = direct_tickers
            elif self._is_topic_transition(sentence):
                context_tickers = []
            
            # Create tagged sentence
            tagged_sentence = {
                "sentence_id": i + 1,
                "sentence": sentence,
                "direct_tickers": direct_tickers,
                "inherited_tickers": inherited_tickers,
                "all_tickers": all_tickers,
                "has_tickers": len(all_tickers) > 0
            }
            
            tagged_sentences.append(tagged_sentence)
        
        # Create enhanced record
        enhanced_record = record.copy()
        enhanced_record["tagged_sentences"] = tagged_sentences
        enhanced_record["ticker_summary"] = self._create_ticker_summary(tagged_sentences)
        
        return enhanced_record

    def _find_direct_tickers(self, sentence: str, asset_mapping: Dict) -> List[str]:
        """Find direct ticker mentions in sentence."""
        found_tickers = []
        sentence_lower = sentence.lower()
        
        # Check all asset categories with correct names
        categories = ['stocks', 'indices', 'sector_etfs', 'crypto', 'commodities', 'forex', 'indicators', 'meme_stocks', 'real_estate', 'international', 'bonds']
        
        for category in categories:
            if category in asset_mapping:
                for ticker, ticker_data in asset_mapping[category].items():
                    # Handle both old format (list of aliases) and new format (dict with aliases key)
                    if isinstance(ticker_data, dict) and 'aliases' in ticker_data:
                        aliases = ticker_data['aliases']
                    elif isinstance(ticker_data, list):
                        aliases = ticker_data
                    else:
                        continue
                    
                    # Check for exact ticker symbol first
                    if ticker.lower() in sentence_lower:
                        found_tickers.append(ticker)
                        continue
                    
                    # Check aliases with word boundaries to avoid false matches
                    for alias in aliases:
                        # Use word boundaries to avoid partial matches
                        pattern = r'\b' + re.escape(alias.lower()) + r'\b'
                        if re.search(pattern, sentence_lower):
                            found_tickers.append(ticker)
                            break
        
        return list(set(found_tickers))

    def _apply_inheritance(self, sentence: str, context_tickers: List[str]) -> List[str]:
        """Apply context inheritance based on sentence content."""
        sentence_lower = sentence.lower()
        
        # Check for inheritance indicators
        inheritance_patterns = [
            r'\bthey\b', r'\bit\b', r'\bthis\b', r'\bthat\b',
            r'\bthe stock\b', r'\bthe company\b',
            r'\bis up\b', r'\bis down\b', r'\bsupport\b', r'\bresistance\b'
        ]
        
        has_inheritance_signal = any(re.search(pattern, sentence_lower) for pattern in inheritance_patterns)
        
        return context_tickers if has_inheritance_signal else []

    def _is_topic_transition(self, sentence: str) -> bool:
        """Check if sentence indicates topic transition."""
        transition_words = ["switching to", "moving on", "next up", "now", "regarding"]
        sentence_lower = sentence.lower()
        return any(word in sentence_lower for word in transition_words)

    def _create_ticker_summary(self, tagged_sentences: List[Dict]) -> Dict:
        """Create summary for tagged sentences."""
        total = len(tagged_sentences)
        with_tickers = sum(1 for s in tagged_sentences if s["has_tickers"])
        with_inheritance = sum(1 for s in tagged_sentences if s["inherited_tickers"])
        
        ticker_counts = {}
        for sentence in tagged_sentences:
            for ticker in sentence["all_tickers"]:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        return {
            "total_sentences": total,
            "sentences_with_tickers": with_tickers,
            "sentences_with_inheritance": with_inheritance,
            "unique_tickers": list(ticker_counts.keys()),
            "ticker_counts": ticker_counts
        }

    def _save_ticker_tagged_data(self, data: Dict, output_file: str):
        """Save ticker-tagged data."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_existing_file_stats(self, output_file: str) -> Dict:
        """Get statistics from existing output file."""
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # Generate stats from existing data
            return self._generate_tagging_stats(existing_data)
        except Exception as e:
            return {"error": f"Could not read existing file: {str(e)}", "total_sentences": 0}

    def _generate_tagging_stats(self, data: Dict) -> Dict:
        """Generate overall tagging statistics."""
        records = data.get("data", [])
        
        total_sentences = 0
        total_attributions = 0
        total_inheritance = 0
        all_tickers = set()
        
        for record in records:
            summary = record.get("ticker_summary", {})
            total_sentences += summary.get("total_sentences", 0)
            total_attributions += summary.get("sentences_with_tickers", 0)
            total_inheritance += summary.get("sentences_with_inheritance", 0)
            all_tickers.update(summary.get("unique_tickers", []))
        
        return {
            "total_sentences": total_sentences,
            "total_attributions": total_attributions,
            "total_inheritance": total_inheritance,
            "unique_tickers": len(all_tickers),
            "attribution_rate": round(total_attributions / total_sentences, 3) if total_sentences > 0 else 0
        } 