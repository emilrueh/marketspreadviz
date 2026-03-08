import json, logging, os, re
from pathlib import Path

import httpx

from src.models import NewsArticle, SpikeNewsResponse
from src.utils import DATA_DIR

logger = logging.getLogger(__name__)

NEWS_CACHE_DIR = DATA_DIR / "news"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def _strip_citations(text: str) -> str:
    return re.sub(r"\[\d+\]", "", text).strip()


def _cache_path(pair: str, date: str) -> Path:
    return NEWS_CACHE_DIR / f"{pair}_{date}.json"


def _load_cache(pair: str, date: str) -> SpikeNewsResponse | None:
    path = _cache_path(pair, date)
    if path.exists():
        return SpikeNewsResponse.model_validate_json(path.read_text())
    return None


def _save_cache(response: SpikeNewsResponse) -> None:
    NEWS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(response.pair, response.date)
    path.write_text(response.model_dump_json(indent=2))


def _build_messages(pair_config: dict, date: str, direction: str) -> list[dict]:
    label = pair_config["label"]
    category = pair_config["category"]
    name_a, name_b = label.split(" / ")

    if direction == "up":
        performance = f"{name_a} outperforming {name_b}"
    else:
        performance = f"{name_b} outperforming {name_a}"

    return [
        dict(
            role="system",
            content=("You are a commodity market analyst. " "Respond in plain text only. No markdown formatting. No citation markers like [1][2]."),
        ),
        dict(
            role="user",
            content=(
                f"What were the key developments in {category} around {date}? "
                f"Consider supply/demand shifts, geopolitical events, production decisions, "
                f"weather impacts, and macro trends. "
                f"Then explain how these factors would have led to {performance} during this period."
            ),
        ),
    ]



async def fetch_spike_news(pair: str, date: str, direction: str, pair_config: dict) -> SpikeNewsResponse:
    cached = _load_cache(pair, date)
    if cached is not None:
        return cached

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not set. Add it to your .env file.")

    payload = dict(
        model="sonar",
        messages=_build_messages(pair_config, date, direction),
        max_tokens=400,
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        logger.info("Perplexity response keys: %s", list(data.keys()))
        if "search_results" in data:
            logger.info("search_results count: %d", len(data["search_results"]))
        else:
            logger.info("No search_results in response")
        if "citations" in data:
            logger.info("citations count: %d", len(data["citations"]))

        content = data["choices"][0]["message"]["content"]
        logger.info("Raw content: %s", content[:500])
        try:
            parsed = json.loads(content)
            summary = _strip_citations(parsed["summary"])
            detail = _strip_citations(parsed["detail"])
        except (json.JSONDecodeError, KeyError):
            logger.warning("JSON parse failed, extracting from raw text")
            summary = _strip_citations(content[:200])
            detail = _strip_citations(content)

        articles = []
        for result in data.get("search_results", []):
            articles.append(
                NewsArticle(
                    title=result.get("title", result.get("url", "")),
                    url=result.get("url", ""),
                    snippet=result.get("snippet", ""),
                    date=result.get("date", ""),
                )
            )

        response = SpikeNewsResponse(
            pair=pair,
            date=date,
            direction=direction,
            summary=summary,
            detail=detail,
            articles=articles,
        )
        _save_cache(response)
        return response

    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        logger.exception("Perplexity API error for %s/%s", pair, date)
        return SpikeNewsResponse(
            pair=pair,
            date=date,
            direction=direction,
            summary="Failed to fetch news analysis",
            detail=str(exc),
        )
