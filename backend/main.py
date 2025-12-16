import os
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from typing import Dict # <-- ADD THIS IMPORT
from urllib.parse import urlparse

from backend.models import ScrapeRequest, ScrapeResponse, Error, ScrapeResult
from backend.scraper import UniversalScraper
from datetime import datetime, timezone


# --- Setup ---
app = FastAPI(title="Lyftr AI Universal Scraper")
scraper = UniversalScraper()

# --- Serve Frontend ---
FRONTEND_DIR = "frontend/dist"

if not os.path.exists(FRONTEND_DIR):
    print(f"WARNING: Frontend build directory '{FRONTEND_DIR}' not found. Please run 'npm run build' in the frontend directory.")

# Static files for assets (JS, CSS, images) - MUST use the same path as Vite's base config
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Templates for serving the main index.html file
templates = Jinja2Templates(directory=FRONTEND_DIR)

# --- API Endpoints ---

@app.get("/healthz", response_model=Dict[str, str])
async def health_check():
    """Stage 1: Health Check"""
    return {"status": "ok"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    """Stage 2/3/4: Main Scrape Endpoint"""
    url = request.url
    if not url.startswith(("http://", "https://")):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL scheme. Only http(s) URLs are supported, received: {urlparse(url).scheme}"
        )
    
    try:
        # Pass the URL to the scraper logic
        scrape_result: ScrapeResult = await scraper.scrape(url)
        return {"result": scrape_result}
    except ValidationError as e:
        # Catch Pydantic validation errors (if data coming out of scraper is bad)
        error_msg = f"Data Validation Error: {e.errors()}"
        print(f"Critical scraping failure: {error_msg}")
        
        # Create a partial result to return, avoiding a crash
        partial_result = ScrapeResult(
            url=url,
            scrapedAt=datetime.now(timezone.utc),
            meta=scrape_result.meta, # use whatever meta we got
            sections=[],
            interactions=scrape_result.interactions,
            errors=[Error(message=error_msg, phase="validation")]
        )
        # Raise an HTTP exception with the partial result
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "An unknown error occurred on the backend", "validation_error": error_msg}
        )
    except Exception as e:
        # Catch all other unexpected backend errors
        error_msg = f"Critical scraping failure: {type(e).__name__}: {e}"
        print(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "An unknown error occurred on the backend", "internal_error": error_msg}
        )

# --- Frontend Catch-all Route ---
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_frontend(request: Request, full_path: str):
    """Stage 5: Serve the main index.html for all non-API routes"""
    try:
        # FastAPI's StaticFiles serves static assets like JS/CSS via /static mount
        # For the root path and all other frontend routes, serve index.html
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception:
        # Fallback if index.html is missing
        return HTMLResponse("<h1>Frontend Not Found</h1><p>Please ensure React app is built using 'npm run build' and the 'dist' folder exists.</p>", status_code=500)

