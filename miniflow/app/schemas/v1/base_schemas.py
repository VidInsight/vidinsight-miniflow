from typing import Optional, List, Any, Dict
from pydantic import BaseModel
from datetime import datetime, timezone


class BaseResponse(BaseModel):
    message: str
    status: bool = True
    timestamp: datetime = datetime.now(timezone.utc)

class ErrorResponse(BaseResponse):
    status: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class DataResponse(BaseResponse):
    data: Any

class CountResponse(BaseResponse):
    count: int

class ExistsResponse(BaseResponse):
    exists: bool
    name: Optional[str] = None

class ListResponse(BaseResponse):
    data: List[Any]
    total_count: int
    page: Optional[int] = None
    page_size: Optional[int] = None