"""
query_params.py — Standard pagination, sorting, and filtering dependencies.

Pagination contract (all list endpoints):
  {
      "items":       [...],
      "page":        1,
      "page_size":   25,
      "total":       1083,
      "total_pages": 44
  }

Query parameters:
  ?page=1          (1-indexed)
  ?page_size=25    (max 200)
  ?search=<term>   (substring match on entity-defined searchable fields)
  ?sort_by=<field> (allowlisted per entity)
  ?sort_order=asc|desc

Security:
  sort_by values are NEVER interpolated directly into SQL.
  Each router provides an explicit ALLOWLIST mapping {param_name: model_column}.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Generic, List, Optional, Type, TypeVar

from fastapi import Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, Query as SAQuery

M = TypeVar("M")


# ---------------------------------------------------------------------------
# Pagination response model
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel):
    items: List[Any]
    page: int
    page_size: int
    total: int
    total_pages: int


# ---------------------------------------------------------------------------
# Query parameter dataclass
# ---------------------------------------------------------------------------

@dataclass
class PageParams:
    page: int = 1
    page_size: int = 25
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"


def pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=500, description="Items per page (max 500)"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Alias for page_size"),
    search: Optional[str] = Query(None, description="Substring search"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
) -> PageParams:
    effective_page_size = limit if limit is not None else page_size
    return PageParams(
        page=page,
        page_size=effective_page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ---------------------------------------------------------------------------
# Helper: apply pagination + sorting + execute
# ---------------------------------------------------------------------------

def paginate_query(
    query: SAQuery,
    params: PageParams,
    sort_allowlist: dict[str, Any],
    response_schema,
) -> PaginatedResponse:
    """Apply sort → count → slice → serialize.

    Args:
        query:          SQLAlchemy query (filters already applied).
        params:         PageParams from request.
        sort_allowlist: {param_name: model_column_attribute}, e.g.
                        {"company_name": Company.company_name}.
        response_schema: Pydantic schema to validate each row.

    Returns:
        PaginatedResponse with serialized items.
    """
    # Sorting — only allowlisted fields
    if params.sort_by:
        col = sort_allowlist.get(params.sort_by)
        if col is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid sort_by value '{params.sort_by}'. "
                    f"Allowed: {list(sort_allowlist.keys())}"
                ),
            )
        query = query.order_by(asc(col) if params.sort_order == "asc" else desc(col))

    total = query.count()
    total_pages = math.ceil(total / params.page_size) if params.page_size else 1
    offset = (params.page - 1) * params.page_size
    rows = query.offset(offset).limit(params.page_size).all()

    items = [response_schema.model_validate(r) for r in rows]
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        page=params.page,
        page_size=params.page_size,
        total=total,
        total_pages=total_pages,
    )
