import logging, os, re
from pathlib import Path

from openai import AsyncOpenAI

from src.models import AnalysisContent, NewsArticle, SpikeNewsResponse
from src.utils import DATA_DIR

logger = logging.getLogger(__name__)

NEWS_CACHE_DIR = DATA_DIR / "news"

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not api_key:
            raise ValueError("PERPLEXITY_API_KEY not set.")
        _client = AsyncOpenAI(base_url="https://api.perplexity.ai", api_key=api_key)
    return _client


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
            content="You are a commodity market analyst. Respond in plain text only. No markdown formatting. No citation markers like [1][2]. Never mention specific dates. Keep it extremely short and concise.",
        ),
        dict(
            role="user",
            content=f"""
What were the key developments in {category} around {date} and the previous and following days?
Analyze supply/demand shifts, geopolitical events, production decisions, weather impacts, macro trends, and anything else that might be of relevance and consider the broader context.
Then explain how these factors have led to {performance} during this period.
""".strip(),
        ),
    ]


async def fetch_spike_news(pair: str, date: str, direction: str, pair_config: dict) -> SpikeNewsResponse:
    cached = _load_cache(pair, date)
    if cached is not None:
        return cached

    try:
        client = _get_client()
        completion = await client.beta.chat.completions.parse(
            model="sonar",
            messages=_build_messages(pair_config, date, direction),
            response_format=AnalysisContent,
        )

        analysis = completion.choices[0].message.parsed
        single_exact_reason = _strip_citations(analysis.single_exact_reason)
        detailed_summary = _strip_citations(analysis.detailed_summary)

        articles = []
        search_results = getattr(completion, "model_extra", {}).get("search_results", [])
        logger.info("model_extra keys: %s", list(getattr(completion, "model_extra", {}).keys()))
        for result in search_results:
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
            single_exact_reason=single_exact_reason,
            detailed_summary=detailed_summary,
            articles=articles,
        )
        _save_cache(response)
        return response

    except ValueError:
        raise
    except Exception as exc:
        logger.exception("Perplexity API error for %s/%s", pair, date)
        return SpikeNewsResponse(
            pair=pair,
            date=date,
            direction=direction,
            single_exact_reason="Failed to fetch news analysis",
            detailed_summary=str(exc),
        )
