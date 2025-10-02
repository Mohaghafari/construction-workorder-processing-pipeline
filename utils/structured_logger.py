"""
Structured logging utilities for the pipeline
Provides correlation IDs, contextual logging, and proper error handling
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import functools

# Global correlation ID for tracking requests through the pipeline
_correlation_id = None

def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracking a pipeline run"""
    return str(uuid.uuid4())

def set_correlation_id(correlation_id: str):
    """Set the correlation ID for this pipeline run"""
    global _correlation_id
    _correlation_id = correlation_id

def get_correlation_id() -> str:
    """Get the current correlation ID"""
    global _correlation_id
    if _correlation_id is None:
        _correlation_id = generate_correlation_id()
    return _correlation_id

class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs
    Includes correlation IDs, timestamps, and contextual information
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Set up JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal log method with structured data"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'logger': self.name,
            'correlation_id': get_correlation_id(),
            'message': message,
            **kwargs
        }
        
        if level == 'INFO':
            self.logger.info(json.dumps(log_data))
        elif level == 'WARNING':
            self.logger.warning(json.dumps(log_data))
        elif level == 'ERROR':
            self.logger.error(json.dumps(log_data))
        elif level == 'DEBUG':
            self.logger.debug(json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self._log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self._log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self._log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self._log('DEBUG', message, **kwargs)

class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON"""
    
    def format(self, record):
        try:
            # Try to parse as JSON first (already structured)
            return record.getMessage()
        except:
            # Fallback to standard formatting
            return super().format(record)

def log_execution_time(func):
    """
    Decorator to log function execution time
    
    Usage:
        @log_execution_time
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = StructuredLogger(func.__module__)
        start_time = datetime.utcnow()
        
        logger.info(
            f"Starting {func.__name__}",
            function=func.__name__,
            event='function_start'
        )
        
        try:
            result = func(*args, **kwargs)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Completed {func.__name__}",
                function=func.__name__,
                event='function_complete',
                duration_seconds=duration,
                success=True
            )
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(
                f"Failed {func.__name__}: {str(e)}",
                function=func.__name__,
                event='function_error',
                duration_seconds=duration,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
    
    return wrapper

class PipelineContext:
    """
    Context manager for pipeline runs
    Tracks correlation ID, stage, and metrics
    """
    
    def __init__(self, pipeline_name: str, stage: str):
        self.pipeline_name = pipeline_name
        self.stage = stage
        self.correlation_id = generate_correlation_id()
        self.logger = StructuredLogger(pipeline_name)
        self.start_time = None
        self.metrics = {}
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        set_correlation_id(self.correlation_id)
        
        self.logger.info(
            f"Starting pipeline stage: {self.stage}",
            pipeline=self.pipeline_name,
            stage=self.stage,
            event='stage_start'
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(
                f"Completed pipeline stage: {self.stage}",
                pipeline=self.pipeline_name,
                stage=self.stage,
                event='stage_complete',
                duration_seconds=duration,
                success=True,
                **self.metrics
            )
        else:
            self.logger.error(
                f"Failed pipeline stage: {self.stage}",
                pipeline=self.pipeline_name,
                stage=self.stage,
                event='stage_error',
                duration_seconds=duration,
                success=False,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.metrics
            )
        
        return False  # Don't suppress exceptions
    
    def add_metric(self, key: str, value: Any):
        """Add a metric to track for this stage"""
        self.metrics[key] = value
    
    def log_progress(self, message: str, **kwargs):
        """Log progress within a stage"""
        self.logger.info(
            message,
            pipeline=self.pipeline_name,
            stage=self.stage,
            event='progress',
            **kwargs
        )

# Example usage:
"""
from utils.structured_logger import StructuredLogger, PipelineContext, log_execution_time

# Method 1: Direct logger
logger = StructuredLogger(__name__)
logger.info("Processing PDF", pdf_file="test.pdf", size_mb=2.5)

# Method 2: Context manager
with PipelineContext("work_order_pipeline", "ocr_extraction") as ctx:
    ctx.log_progress("Processing PDF 1/10", current=1, total=10)
    result = extract_pdf()
    ctx.add_metric("pdfs_processed", 10)
    ctx.add_metric("success_rate", 0.93)

# Method 3: Decorator
@log_execution_time
def process_pdf(pdf_path):
    # Function is automatically logged with timing
    return extract_data(pdf_path)
"""

