# api/index.py
# Serverless handler for Vercel deployment of TradeCraft FastAPI Backend
import os
import sys

# Ensure backend directory is in the Python module search path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set current working directory to backend so relative file imports/config work
try:
    os.chdir(backend_dir)
except Exception as e:
    print(f"[Vercel Handler] Warning: could not chdir to {backend_dir}: {e}")

from main import app
