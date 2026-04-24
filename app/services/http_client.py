import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
async def fetch_text(url: str, timeout_s: float = 20.0) -> str:
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
