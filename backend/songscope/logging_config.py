# Add to a new file: songscope/logging_config.py

import logging

# Configure logger
logger = logging.getLogger('songscope')
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create custom filters to reduce noise
class SpotifyAPIFilter(logging.Filter):
    def filter(self, record):
        # Filter out verbose track data logs
        return 'spotify:track' not in str(record.msg)

logger.addFilter(SpotifyAPIFilter())

# Add descriptive logging methods
def log_api_error(error, context=None):
    """Log API errors with context"""
    if context:
        logger.error(f"API Error in {context}: {str(error)}")
    else:
        logger.error(f"API Error: {str(error)}")

def log_spotify_error(error, endpoint=None):
    """Log Spotify-specific errors"""
    if hasattr(error, 'http_status'):
        logger.error(f"Spotify API Error ({error.http_status}) at {endpoint}: {str(error)}")
    else:
        logger.error(f"Spotify Error at {endpoint}: {str(error)}")