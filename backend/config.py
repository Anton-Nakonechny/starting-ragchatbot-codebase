import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv


def load_environment() -> None:
    """Load config from .env and secrets from .env.key (searching up dirs).

    Secrets (ANTHROPIC_API_KEY) live in a separate ``.env.key`` file, kept out
    of ``.env``. ``load_dotenv()`` alone only reads ``.env``, so the key file
    must be loaded explicitly or the API key resolves to "" and every query
    500s. ``find_dotenv(usecwd=True)`` walks up from the cwd (the server runs
    from ``backend/``) to the repo root, matching how ``.env`` is found.
    """
    load_dotenv(find_dotenv(usecwd=True))              # .env (PORT, ...)
    load_dotenv(find_dotenv(".env.key", usecwd=True))  # secrets (ANTHROPIC_API_KEY)


# Load environment variables before the dataclass defaults read os.getenv.
load_environment()

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    
    # Embedding model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Document processing settings
    CHUNK_SIZE: int = 800       # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100     # Characters to overlap between chunks
    MAX_RESULTS: int = 5         # Maximum search results to return
    MAX_HISTORY: int = 2         # Number of conversation messages to remember
    
    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

    # Server settings — .env (PORT), also sourced by run.sh, drives the runtime
    # value; the 8000 here is a fallback when PORT is unset (fresh clone / CI).
    PORT: int = int(os.getenv("PORT", "8000"))

config = Config()


