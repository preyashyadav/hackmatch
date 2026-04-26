import logging

import httpx

import config


logger = logging.getLogger(__name__)

BASE_URL = config.NIA_API_URL.rstrip("/")
HEADERS = {
    "Authorization": f"Bearer {config.NIA_API_KEY}",
    "Content-Type": "application/json",
}


def _normalize_result(item: dict) -> dict:
    source_value = item.get("source", "")
    if isinstance(source_value, dict):
        source_value = (
            source_value.get("display_name")
            or source_value.get("identifier")
            or source_value.get("url")
            or source_value.get("id")
            or ""
        )

    snippet = (
        item.get("snippet")
        or item.get("text")
        or item.get("content")
        or item.get("chunk_text")
        or item.get("body")
        or ""
    )

    return {
        "snippet": str(snippet).strip(),
        "source": str(source_value).strip(),
        "score": item.get("score"),
    }


def _extract_results(payload: dict) -> list[dict]:
    candidates = payload.get("results")
    if not isinstance(candidates, list):
        candidates = payload.get("sources")
    if not isinstance(candidates, list):
        answer = payload.get("answer")
        if isinstance(answer, dict):
            candidates = answer.get("sources")
    if not isinstance(candidates, list):
        candidates = payload.get("items")
    if not isinstance(candidates, list):
        candidates = []

    return [_normalize_result(item) for item in candidates if isinstance(item, dict)]


async def index_text(text: str, name: str) -> str:
    if not config.NIA_API_KEY:
        raise RuntimeError("NIA_API_KEY is not configured.")

    payload = {
        "type": "local_folder",
        "folder_name": name,
        "display_name": name,
        "files": [
            {
                "path": f"{name}.txt",
                "content": text,
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/v2/sources",
            headers=HEADERS,
            json=payload,
        )
        response.raise_for_status()
        response_json = response.json()

    source_id = response_json.get("id")
    if not source_id:
        raise ValueError("Nia text indexing response missing source id.")
    return str(source_id)


async def index_url(url: str, name: str | None = None) -> str:
    if not config.NIA_API_KEY:
        raise RuntimeError("NIA_API_KEY is not configured.")

    payload = {
        "type": "documentation",
        "url": url,
        "display_name": name or url,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/v2/sources",
            headers=HEADERS,
            json=payload,
        )
        response.raise_for_status()
        response_json = response.json()

    source_id = response_json.get("id")
    if not source_id:
        raise ValueError("Nia URL indexing response missing source id.")
    return str(source_id)


async def search(query: str, source_ids: list[str], limit: int = 5) -> list[dict]:
    if not config.NIA_API_KEY or not source_ids:
        return []

    base_payload = {
        "messages": [{"role": "user", "content": query}],
        "search_mode": "unified",
        "stream": False,
        "include_sources": True,
        "fast_mode": True,
        "skip_llm": True,
        "reasoning_strategy": "vector",
        "mode": "query",
    }

    payloads = [
        {
            **base_payload,
            "data_sources": source_ids,
            "local_folders": source_ids,
        },
        {
            **base_payload,
            "data_sources": source_ids,
        },
        {
            **base_payload,
            "local_folders": source_ids,
        },
    ]

    for payload in payloads:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{BASE_URL}/v2/search",
                    headers=HEADERS,
                    json=payload,
                )
                response.raise_for_status()
                response_json = response.json()
            return _extract_results(response_json)[:limit]
        except Exception as exc:
            logger.warning("Nia search attempt failed; trying fallback payload. %s", exc)

    return []
