import json
import os
from typing import Dict, Any

def ensure_config_files():
    """Ensure config.json and models.json exist, create defaults if missing"""
    # Default configurations
    DIRS = {
        'models': "models",
        'speakers': "speakers",
        'output': "output",
        'binaries': "binaries"
    }

    DEFAULT_CONFIG = {
  "model_id": 0,
  "workers_count": 1,
  "server_ip": "0.0.0.0",
  "server_port": 8080,
  "default_speaker": "pricelius_v2"
}

    DEFAULT_MODELS = [
  {
    "name": "xtts-v2",
    "path": "models/tts_models--multilingual--multi-dataset--xtts_v2",
    "config": "models/tts_models--multilingual--multi-dataset--xtts_v2/config.json"
  },
  {
    "name": "xtts-v2-banana",
    "path": "models/model_banana/v2.0.2",
    "config": "models/model_banana/v2.0.2/config.json"
  }
]
    #check and create dirs
    for name, path in DIRS.items():
        os.makedirs(path, exist_ok=True)
        print(f"Ensured directory exists: {path}")

    # Check and create config.json
    if not os.path.exists("config.json"):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print("Created default config.json")

    # Check and create models.json
    if not os.path.exists("models.json"):
        with open("models.json", "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MODELS, f, indent=4)
        print("Created default models.json")

def load_config() -> Dict[str, Any]:
    """Load configuration with fallback to defaults"""
    ensure_config_files()
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_models_config() -> Dict[str, Any]:
    """Load models configuration with fallback to defaults"""
    ensure_config_files()
    with open("models.json", "r", encoding="utf-8") as f:
        return json.load(f)