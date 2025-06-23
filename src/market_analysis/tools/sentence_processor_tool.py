from crewai.tools import BaseTool
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
import json
import re
import os
from datetime import datetime
from pathlib import Path

class SentenceProcessorInput(BaseModel):
    """Input schema for Sentence Processor Tool."""
    processed_data_file: str = Field(default="output/20250623/youtube_processed.json", description="Path to processed data file from previous agent")
    output_dir: str = Field(default="output/20250623", description="Output directory for saving sentence-processed files")

class SentenceProcessorTool(BaseTool):
    name: str = "Financial Context-Aware Sentence Processor"
    description: str = (
        "Reads processed YouTube data from previous agent, applies smart sentence boundary detection "
        "to each transcript, and saves sentence-processed data for the next agent."
    )
    args_schema: Type[BaseModel] = SentenceProcessorInput

    def _run(self, processed_data_file: str = "output/20250623/youtube_processed.json", output_dir: str = "output/20250623") -> str:
        """Execute sentence processing on data from previous agent."""
        try:
            # Check if output file already exists
            output_file = f"{output_dir}/sentences_processed.json"
            if os.path.exists(output_file):
                # Load existing file and return skip status
                existing_stats = self._get_existing_file_stats(output_file)
                return json.dumps({
                    "status": "skipped",
                    "reason": "Output file already exists",
                    "processing_time": datetime.now().isoformat(),
                    "input_file": processed_data_file,
                    "output_file": output_file,
                    "output_directory": output_dir,
                    "existing_statistics": existing_stats,
                    "summary": f"Skipped processing - found existing file with {existing_stats.get('total_sentences', 0)} sentences"
                }, indent=2)
            
            # Read processed data from previous agent
            processed_data = self._load_processed_data(processed_data_file)
            if not processed_data:
                return json.dumps({
                    "status": "error",
                    "error": f"Could not load processed data file: {processed_data_file}",
                    "processing_time": datetime.now().isoformat()
                })
            
            # Process sentences for each transcript
            sentence_processed_data = self._process_all_transcripts(processed_data)
            
            # Save sentence-processed data for next agent
            self._save_sentence_processed_data(sentence_processed_data, output_file)
            
            # Generate statistics
            stats = self._generate_processing_stats(sentence_processed_data)
            
            result = {
                "status": "success",
                "processing_time": datetime.now().isoformat(),
                "input_file": processed_data_file,
                "output_file": output_file,
                "output_directory": output_dir,
                "statistics": stats,
                "summary": f"Processed {stats['total_records']} transcript records into {stats['total_sentences']} sentences"
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "processing_time": datetime.now().isoformat()
            })

    def _load_processed_data(self, processed_data_file: str) -> Dict:
        """Load processed data from previous agent."""
        try:
            with open(processed_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading processed data file {processed_data_file}: {e}")
            return None

    def _process_all_transcripts(self, processed_data: Dict) -> Dict:
        """Process sentences for all transcript records."""
        # Extract data array from processed data structure
        data_records = processed_data.get("data", [])
        
        sentence_processed_records = []
        
        for record in data_records:
            # Each record has: source, trader, data (transcript text)
            transcript_text = record.get("data", "")
            channel_name = record.get("trader", "Unknown")
            source = record.get("source", "youtube")
            
            if transcript_text:
                # Process sentences for this transcript
                sentences = self._process_transcript_sentences(transcript_text, channel_name)
                
                # Create sentence-processed record
                sentence_record = {
                    "source": source,
                    "trader": channel_name,
                    "original_transcript": transcript_text,
                    "sentences": sentences,
                    "sentence_count": len(sentences),
                    "processing_date": datetime.now().strftime('%Y-%m-%d')
                }
                
                sentence_processed_records.append(sentence_record)
        
        # Preserve original statistics and add sentence processing info
        result = {
            "data": sentence_processed_records,
            "original_statistics": {
                "total_transcript_hours": processed_data.get("total_transcript_hours", 0),
                "total_videos_collected": processed_data.get("total_videos_collected", 0),
                "total_transcripts_collected": processed_data.get("total_transcripts_collected", 0)
            },
            "sentence_processing_date": datetime.now().strftime('%Y-%m-%d'),
            "sentence_processing_time": datetime.now().isoformat()
        }
        
        return result

    def _process_transcript_sentences(self, transcript_text: str, channel_name: str) -> List[str]:
        """Process a single transcript into sentences."""
        # Clean the transcript text
        cleaned_text = self._clean_transcript_text(transcript_text)
        
        # Smart sentence splitting
        sentences = self._smart_sentence_split(cleaned_text)
        
        # Post-process sentences
        processed_sentences = self._post_process_sentences(sentences)
        
        return processed_sentences

    def _save_sentence_processed_data(self, sentence_data: Dict, output_file: str):
        """Save sentence-processed data for next agent."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sentence_data, f, indent=2, ensure_ascii=False)

    def _get_existing_file_stats(self, output_file: str) -> Dict:
        """Get statistics from existing output file."""
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # Generate stats from existing data
            return self._generate_processing_stats(existing_data)
        except Exception as e:
            return {"error": f"Could not read existing file: {str(e)}", "total_sentences": 0}

    def _generate_processing_stats(self, sentence_data: Dict) -> Dict:
        """Generate processing statistics."""
        data_records = sentence_data.get("data", [])
        
        total_records = len(data_records)
        total_sentences = sum(record.get("sentence_count", 0) for record in data_records)
        
        # Get channel breakdown
        channel_stats = {}
        for record in data_records:
            channel = record.get("trader", "Unknown")
            if channel not in channel_stats:
                channel_stats[channel] = {"records": 0, "sentences": 0}
            channel_stats[channel]["records"] += 1
            channel_stats[channel]["sentences"] += record.get("sentence_count", 0)
        
        return {
            "total_records": total_records,
            "total_sentences": total_sentences,
            "avg_sentences_per_record": round(total_sentences / total_records, 1) if total_records > 0 else 0,
            "channel_breakdown": channel_stats
        }

    def _clean_transcript_text(self, text: str) -> str:
        """Clean transcript text while preserving financial context."""
        if not text:
            return ""
        
        # Basic cleaning
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'\s+([.!?])', r'\1', text)
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
        
        # Fix financial numbers
        text = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', text)
        text = re.sub(r'(\d+)\s*%', r'\1%', text)
        text = re.sub(r'\$\s*(\d+)', r'$\1', text)
        
        return text

    def _smart_sentence_split(self, text: str) -> List[str]:
        """Advanced financial context-aware sentence boundary detection."""
        if not text:
            return []
        
        # Step 1: Pre-process and protect financial patterns
        text = self._protect_financial_patterns(text)
        
        # Step 2: Split into potential sentences
        sentences = []
        current_sentence = ""
        
        # Use more sophisticated splitting
        # Split on periods, exclamation marks, and question marks
        parts = re.split(r'([.!?]+)\s*', text)
        
        i = 0
        while i < len(parts):
            if i % 2 == 0:  # Text part
                current_sentence += parts[i]
            else:  # Punctuation part
                punctuation = parts[i]
                current_sentence += punctuation
                
                # Check if this is a real sentence boundary
                next_text = parts[i+1] if i+1 < len(parts) else ""
                
                if self._is_real_sentence_boundary(current_sentence, next_text):
                    clean_sentence = self._restore_financial_patterns(current_sentence.strip())
                    if self._is_valid_sentence(clean_sentence):
                        sentences.append(clean_sentence)
                    current_sentence = ""
            i += 1
        
        # Add remaining text as final sentence
        if current_sentence.strip():
            clean_sentence = self._restore_financial_patterns(current_sentence.strip())
            if self._is_valid_sentence(clean_sentence):
                sentences.append(clean_sentence)
        
        # Step 3: Post-process to handle special cases
        sentences = self._merge_short_sentences(sentences)
        sentences = self._split_long_sentences(sentences)
        
        return sentences

    def _protect_financial_patterns(self, text: str) -> str:
        """Protect financial patterns from being split."""
        # Protect decimal numbers (prices, percentages)
        text = re.sub(r'(\d+)\.(\d+)', r'\1__DECIMAL__\2', text)
        
        # Protect ticker symbols
        text = re.sub(r'\b([A-Z]{1,5})\b', r'__TICKER__\1__TICKER__', text)
        
        # Protect common financial abbreviations
        abbrevs = [
            'vs.', 'Q1.', 'Q2.', 'Q3.', 'Q4.', 'P/E.', 'EPS.', 'CEO.', 'CFO.', 
            'Inc.', 'Corp.', 'Ltd.', 'LLC.', 'Co.', 'St.', 'Ave.', 'Dr.',
            'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Dr.', 'Ph.D.', 'M.D.', 'B.A.', 'M.S.'
        ]
        for abbrev in abbrevs:
            text = text.replace(abbrev, abbrev.replace('.', '__DOT__'))
        
        # Protect dollar amounts
        text = re.sub(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', r'__DOLLAR__\1__DOLLAR__', text)
        
        # Protect percentages
        text = re.sub(r'(\d+(?:\.\d+)?)%', r'__PERCENT__\1__PERCENT__', text)
        
        return text

    def _restore_financial_patterns(self, text: str) -> str:
        """Restore protected patterns."""
        text = re.sub(r'(\d+)__DECIMAL__(\d+)', r'\1.\2', text)
        text = re.sub(r'__TICKER__([A-Z]{1,5})__TICKER__', r'\1', text)
        text = text.replace('__DOT__', '.')
        text = re.sub(r'__DOLLAR__(\d+(?:,\d{3})*(?:\.\d{2})?)__DOLLAR__', r'$\1', text)
        text = re.sub(r'__PERCENT__(\d+(?:\.\d+)?)__PERCENT__', r'\1%', text)
        return text

    def _is_real_sentence_boundary(self, current_sentence: str, next_text: str) -> bool:
        """Determine if this is a real sentence boundary."""
        current_clean = current_sentence.strip()
        next_clean = next_text.strip() if next_text else ""
        
        # Must have minimum length
        if len(current_clean) < 10:
            return False
        
        # Don't split if next part starts with lowercase (continuation)
        if next_clean and next_clean[0].islower():
            return False
        
        # Don't split after common abbreviations
        abbrev_patterns = [
            r'\b(Inc|Corp|Ltd|LLC|Co|St|Ave|Dr|Mr|Mrs|Ms|Prof|Ph\.D|M\.D|B\.A|M\.S)\.$',
            r'\b(Q1|Q2|Q3|Q4|P/E|EPS|CEO|CFO)\.$',
            r'\b(vs)\.$'
        ]
        for pattern in abbrev_patterns:
            if re.search(pattern, current_clean, re.IGNORECASE):
                return False
        
        # Don't split decimal numbers
        if re.search(r'\d+\.$', current_clean) and next_clean:
            if re.match(r'^\d+\s*(billion|million|thousand|hundred)', next_clean, re.IGNORECASE):
                return False
        
        # Don't split after ticker symbols
        if re.search(r'[A-Z]{1,5}\.$', current_clean):
            return False
        
        # Don't split after dollar amounts
        if re.search(r'\$\d+\.$', current_clean):
            return False
        
        return True

    def _is_valid_sentence(self, sentence: str) -> bool:
        """Check if sentence is valid."""
        if not sentence or len(sentence) < 5:
            return False
        
        # Must contain at least one word character
        if not re.search(r'\w', sentence):
            return False
        
        # Filter out filler sentences
        filler_patterns = [
            r'^\s*[A-Za-z\s]*\s*$',  # Just letters and spaces
            r'^\s*[^\w]*\s*$',       # No word characters
        ]
        
        for pattern in filler_patterns:
            if re.match(pattern, sentence):
                return False
        
        return True

    def _merge_short_sentences(self, sentences: List[str]) -> List[str]:
        """Merge very short sentences that should be together."""
        if len(sentences) <= 1:
            return sentences
        
        merged = []
        i = 0
        
        while i < len(sentences):
            current = sentences[i]
            
            # If current sentence is very short and next exists, try to merge
            if len(current) < 50 and i + 1 < len(sentences):
                next_sentence = sentences[i + 1]
                
                # Check if they should be merged
                if self._should_merge_sentences(current, next_sentence):
                    merged_sentence = current + " " + next_sentence
                    merged.append(merged_sentence)
                    i += 2  # Skip next sentence
                    continue
            
            merged.append(current)
            i += 1
        
        return merged

    def _should_merge_sentences(self, sentence1: str, sentence2: str) -> bool:
        """Determine if two sentences should be merged."""
        # Merge if first sentence ends with common continuation words
        continuation_words = [
            'and', 'but', 'or', 'so', 'because', 'since', 'while', 'when',
            'if', 'although', 'however', 'therefore', 'meanwhile', 'then'
        ]
        
        sentence1_lower = sentence1.lower().strip()
        sentence2_lower = sentence2.lower().strip()
        
        # Check if first sentence ends with continuation word
        for word in continuation_words:
            if sentence1_lower.endswith(f" {word}"):
                return True
        
        # Check if second sentence starts with lowercase (continuation)
        if sentence2 and sentence2[0].islower():
            return True
        
        # Check if they're part of a list or enumeration
        if re.search(r'\d+\.$', sentence1) and sentence2:
            return True
        
        return False

    def _split_long_sentences(self, sentences: List[str]) -> List[str]:
        """Split very long sentences that contain multiple thoughts."""
        result = []
        
        for sentence in sentences:
            if len(sentence) > 200:  # Very long sentence
                # Try to split on common financial connectors
                splits = self._split_long_sentence(sentence)
                result.extend(splits)
            else:
                result.append(sentence)
        
        return result

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Split a long sentence on logical boundaries."""
        # Common financial connectors that often separate thoughts
        connectors = [
            r'\s+but\s+', r'\s+however\s+', r'\s+meanwhile\s+', r'\s+then\s+',
            r'\s+also\s+', r'\s+additionally\s+', r'\s+furthermore\s+',
            r'\s+on the other hand\s+', r'\s+in contrast\s+', r'\s+conversely\s+'
        ]
        
        for connector in connectors:
            if re.search(connector, sentence, re.IGNORECASE):
                parts = re.split(connector, sentence, flags=re.IGNORECASE)
                if len(parts) > 1:
                    # Reconstruct with connector
                    result = []
                    for i, part in enumerate(parts):
                        if i == 0:
                            result.append(part.strip())
                        else:
                            # Add connector back to the part
                            connector_match = re.search(connector, sentence, re.IGNORECASE)
                            if connector_match:
                                connector_text = connector_match.group(0)
                                result.append(connector_text + part.strip())
                    return [s for s in result if len(s) > 20]  # Filter out very short parts
        
        # If no good split point found, return original
        return [sentence]

    def _post_process_sentences(self, sentences: List[str]) -> List[str]:
        """Post-process sentences for quality."""
        processed = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Skip short or empty sentences
            if len(sentence) < 5:
                continue
            
            # Skip punctuation-only sentences
            if re.match(r'^[^a-zA-Z]*$', sentence):
                continue
            
            # Ensure proper punctuation
            if not sentence[-1] in '.!?':
                sentence += '.'
            
            # Clean artifacts
            sentence = self._clean_artifacts(sentence)
            processed.append(sentence)
        
        return processed

    def _clean_artifacts(self, sentence: str) -> str:
        """Clean transcript artifacts."""
        # Remove filler words at start
        filler_patterns = [
            r'^(um|uh|like|you know|so)\s+',
            r'^(okay|alright|now)\s+',
        ]
        
        for pattern in filler_patterns:
            sentence = re.sub(pattern, '', sentence, flags=re.IGNORECASE)
        
        # Clean spaces and capitalize
        sentence = re.sub(r'\s+', ' ', sentence).strip()
        if sentence and sentence[0].islower():
            sentence = sentence[0].upper() + sentence[1:]
        
        return sentence 