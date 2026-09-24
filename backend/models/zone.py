from pydantic import BaseModel, Field
from typing import List, Optional


class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=25)
    building_ids: List[str] = []
    user_ids: List[str] = []


class ZoneResponse(BaseModel):
    id: str
    name: str
    building_ids: List[str] = []
    user_ids: List[str] = []
    created_at: str


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=25)
    building_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
