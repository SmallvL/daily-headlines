from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: ApiError | None = None
    request_id: str | None = None
