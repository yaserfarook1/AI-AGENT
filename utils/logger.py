import logging
import logging.handlers
import os
import sys

def setup_logger(name, log_file, max_bytes=5*1024*1024, backup_count=5):
    """
    Set up a logger with rotation.
    
    Args:
        name (str): Logger name
        log_file (str): Path to log file
        max_bytes (int): Maximum size of log file before rotation (default: 5MB)
        backup_count (int): Number of backup files to keep (default: 5)
    
    Returns:
        logging.Logger: Configured logger
    """
    # Ensure logs directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Stream handler for terminal output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.handlers = [file_handler, stream_handler]

    return logger