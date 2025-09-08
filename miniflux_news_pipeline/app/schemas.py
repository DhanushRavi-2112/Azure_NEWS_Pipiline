from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List, Dict, Any

class MinifluxEntry(BaseModel):
    id: int
    user_id: int
    feed_id: int
    title: str
    url: HttpUrl
    author: Optional[str] = None
    content: Optional[str] = None
    published_at: datetime
    created_at: datetime
    status: str
    starred: bool
    feed: Dict[str, Any]
    
class WebhookPayload(BaseModel):
    event_type: str
    entry: MinifluxEntry
    
class ArticleResponse(BaseModel):
    id: int
    entry_id: str
    title: str
    url: str
    published_at: datetime
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True