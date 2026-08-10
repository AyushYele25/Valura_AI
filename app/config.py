import os
from pydantic import BaseModel

class Settings(BaseModel):
    BOOK_PATH: str = os.getenv("BOOK_PATH", "client_book.json")
    MARKET_PATH: str = os.getenv("MARKET_PATH", "market_data.json")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://ai-arena.twocc.in/llm/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "vlr_V7pE04PXx7FLI_yDGQZ66AKM3Jdvfwi9")
    PORT: int = int(os.getenv("PORT", "8080"))

settings = Settings()
