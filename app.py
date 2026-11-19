"""Vercel WSGI entry point for the Flask application."""

import importlib.util
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

spec = importlib.util.spec_from_file_location('college_notice_backend', BACKEND_DIR / 'app.py')
if spec is None or spec.loader is None:
    raise RuntimeError('Unable to load the Flask application.')
backend_app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = backend_app
spec.loader.exec_module(backend_app)
app = backend_app.app
