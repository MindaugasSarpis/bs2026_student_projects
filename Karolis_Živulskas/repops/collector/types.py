"""Shared data types for the collection layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ScrapedPost:
    facebook_id: str
    page_id: str
    author_facebook_id: str | None
    content: str
    url: str
    post_type: str  # post | comment
    posted_at: datetime | None
    reaction_count: int = 0
    share_count: int = 0
    comment_count: int = 0
    author_name: str | None = None
    screenshot_bytes: bytes | None = field(default=None, repr=False)
