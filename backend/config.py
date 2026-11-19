"""Application configuration sourced from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base configuration for the Flask application."""

    APP_ENV = os.getenv('APP_ENV', 'development').lower()
    IS_PRODUCTION = APP_ENV == 'production' or os.getenv('VERCEL') == '1'
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
    GEMINI_REQUEST_TIMEOUT_MS = 15_000
    GEMINI_RETRY_ATTEMPTS = 2
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY')
    # Local development remains convenient, while deployed instances must
    # explicitly declare their permitted frontend origin.
    FRONTEND_URL = os.getenv('FRONTEND_URL') or (None if IS_PRODUCTION else 'http://localhost:5173')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    JSON_SORT_KEYS = False
