from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from app.schemas.common import PaginationMeta, PaginationParams


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PagedResult(Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int

    def to_pagination_meta(self) -> PaginationMeta:
        count = len(self.items)
        return PaginationMeta(
            total=self.total,
            offset=self.offset,
            limit=self.limit,
            count=count,
            has_more=self.offset + count < self.total,
        )


def build_paged_result(items: list[T], total: int, params: PaginationParams) -> PagedResult[T]:
    return PagedResult(items=items, total=total, offset=params.offset, limit=params.limit)
