import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DOCUMENTS_FILE = DATA_DIR / "documents.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Load environment variables
load_dotenv(BASE_DIR / ".env")

class Settings:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.default_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        self._load_saved_settings()

    def _load_saved_settings(self):
        """Loads runtime settings saved via Admin UI if available"""
        if SETTINGS_FILE.exists():
            try:
                import json
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if saved.get("api_key"):
                        self.api_key = saved["api_key"]
                    if saved.get("default_model"):
                        self.default_model = saved["default_model"]
            except Exception:
                pass

    def save_settings(self, api_key: str, default_model: str = "gemini-flash-latest"):
        """Persists settings saved via Admin UI"""
        import json
        self.api_key = api_key.strip()
        self.default_model = default_model.strip()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "api_key": self.api_key,
                "default_model": self.default_model
            }, f, indent=2)

settings = Settings()
