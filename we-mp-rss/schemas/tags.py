from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import json
class TagsBase(BaseModel):
    name: str
    cover: Optional[str] = None
    intro: Optional[str] = None
    mps_id: str
    status: int = 1

class TagsCreate(TagsBase):
    pass

class Tags(TagsBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True