"""Endpoints for browsing and reviewing analysis results."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from repops.api.dependencies import get_db
from repops.models import AnalysisLabel, AnalysisResult, Post, PostStatus

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


class AnalysisResultResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    post_facebook_id: str
    post_url: str
    matched_keywords: list[str]
    keyword_severity: int
    overall_label: str
    overall_score: float
    reviewer_notes: str | None
    reviewed_by: str | None

    model_config = {"from_attributes": True}


class ReviewBody(BaseModel):
    notes: str
    reviewer: str
    clear: bool = False  # if True, mark post as CLEARED (false positive)


@router.get("/", response_model=list[AnalysisResultResponse])
def list_results(
    db: DB,
    label: AnalysisLabel | None = None,
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> list[dict]:  # type: ignore[type-arg]
    q = (
        select(AnalysisResult, Post)
        .join(Post, Post.id == AnalysisResult.post_id)
        .where(AnalysisResult.overall_score >= min_score)
    )
    if label:
        q = q.where(AnalysisResult.overall_label == label)

    q = q.order_by(AnalysisResult.overall_score.desc()).offset(offset).limit(limit)

    rows = db.execute(q).all()
    return [
        {
            "id": ar.id,
            "post_id": ar.post_id,
            "post_facebook_id": post.facebook_id,
            "post_url": post.url,
            "matched_keywords": ar.matched_keywords or [],
            "keyword_severity": ar.keyword_severity,
            "overall_label": ar.overall_label,
            "overall_score": ar.overall_score,
            "reviewer_notes": ar.reviewer_notes,
            "reviewed_by": ar.reviewed_by,
        }
        for ar, post in rows
    ]


@router.post("/{result_id}/review", response_model=AnalysisResultResponse)
def review_result(result_id: uuid.UUID, body: ReviewBody, db: DB) -> dict:  # type: ignore[type-arg]
    ar = db.get(AnalysisResult, result_id)
    if not ar:
        raise HTTPException(status_code=404, detail="Analysis result not found")

    ar.reviewer_notes = body.notes
    ar.reviewed_by = body.reviewer

    if body.clear:
        post = db.get(Post, ar.post_id)
        if post:
            post.status = PostStatus.CLEARED

    db.commit()
    db.refresh(ar)

    post = db.get(Post, ar.post_id)
    return {
        "id": ar.id,
        "post_id": ar.post_id,
        "post_facebook_id": post.facebook_id if post else "",
        "post_url": post.url if post else "",
        "matched_keywords": ar.matched_keywords or [],
        "keyword_severity": ar.keyword_severity,
        "overall_label": ar.overall_label,
        "overall_score": ar.overall_score,
        "reviewer_notes": ar.reviewer_notes,
        "reviewed_by": ar.reviewed_by,
    }
