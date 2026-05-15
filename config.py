import os
from dotenv import load_dotenv
 
load_dotenv()
 
 
class Config:
    # CAPTCHA
    CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY", "")
 
    # Postal (self-hosted email server)
    POSTAL_URL = os.getenv("POSTAL_URL", "https://postal.botwave.online")
    POSTAL_API_KEY = os.getenv("POSTAL_API_KEY", "")
 
    # Email (IMAP fallback)
    EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
    EMAIL_IMAP_PORT = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
 
    # Proxy
    PROXY_URL = os.getenv("PROXY_URL", "")
    ROTATING_PROXY_URL = os.getenv("ROTATING_PROXY_URL", "")
 
    # Account defaults
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "TikT0k_Auto!2024")
    BIRTH_YEAR = int(os.getenv("BIRTH_YEAR", "1998"))
    BIRTH_MONTH = int(os.getenv("BIRTH_MONTH", "6"))
    BIRTH_DAY = int(os.getenv("BIRTH_DAY", "15"))
 
    # TikTok
    SIGNUP_URL = "https://www.tiktok.com/signup/phone-or-email/email"
 
    # Timing
    ACTION_DELAY = 1.5  # seconds between actions (human-like)
    PAGE_LOAD_TIMEOUT = 30000  # ms
    CAPTCHA_SOLVE_TIMEOUT = 120  # seconds
 
    # Output
    ACCOUNTS_FILE = "accounts.csv"
