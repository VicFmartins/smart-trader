from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)


class PaginationMeta(BaseModel):
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    count: int = Field(ge=0)
    has_more: bool


class APIResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T


class ListAPIResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: list[T]
    pagination: PaginationMeta


class ValidationIssue(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    status: str = "error"
    detail: str
    error_code: str
    errors: list[ValidationIssue] = Field(default_factory=list)
