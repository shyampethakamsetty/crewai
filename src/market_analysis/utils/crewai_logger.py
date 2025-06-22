import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
import json
import threading
from pathlib import Path

class CrewAILogHandler(logging.Handler):
    """Custom log handler that captures CrewAI's verbose output."""
    
    def __init__(self, log_file: str, level=logging.NOTSET):
        super().__init__(level)
        self.log_file = log_file
        self.file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        self.file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
    def emit(self, record):
        try:
            # Write to our log file
            self.file_handler.emit(record)
        except Exception:
            pass

class CrewAILogger:
    """Advanced logger for CrewAI with comprehensive output capture."""
    
    def __init__(self, log_dir: str = "logs", enable_console: bool = True):
        self.log_dir = Path(log_dir)
        self.enable_console = enable_console
        self.setup_log_directory()
        
        # Create timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"crewai_run_{self.timestamp}.log"
        self.log_filepath = self.log_dir / self.log_filename
        
        # Setup logging
        self.setup_logging()
        
        # Store original loggers
        self.original_handlers = {}
        
    def setup_log_directory(self):
        """Ensure logs directory exists."""
        self.log_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Setup comprehensive logging for CrewAI."""
        # Create our main logger
        self.logger = logging.getLogger('crewai_run')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler for detailed logging
        file_handler = logging.FileHandler(self.log_filepath, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler if enabled
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def capture_crewai_loggers(self):
        """Capture and redirect CrewAI's internal loggers."""
        crewai_loggers = [
            'crewai',
            'crewai.agents',
            'crewai.tasks', 
            'crewai.crew',
            'crewai.tools',
            'langchain',
            'openai',
            'anthropic'
        ]
        
        for logger_name in crewai_loggers:
            logger = logging.getLogger(logger_name)
            
            # Store original handlers
            self.original_handlers[logger_name] = logger.handlers.copy()
            
            # Add our custom handler
            custom_handler = CrewAILogHandler(str(self.log_filepath))
            logger.addHandler(custom_handler)
            
            # Ensure the logger is at DEBUG level to capture everything
            logger.setLevel(logging.DEBUG)
    
    def restore_crewai_loggers(self):
        """Restore original CrewAI logger handlers."""
        for logger_name, original_handlers in self.original_handlers.items():
            logger = logging.getLogger(logger_name)
            
            # Remove our custom handlers
            logger.handlers = [h for h in logger.handlers 
                             if not isinstance(h, CrewAILogHandler)]
            
            # Restore original handlers
            logger.handlers.extend(original_handlers)
    
    @contextmanager
    def capture_crewai_output(self):
        """Context manager to capture all CrewAI output."""
        try:
            # Log run start
            self.log_run_start()
            
            # Capture CrewAI loggers
            self.capture_crewai_loggers()
            
            yield
            
        finally:
            # Restore original loggers
            self.restore_crewai_loggers()
            
            # Log run end
            self.log_run_end()
    
    def log_run_start(self):
        """Log the start of a CrewAI run."""
        self.logger.info("=" * 80)
        self.logger.info("CREWAI RUN STARTED")
        self.logger.info("=" * 80)
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info(f"Log file: {self.log_filepath}")
        self.logger.info("=" * 80)
    
    def log_run_end(self):
        """Log the end of a CrewAI run."""
        self.logger.info("=" * 80)
        self.logger.info("CREWAI RUN COMPLETED")
        self.logger.info("=" * 80)
    
    def log_configuration(self, inputs: Dict[str, Any]):
        """Log the configuration parameters."""
        self.logger.info("CONFIGURATION:")
        self.logger.info("-" * 40)
        for key, value in inputs.items():
            self.logger.info(f"  {key}: {value}")
        self.logger.info("-" * 40)
    
    def log_results(self, result, output_file: str):
        """Log the results of the run."""
        self.logger.info("RESULTS:")
        self.logger.info("-" * 40)
        self.logger.info(f"Output file: {output_file}")
        self.logger.info(f"Result type: {type(result).__name__}")
        
        if hasattr(result, '__dict__'):
            self.logger.info(f"Result attributes: {list(result.__dict__.keys())}")
        
        # Log result content if available
        if hasattr(result, 'raw') and result.raw:
            self.logger.info("Raw result content available")
        elif hasattr(result, 'output') and result.output:
            self.logger.info("Output content available")
        
        self.logger.info("-" * 40)
    
    def log_error(self, error: Exception, context: str = ""):
        """Log errors with full context."""
        self.logger.error(f"ERROR in {context}: {str(error)}")
        self.logger.error(f"Error type: {type(error).__name__}")
        import traceback
        self.logger.error(f"Traceback:\n{traceback.format_exc()}")
    
    def get_log_filepath(self) -> str:
        """Get the current log file path."""
        return str(self.log_filepath)
    
    def get_latest_log_file(self) -> Optional[str]:
        """Get the path to the most recent log file."""
        if not self.log_dir.exists():
            return None
            
        log_files = list(self.log_dir.glob("crewai_run_*.log"))
        if not log_files:
            return None
            
        # Sort by modification time (newest first)
        latest_file = max(log_files, key=lambda f: f.stat().st_mtime)
        return str(latest_file)
    
    def log_separator(self, message: str = ""):
        """Log a separator line."""
        if message:
            self.logger.info(f"--- {message} ---")
        else:
            self.logger.info("-" * 40)
    
    def log_agent_activity(self, agent_name: str, activity: str):
        """Log specific agent activities."""
        self.logger.info(f"AGENT [{agent_name}]: {activity}")
    
    def log_tool_execution(self, tool_name: str, input_data: str, output_data: str):
        """Log tool executions."""
        self.logger.info(f"TOOL [{tool_name}] EXECUTED:")
        self.logger.info(f"  Input: {input_data}")
        self.logger.info(f"  Output: {output_data}")
        self.logger.info("-" * 40) 