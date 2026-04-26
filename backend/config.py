from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

AGENTMAIL_API_KEY = os.getenv("AGENTMAIL_API_KEY", "")
NIA_API_KEY = os.getenv("NIA_API_KEY", "")
NIA_API_URL = os.getenv("NIA_API_URL", "https://apigcp.trynia.ai")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hackmatch.db")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
AGENT_DOMAIN = os.getenv("AGENT_DOMAIN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
