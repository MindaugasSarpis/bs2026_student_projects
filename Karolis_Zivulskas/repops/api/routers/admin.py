"""Browser-facing admin UI for managing targets and keyword sets."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from repops.api.dependencies import get_db
from repops.models import AnalysisLabel, AnalysisResult, KeywordEntry, KeywordSet, Post, PostStatus, Target, TargetType
from repops.settings import settings
from repops.workers.app import app as celery_app

_security = HTTPBasic()


def _require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    ok = secrets.compare_digest(credentials.username, settings.admin_username) and \
         secrets.compare_digest(credentials.password, settings.admin_password.get_secret_value())
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


router = APIRouter(dependencies=[Depends(_require_auth)])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
DB = Annotated[Session, Depends(get_db)]


@router.get("/", response_class=HTMLResponse)
def admin_index() -> RedirectResponse:
    return RedirectResponse("/admin/targets")


@router.get("/targets", response_class=HTMLResponse)
def targets_page(request: Request, db: DB) -> HTMLResponse:
    targets = list(db.scalars(select(Target)).all())
    return templates.TemplateResponse(request, "admin/targets.html", {
        "targets": targets,
        "target_types": [t.value for t in TargetType],
    })


@router.post("/targets/add")
def add_target(
    db: DB,
    facebook_id: str = Form(...),
    name: str = Form(...),
    target_type: str = Form(...),
    url: str = Form(""),
    scan_interval_minutes: int = Form(60),
    priority: int = Form(1),
) -> RedirectResponse:
    if not db.scalar(select(Target).where(Target.facebook_id == facebook_id)):
        db.add(Target(
            facebook_id=facebook_id,
            name=name,
            target_type=TargetType(target_type),
            url=url or None,
            scan_interval_minutes=scan_interval_minutes,
            priority=priority,
        ))
        db.commit()
    return RedirectResponse("/admin/targets", status_code=303)


@router.post("/targets/{target_id}/toggle")
def toggle_target(target_id: uuid.UUID, db: DB) -> RedirectResponse:
    target = db.get(Target, target_id)
    if target:
        target.is_active = not target.is_active
        db.commit()
    return RedirectResponse("/admin/targets", status_code=303)


@router.post("/targets/{target_id}/collect")
def collect_target(target_id: uuid.UUID, db: DB) -> RedirectResponse:
    target = db.get(Target, target_id)
    if target and target.is_active:
        celery_app.send_task(
            "repops.collector.tasks.collect_target",
            args=[str(target_id)],
            queue="collection",
        )
    return RedirectResponse("/admin/targets", status_code=303)


@router.post("/targets/{target_id}/delete")
def delete_target(target_id: uuid.UUID, db: DB) -> RedirectResponse:
    target = db.get(Target, target_id)
    if target:
        db.delete(target)
        db.commit()
    return RedirectResponse("/admin/targets", status_code=303)


@router.get("/flagged", response_class=HTMLResponse)
def flagged_page(request: Request, db: DB) -> HTMLResponse:
    posts = list(db.scalars(
        select(Post)
        .join(AnalysisResult, AnalysisResult.post_id == Post.id)
        .where(AnalysisResult.overall_label != AnalysisLabel.CLEAN)
        .order_by(Post.created_at.desc())
        .limit(200)
    ).all())
    latest_result: dict[uuid.UUID, AnalysisResult] = {}
    for post in posts:
        result = db.scalar(
            select(AnalysisResult)
            .where(AnalysisResult.post_id == post.id)
            .order_by(AnalysisResult.created_at.desc())
        )
        if result:
            latest_result[post.id] = result
    return templates.TemplateResponse(request, "admin/flagged.html", {
        "posts": posts,
        "latest_result": latest_result,
    })


@router.post("/flagged/{post_id}/review")
def mark_reviewed(post_id: uuid.UUID, db: DB) -> RedirectResponse:
    post = db.get(Post, post_id)
    if post and post.status in (PostStatus.FLAGGED, PostStatus.ANALYZED):
        post.status = PostStatus.CLEARED
        db.commit()
    return RedirectResponse("/admin/flagged", status_code=303)


@router.get("/keywords", response_class=HTMLResponse)
def keywords_page(request: Request, db: DB) -> HTMLResponse:
    sets = list(db.scalars(select(KeywordSet)).all())
    entries_by_set = {
        ks.id: list(db.scalars(select(KeywordEntry).where(KeywordEntry.keyword_set_id == ks.id)).all())
        for ks in sets
    }
    return templates.TemplateResponse(request, "admin/keywords.html", {
        "sets": sets,
        "entries_by_set": entries_by_set,
    })


@router.post("/keywords/sets/add")
def add_keyword_set(
    db: DB,
    name: str = Form(...),
    description: str = Form(""),
    language: str = Form(""),
) -> RedirectResponse:
    if not db.scalar(select(KeywordSet).where(KeywordSet.name == name)):
        db.add(KeywordSet(name=name, description=description or None, language=language or None))
        db.commit()
    return RedirectResponse("/admin/keywords", status_code=303)


@router.post("/keywords/sets/{set_id}/delete")
def delete_keyword_set(set_id: uuid.UUID, db: DB) -> RedirectResponse:
    ks = db.get(KeywordSet, set_id)
    if ks:
        db.delete(ks)
        db.commit()
    return RedirectResponse("/admin/keywords", status_code=303)


@router.post("/keywords/sets/{set_id}/entries/add")
def add_entry(
    set_id: uuid.UUID,
    db: DB,
    pattern: str = Form(...),
    severity: int = Form(1),
    is_regex: str | None = Form(None),
    added_by: str = Form(""),
) -> RedirectResponse:
    if db.get(KeywordSet, set_id):
        db.add(KeywordEntry(
            keyword_set_id=set_id,
            pattern=pattern,
            severity=severity,
            is_regex=is_regex is not None,
            added_by=added_by or None,
        ))
        db.commit()
    return RedirectResponse("/admin/keywords", status_code=303)


@router.post("/keywords/entries/{entry_id}/delete")
def delete_entry(entry_id: uuid.UUID, db: DB) -> RedirectResponse:
    entry = db.get(KeywordEntry, entry_id)
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse("/admin/keywords", status_code=303)
