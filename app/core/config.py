"""K-FLEET SECURE configuration.

Reads secrets from environment variables.
For local development, create a .env file in the project root.
For production (Render), set these in the service's Environment settings.
"""
import os
from dotenv import load_dotenv

# Load .env file if present (local development only)
load_dotenv()

# --- Traccar GPS integration ---
TRACCAR_URL = os.getenv("TRACCAR_URL", "http://localhost:8082")
TRACCAR_TOKEN = os.getenv("TRACCAR_TOKEN", "")
TRACCAR_POLL_SECONDS = int(os.getenv("TRACCAR_POLL_SECONDS", "60"))

# --- Application ---
APP_NAME = "K-FLEET SECURE"