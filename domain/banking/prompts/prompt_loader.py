import os
from functools import lru_cache

PROMPTS_DIR = os.path.dirname(__file__)

@lru_cache(maxsize=32)
def load_prompt(filename: str) -> str:
    """Loads and caches a prompt template from an .md file."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()
