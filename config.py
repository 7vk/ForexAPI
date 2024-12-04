import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Application configuration class
    
    Contains all configuration variables for the application,
    loaded from environment variables with fallback defaults
    """
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///exchange_rates.db'
    )
    
    # API Configuration
    SUPPORTED_CURRENCIES = [
        'GBP',  # British Pound
        'AED',  # UAE Dirham
        'INR'   # Indian Rupee
    ]
    
    SUPPORTED_PERIODS = [
        '1W',   # 1 Week
        '1M',   # 1 Month
        '3M',   # 3 Months
        '6M',   # 6 Months
        '1Y'    # 1 Year
    ]
    
    # Scraper Configuration
    MAX_WORKERS = 2          # Maximum number of concurrent workers
    REQUEST_TIMEOUT = 30     # Request timeout in seconds
    MAX_RETRIES = 3         # Maximum number of retry attempts