import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.rstrip('/')
        self.api_key = settings.LLM_API_KEY

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "valura-fast",
        temperature: float = 0.0,
        max_tokens: int = 1000,
        max_retries: int = 4
    ) -> Optional[str]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, json=payload, headers=headers)

                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                        return ""

                    elif response.status_code == 429:
                        # Check Retry-After header or quota blackout
                        body = response.text.lower()
                        if "quota" in body or "exhausted" in body or "blackout" in body:
                            logger.warning(f"Blackout band detected: {body}")
                            return None  # Quota exhausted blackout: retry won't succeed

                        retry_after = response.headers.get("Retry-After")
                        wait_seconds = float(retry_after) if retry_after else (2.0 ** attempt)
                        logger.info(f"Rate limited (429). Retrying in {wait_seconds}s (attempt {attempt+1}/{max_retries})...")
                        await asyncio.sleep(wait_seconds)

                    else:
                        logger.error(f"LLM API error {response.status_code}: {response.text}")
                        await asyncio.sleep(1.0 * (attempt + 1))

                except Exception as e:
                    logger.error(f"HTTP exception during LLM call: {e}")
                    await asyncio.sleep(1.0 * (attempt + 1))

        return None

llm_client = LLMClient()
