"""Top-level verification: run parsed citations through Crossref + OpenAlex."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

import httpx

from hallucitation import crossref, openalex
from hallucitation.parse import Citation
from hallucitation.score import aggregate


Verdict = Literal["verified", "partial_match", "mangled", "hallucinated"]


@dataclass
class VerificationResult:
    citation: Citation
    verdict: Verdict = "hallucinated"
    confidence: float = 0.0
    crossref_match: dict[str, Any] | None = None
    openalex_match: dict[str, Any] | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["citation"] = self.citation.to_dict()
        return d

    @property
    def is_hallucinated(self) -> bool:
        return self.verdict == "hallucinated"


class RateLimiter:
    """Simple token-bucket style limiter: at most ``rate`` calls per second."""

    def __init__(self, rate: float) -> None:
        self._interval = 1.0 / rate if rate > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next_time = 0.0

    async def acquire(self) -> None:
        if self._interval <= 0:
            return
        async with self._lock:
            loop = asyncio.get_event_loop()
            now = loop.time()
            wait = self._next_time - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = loop.time()
            self._next_time = max(now, self._next_time) + self._interval


async def _with_retry(coro_factory, max_tries: int = 3) -> Any:
    delay = 0.5
    for attempt in range(max_tries):
        try:
            return await coro_factory()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and attempt < max_tries - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            return None
        except httpx.HTTPError:
            if attempt < max_tries - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            return None
    return None


async def verify_one(
    client: httpx.AsyncClient,
    citation: Citation,
    cr_limiter: RateLimiter,
    oa_limiter: RateLimiter,
) -> VerificationResult:
    async def _cr():
        await cr_limiter.acquire()
        return await crossref.find(client, citation)

    async def _oa():
        await oa_limiter.acquire()
        return await openalex.find(client, citation)

    cr_match, oa_match = await asyncio.gather(
        _with_retry(_cr), _with_retry(_oa), return_exceptions=False
    )

    verdict, confidence, notes = aggregate(citation, cr_match, oa_match)
    return VerificationResult(
        citation=citation,
        verdict=verdict,  # type: ignore[arg-type]
        confidence=confidence,
        crossref_match=cr_match,
        openalex_match=oa_match,
        notes=notes,
    )


async def verify_citations(
    citations: list[Citation],
    *,
    rate: float = 5.0,
    client: httpx.AsyncClient | None = None,
) -> list[VerificationResult]:
    cr_limiter = RateLimiter(rate)
    oa_limiter = RateLimiter(rate)

    close_client = False
    if client is None:
        client = httpx.AsyncClient(follow_redirects=True)
        close_client = True
    try:
        tasks = [verify_one(client, c, cr_limiter, oa_limiter) for c in citations]
        return await asyncio.gather(*tasks)
    finally:
        if close_client:
            await client.aclose()


def verify_citations_sync(
    citations: list[Citation], *, rate: float = 5.0
) -> list[VerificationResult]:
    return asyncio.run(verify_citations(citations, rate=rate))
