from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime, timezone

# --- Data Models ---

class Link(BaseModel):
    """Represents a hyperlink."""
    text: str = Field(default="")
    href: str = Field(default="")

class Image(BaseModel):
    """Represents an image."""
    src: str = Field(default="")
    alt: str = Field(default="")

class Content(BaseModel):
    """Extracted content fields for a section."""
    headings: List[str] = Field(default_factory=list)
    text: str = Field(default="")
    links: List[Link] = Field(default_factory=list)
    images: List[Image] = Field(default_factory=list)
    lists: List[List[str]] = Field(default_factory=list)
    tables: List[Any] = Field(default_factory=list) # Use Any for flexible table structure

class Section(BaseModel):
    """A single logical section of the webpage."""
    id: str = Field(..., description="Stable identifier for the section.")
    type: Literal["hero", "section", "nav", "footer", "list", "grid", "faq", "pricing", "unknown"] = Field(..., description="Semantic type of the section.")
    label: str = Field(..., description="Human-readable label for the section.")
    sourceUrl: str = Field(..., description="The URL the section came from.")
    content: Content
    rawHtml: str = Field(..., description="Truncated HTML snippet.")
    truncated: bool = Field(..., description="True if rawHtml was truncated.")

class Meta(BaseModel):
    """SEO and structural metadata for the page."""
    title: str = Field(default="")
    description: Optional[str] = Field(default=None) # FIX: Allow None
    language: str = Field(default="")
    canonical: Optional[HttpUrl] = Field(default=None) # FIX: Allow None
    strategy: Literal["static", "js"] = Field(default="static") # NEW: Indicate strategy

class Error(BaseModel):
    """Represents a scraping error."""
    message: str
    phase: Literal["fetch", "render", "parse", "validation", "unknown", "heuristic"]

class Interactions(BaseModel):
    """Record of actions taken during JS rendering."""
    clicks: List[str] = Field(default_factory=list)
    scrolls: int = Field(default=0)
    pages: List[str] = Field(default_factory=list)

class ScrapeResult(BaseModel):
    """The complete result structure for a successful scrape."""
    url: str
    scrapedAt: datetime
    meta: Meta
    sections: List[Section]
    interactions: Interactions
    errors: List[Error] = Field(default_factory=list)

# --- API Schemas ---

class ScrapeRequest(BaseModel):
    """The model for the POST /scrape request body."""
    url: str
    # url: HttpUrl
    # url: HttpUrl
    
class ScrapeResponse(BaseModel):
    result: ScrapeResult
