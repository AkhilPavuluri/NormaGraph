"""
Enhanced logging configuration for ingestion_v2 pipeline.

Provides clear, structured logging with progress indicators and detailed step information.
"""
import logging
import sys
from pathlib import Path
from typing import Optional


class PipelineFormatter(logging.Formatter):
    """Custom formatter for pipeline logs with clear structure."""
    
    # Color codes for terminal (if supported)
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    # Stage emojis and indicators
    STAGE_MARKERS = {
        'STAGE_START': '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
        'STAGE_END': '────────────────────────────────────────────────────────────────────────────────',
        'SUBSECTION': '  ├─',
        'SUBSECTION_END': '  └─',
        'PROGRESS': '  │',
    }
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize formatter.
        
        Args:
            use_colors: Whether to use color codes (only if terminal supports it)
        """
        self.use_colors = use_colors and sys.stdout.isatty()
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with enhanced structure."""
        # Get base format
        if self.use_colors and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            reset = self.COLORS['RESET']
        else:
            color = reset = ''
        
        # Format timestamp
        timestamp = self.formatTime(record, '%H:%M:%S')
        
        # Format message with appropriate prefix
        message = record.getMessage()
        
        # Add stage markers for special messages
        if message.startswith('STAGE:'):
            # Stage header
            stage_name = message.replace('STAGE:', '').strip()
            formatted = f"\n{self.STAGE_MARKERS['STAGE_START']}\n"
            formatted += f"  {color}▶ {stage_name}{reset}\n"
            formatted += f"{self.STAGE_MARKERS['STAGE_START']}"
        elif message.startswith('STEP:'):
            # Sub-step
            step_name = message.replace('STEP:', '').strip()
            formatted = f"  {self.STAGE_MARKERS['SUBSECTION']} {color}{step_name}{reset}"
        elif message.startswith('METRIC:'):
            # Metric/statistic
            metric = message.replace('METRIC:', '').strip()
            formatted = f"  {self.STAGE_MARKERS['PROGRESS']}   {color}•{reset} {metric}"
        elif message.startswith('SUCCESS:'):
            # Success message
            success_msg = message.replace('SUCCESS:', '').strip()
            formatted = f"  {self.STAGE_MARKERS['SUBSECTION_END']} {color}✓{reset} {success_msg}"
        elif message.startswith('WARNING:'):
            # Warning message
            warn_msg = message.replace('WARNING:', '').strip()
            formatted = f"  {self.STAGE_MARKERS['PROGRESS']}   {color}⚠{reset} {warn_msg}"
        elif message.startswith('ERROR:'):
            # Error message
            error_msg = message.replace('ERROR:', '').strip()
            formatted = f"  {self.STAGE_MARKERS['PROGRESS']}   {color}✗{reset} {error_msg}"
        else:
            # Regular message
            level_name = f"{color}{record.levelname:8s}{reset}"
            formatted = f"[{timestamp}] {level_name} {message}"
        
        return formatted


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Setup enhanced logging for the pipeline.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
        use_colors: Whether to use colors in console output
        
    Returns:
        Configured logger
    """
    # Create formatter
    formatter = PipelineFormatter(use_colors=use_colors)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


class StageLogger:
    """Helper class for logging pipeline stages with timing and metrics."""
    
    def __init__(self, logger: logging.Logger, stage_name: str):
        """
        Initialize stage logger.
        
        Args:
            logger: Base logger
            stage_name: Name of the stage
        """
        self.logger = logger
        self.stage_name = stage_name
        self.start_time = None
        self.metrics = {}
    
    def __enter__(self):
        """Enter stage context."""
        import time
        self.start_time = time.time()
        self.logger.info(f"STAGE: {self.stage_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit stage context."""
        import time
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.logger.info(f"METRIC: Stage '{self.stage_name}' completed in {elapsed:.2f}s")
    
    def step(self, step_name: str):
        """Log a sub-step."""
        self.logger.info(f"STEP: {step_name}")
    
    def metric(self, name: str, value):
        """Log a metric."""
        self.metrics[name] = value
        if isinstance(value, (int, float)):
            self.logger.info(f"METRIC: {name}: {value}")
        else:
            self.logger.info(f"METRIC: {name}: {value}")
    
    def success(self, message: str):
        """Log a success message."""
        self.logger.info(f"SUCCESS: {message}")
    
    def warning(self, message: str):
        """Log a warning."""
        self.logger.warning(f"WARNING: {message}")
    
    def error(self, message: str):
        """Log an error."""
        self.logger.error(f"ERROR: {message}")

