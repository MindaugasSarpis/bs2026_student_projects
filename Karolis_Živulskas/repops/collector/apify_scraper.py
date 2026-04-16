"""Apify-backed Facebook scraper.

Two-actor workflow per collection run:
  1. apify/facebook-posts-scraper  → discover N recent post URLs from the target page
  2. apify/facebook-comments-scraper → fetch comments for all those posts in one call

Both actors' outputs are mapped to ScrapedPost and returned to the existing pipeline.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import httpx

from repops.collector.rate_limiter import facebook_scrape_limiter
from repops.collector.types import ScrapedPost
from repops.observability.logging import get_logger
from repops.settings import settings

logger = get_logger(__name__)

_APIFY_BASE = "https://api.apify.com/v2"
_POSTS_ACTOR = "KoJrdxJCTtpon81KY"    # apify/facebook-posts-scraper
_COMMENTS_ACTOR = "us5srxAYnsrkgUv2v"  # apify/facebook-comments-scraper


class ApifyScraper:
    """Facebook scraper backed by Apify actors. Same interface as FacebookScraper."""

    async def __aenter__(self) -> "ApifyScraper":
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {settings.apify_token}"},
            timeout=60.0,
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def _start_run(self, actor_id: str, input_data: dict) -> tuple[str, str]:
        """Start an actor run. Returns (run_id, dataset_id)."""
        resp = await self._client.post(
            f"{_APIFY_BASE}/acts/{actor_id}/runs",
            json=input_data,
            params={"memory": 2048},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return data["id"], data["defaultDatasetId"]

    async def _wait_for_run(self, run_id: str, timeout_secs: int = 300) -> None:
        """Poll until the run succeeds or fails."""
        deadline = asyncio.get_event_loop().time() + timeout_secs
        while True:
            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError(f"Apify run {run_id} timed out after {timeout_secs}s")
            resp = await self._client.get(f"{_APIFY_BASE}/actor-runs/{run_id}")
            resp.raise_for_status()
            status = resp.json()["data"]["status"]
            if status == "SUCCEEDED":
                return
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Apify run {run_id} ended with status: {status}")
            await asyncio.sleep(5)

    async def _get_items(self, dataset_id: str) -> list[dict]:  # type: ignore[type-arg]
        resp = await self._client.get(
            f"{_APIFY_BASE}/datasets/{dataset_id}/items",
            params={"format": "json", "clean": "true"},
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def _run_actor(
        self, actor_id: str, input_data: dict, timeout_secs: int = 300  # type: ignore[type-arg]
    ) -> list[dict]:  # type: ignore[type-arg]
        run_id, dataset_id = await self._start_run(actor_id, input_data)
        logger.info("apify_run_started", actor=actor_id, run_id=run_id)
        await self._wait_for_run(run_id, timeout_secs)
        items = await self._get_items(dataset_id)
        logger.info("apify_run_done", actor=actor_id, run_id=run_id, items=len(items))
        return items

    async def scrape_page(self, page_id: str, max_posts: int = 10) -> list[ScrapedPost]:
        """Scrape recent posts + comments via Apify. Returns list[ScrapedPost]."""
        await facebook_scrape_limiter.acquire()

        fb_url = f"https://www.facebook.com/{page_id}"
        results: list[ScrapedPost] = []

        # Step 1: get recent posts
        try:
            post_items = await self._run_actor(
                _POSTS_ACTOR,
                {
                    "startUrls": [{"url": fb_url}],
                    "maxPosts": max_posts,
                },
            )
        except Exception as exc:
            logger.error("apify_posts_error", page_id=page_id, error=str(exc))
            return []

        post_urls: list[str] = []
        for item in post_items:
            # topLevelUrl is the canonical /posts/<id> form; fall back to url
            post_url = item.get("topLevelUrl") or item.get("url") or ""
            if not post_url:
                continue
            post_urls.append(post_url)

            fb_id = str(item.get("postId") or post_url.rstrip("/").split("/")[-1])
            text = (item.get("text") or "").strip()
            results.append(ScrapedPost(
                facebook_id=fb_id,
                page_id=page_id,
                author_facebook_id=None,
                content=text,
                url=post_url,
                post_type="post",
                posted_at=_parse_dt(item.get("time")),
                reaction_count=int(item.get("likes") or 0),
                share_count=int(item.get("shares") or 0),
                comment_count=int(item.get("comments") or 0),
            ))

        logger.info("apify_posts_found", page_id=page_id, count=len(post_urls))

        if not post_urls:
            return results

        # Step 2: get comments for all posts in one call
        try:
            comment_items = await self._run_actor(
                _COMMENTS_ACTOR,
                {
                    "startUrls": [{"url": u} for u in post_urls],
                    "maxComments": 200,
                },
                timeout_secs=600,
            )
        except Exception as exc:
            logger.error("apify_comments_error", page_id=page_id, error=str(exc))
            return results  # return posts even if comments fail

        logger.info("apify_comments_found", page_id=page_id, count=len(comment_items))

        for item in comment_items:
            text = (item.get("text") or "").strip()
            if not text:
                continue

            post_url = item.get("facebookUrl") or item.get("inputUrl") or ""
            comment_id = str(item.get("commentId") or item.get("id") or "")
            if not comment_id:
                continue

            # Author: prefer profileId, fall back to last path segment of profileUrl
            author_id: str | None = str(item["profileId"]) if item.get("profileId") else None
            if not author_id:
                profile_url = item.get("profileUrl") or ""
                seg = profile_url.rstrip("/").split("/")[-1]
                author_id = seg if seg and seg != "profile.php" else None

            author_name: str | None = item.get("profileName") or None
            results.append(ScrapedPost(
                facebook_id=comment_id,
                page_id=page_id,
                author_facebook_id=author_id,
                author_name=author_name,
                content=text,
                url=post_url,
                post_type="comment",
                posted_at=_parse_dt(item.get("date")),
            ))

        return results


def _parse_dt(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
