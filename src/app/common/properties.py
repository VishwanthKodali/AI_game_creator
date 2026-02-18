import os
import yaml

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yml")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = config.get("GROQ_BASE_URL")
GROQ_MODEL_FAST = config.get("GROQ_MODEL_FAST")
GROQ_MODEL_POWER = config.get("GROQ_MODEL_POWER")
BACKEND_URL = config.get("BACKEND_URL")
OUTPUT_DIR = config.get("OUTPUT_DIR", "output")