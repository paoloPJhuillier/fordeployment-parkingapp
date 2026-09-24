from pydantic import BaseModel
from typing import Optional


class SiteContentUpdate(BaseModel):
    heading_line1: Optional[str] = None
    heading_highlight: Optional[str] = None
    heading_line3: Optional[str] = None
    description: Optional[str] = None
    badge1_text: Optional[str] = None
    badge2_text: Optional[str] = None
    announcement: Optional[str] = None
