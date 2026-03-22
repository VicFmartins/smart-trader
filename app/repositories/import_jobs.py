from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_job import ImportJob


class ImportJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, import_job: ImportJob) -> ImportJob:
        self.db.add(import_job)
        self.db.commit()
        self.db.refresh(import_job)
        return import_job

    def save(self, import_job: ImportJob) -> ImportJob:
        self.db.add(import_job)
        self.db.commit()
        self.db.refresh(import_job)
        return import_job

    def get_by_batch_id(self, batch_id: str) -> ImportJob | None:
        statement = select(ImportJob).where(ImportJob.batch_id == batch_id)
        return self.db.execute(statement).scalar_one_or_none()
