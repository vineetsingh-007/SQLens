import sys
import os
from pathlib import Path

# Add project root and backend directory to sys.path for seamless Vercel / serverless routing
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from app.main import app
except ImportError:
    from backend.app.main import app  # type: ignore
