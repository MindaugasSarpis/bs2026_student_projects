"""CRUD endpoints for monitoring targets."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from repops.api.dependencies import get_db
from repops.models import Target, TargetType
from repops.workers.app import app as celery_app

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


# Pydantic schemas
class TargetCreate(BaseModel):
    facebook_id: str
    name: str
    target_type: TargetType
    url: str | None = None
    description: str | None = None
    scan_interval_minutes: int = 60
    priority: int = 1


class TargetResponse(BaseModel):
    id: uuid.UUID
    facebook_id: str
    name: str
    target_type: TargetType
    url: str | None
    is_active: bool
    scan_interval_minutes: int
    priority: int

    model_config = {"from_attributes": True}


# Routes
@router.get("/", response_model=list[TargetResponse])
def list_targets(db: DB, active_only: bool = False) -> list[Target]:
    q = select(Target)
    if active_only:
        q = q.where(Target.is_active.is_(True))
    return list(db.scalars(q).all())


@router.post("/", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
def create_target(body: TargetCreate, db: DB) -> Target:
    existing = db.scalar(select(Target).where(Target.facebook_id == body.facebook_id))
    if existing:
        raise HTTPException(status_code=409, detail="Target with this facebook_id already exists")

    target = Target(**body.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/{target_id}", response_model=TargetResponse)
def get_target(target_id: uuid.UUID, db: DB) -> Target:
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.patch("/{target_id}/activate", response_model=TargetResponse)
def activate_target(target_id: uuid.UUID, db: DB) -> Target:
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    target.is_active = True
    db.commit()
    db.refresh(target)
    return target


@router.patch("/{target_id}/deactivate", response_model=TargetResponse)
def deactivate_target(target_id: uuid.UUID, db: DB) -> Target:
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    target.is_active = False
    db.commit()
    db.refresh(target)
    return target


@router.post("/{target_id}/collect", status_code=status.HTTP_202_ACCEPTED)
def trigger_collection(target_id: uuid.UUID, db: DB) -> dict:
    """Manually trigger a collection run for a target."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if not target.is_active:
        raise HTTPException(status_code=400, detail="Target is not active")

    task = celery_app.send_task(
        "repops.collector.tasks.collect_target",
        args=[str(target_id)],
        queue="collection",
    )
    return {"task_id": task.id, "target_id": str(target_id)}


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target(target_id: uuid.UUID, db: DB) -> None:
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    db.delete(target)
    db.commit()
