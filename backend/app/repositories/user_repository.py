from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class UserRepository:
    def __init__(self, session: Session, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    def create(self, **data: Any) -> ModelType:
        instance = self.model(**data)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def get_by_id(self, user_id: int) -> ModelType | None:
        return self.session.get(self.model, user_id)

    def get_by_email(self, email: str) -> ModelType | None:
        statement = select(self.model).where(self.model.email == email)
        return self.session.scalar(statement)
