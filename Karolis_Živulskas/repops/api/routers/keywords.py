"""CRUD endpoints for keyword sets and entries."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from repops.api.dependencies import get_db
from repops.models import KeywordEntry, KeywordSet

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


# Pydantic schemas
class KeywordSetCreate(BaseModel):
    name: str
    description: str | None = None
    language: str | None = None


class KeywordSetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    language: str | None
    is_active: bool
    entry_count: int = 0

    model_config = {"from_attributes": True}


class KeywordEntryCreate(BaseModel):
    pattern: str
    is_regex: bool = False
    severity: int = 1
    added_by: str | None = None


class KeywordEntryResponse(BaseModel):
    id: uuid.UUID
    keyword_set_id: uuid.UUID
    pattern: str
    is_regex: bool
    severity: int
    added_by: str | None

    model_config = {"from_attributes": True}


# KeywordSet routes
@router.get("/sets", response_model=list[KeywordSetResponse])
def list_keyword_sets(db: DB) -> list[KeywordSet]:
    sets = list(db.scalars(select(KeywordSet)).all())
    return sets


@router.post("/sets", response_model=KeywordSetResponse, status_code=status.HTTP_201_CREATED)
def create_keyword_set(body: KeywordSetCreate, db: DB) -> KeywordSet:
    existing = db.scalar(select(KeywordSet).where(KeywordSet.name == body.name))
    if existing:
        raise HTTPException(status_code=409, detail="Keyword set with this name already exists")
    ks = KeywordSet(**body.model_dump())
    db.add(ks)
    db.commit()
    db.refresh(ks)
    return ks


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_set(set_id: uuid.UUID, db: DB) -> None:
    ks = db.get(KeywordSet, set_id)
    if not ks:
        raise HTTPException(status_code=404, detail="Keyword set not found")
    db.delete(ks)
    db.commit()


# KeywordEntry routes
@router.get("/sets/{set_id}/entries", response_model=list[KeywordEntryResponse])
def list_entries(set_id: uuid.UUID, db: DB) -> list[KeywordEntry]:
    ks = db.get(KeywordSet, set_id)
    if not ks:
        raise HTTPException(status_code=404, detail="Keyword set not found")
    return list(db.scalars(select(KeywordEntry).where(KeywordEntry.keyword_set_id == set_id)).all())


@router.post(
    "/sets/{set_id}/entries",
    response_model=KeywordEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_entry(set_id: uuid.UUID, body: KeywordEntryCreate, db: DB) -> KeywordEntry:
    ks = db.get(KeywordSet, set_id)
    if not ks:
        raise HTTPException(status_code=404, detail="Keyword set not found")
    entry = KeywordEntry(keyword_set_id=set_id, **body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: uuid.UUID, db: DB) -> None:
    entry = db.get(KeywordEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
