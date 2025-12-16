import httpx
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timezone
from selectolax.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from backend.models import ScrapeResult, Interactions, Error, Meta
from backend.parser_utils import get_meta, get_sections, remove_noise

# --- Configuration ---
JS_FALLBACK_HEURISTIC_TEXT_MIN_LENGTH = 100 # Min text length in main content to proceed with static
MAX_SCROLL_DEPTH = 3
DEFAULT_TIMEOUT = 30000 # 30 seconds

class UniversalScraper:

    def __init__(self):
        # We will initialize playwright context within the scrape method
        pass

    async def scrape(self, url: str) -> ScrapeResult:
        """
        Main scraping function with static-first, then JS-fallback logic.
        """
        result = ScrapeResult(
            url=url,
            scrapedAt=datetime.now(timezone.utc),
            meta=Meta(strategy="static"),
            sections=[],
            interactions=Interactions(),
            errors=[]
        )
        parsed_url = urlparse(url)
        result.interactions.pages.append(url)

        try:
            # --- 1. Static Fetch Attempt ---
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                html_text = response.text
                
            tree = HTMLParser(html_text)
            html_text = remove_noise(html_text) # Noise filtering
            
            # Extract Meta and Sections from static HTML
            result.meta = get_meta(tree, url)
            result.sections = get_sections(tree, url)

            # --- 2. JS Fallback Heuristic & Pagination Trigger ---
            main_content_text = ""
            for section in result.sections:
                if section.type in ["hero", "section", "list", "grid"]:
                    main_content_text += section.content.text
            
            # Search all extracted links in the initial sections for a "next" page indicator
            # This triggers JS flow for pagination on static sites like books.toscrape.com
            has_next_page_link = any(
                # Look for "next" text or "page-" in href combined with "next" text
                link.text.lower() == 'next' or ('page-' in link.href and link.text.lower() == 'next') 
                for section in result.sections 
                for link in section.content.links
            )

            # Determine if a JS run is needed (if content is sparse OR if a next-page link is found)
            needs_js_render = (len(main_content_text) < JS_FALLBACK_HEURISTIC_TEXT_MIN_LENGTH) or has_next_page_link
            
            if needs_js_render:
                # Add a marker explaining WHY we are falling back
                if len(main_content_text) < JS_FALLBACK_HEURISTIC_TEXT_MIN_LENGTH:
                     message = f"Static content too sparse ({len(main_content_text)} chars). Falling back to JS rendering."
                else:
                     # This message triggers for the books.toscrape.com pagination flow
                     message = f"Static content found, but detected pagination link ('next'). Initiating JS rendering and interaction flow to capture all pages."
                     
                result.errors.append(Error(message=message, phase="heuristic"))
                
                # Call the JS function to handle rendering AND pagination
                await self._js_render_and_interact(url, result, html_text)
                
            return result

        except httpx.HTTPStatusError as e:
            result.errors.append(Error(message=f"HTTP Error {e.response.status_code}: {e.response.reason_phrase}", phase="fetch"))
            if e.response.status_code >= 400 and e.response.status_code < 500:
                # If static fails, we still try JS rendering for robustness
                await self._js_render_and_interact(url, result, "")
            return result

        except Exception as e:
            result.errors.append(Error(message=f"Critical error during static scrape: {type(e).__name__}: {str(e)}", phase="fetch"))
            # If static fails critically, attempt JS render
            await self._js_render_and_interact(url, result, "")
            return result

    # ... (rest of the code above this method remains the same) ...

    async def _js_render_and_interact(self, url: str, result: ScrapeResult, initial_html: str):
        """
        Handles Playwright rendering, noise filtering, and interaction flow.
        Focuses exclusively on Pagination Clicks (Max Depth 3).
        """
        result.meta.strategy = "js"
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                page.set_default_timeout(DEFAULT_TIMEOUT)

                # --- 1. Initial Page Load and Wait Strategy ---
                await page.goto(url)
                await page.wait_for_load_state("networkidle")

                # --- 2. Noise Filtering (Cookie/Modal dismissal) ---
                for selector in ['#cookie-banner button', '.cc-revoke', 'button:has-text("Accept")', '[aria-label*="cookie"] button']:
                    try:
                        await page.click(selector, timeout=2000)
                        result.interactions.clicks.append(f"Dismissed noise: {selector}")
                    except Exception:
                        pass 
                
                # --- 3. Pagination-Only Flow (Depth >= 3) ---
                all_sections = [] 
                current_url = url
                
                # Loop for initial page + MAX_SCROLL_DEPTH (4 pages total)
                for i in range(MAX_SCROLL_DEPTH + 1): 
                    
                    # A. Extract content from the CURRENT page state (Scrape page i)
                    page_html_text = await page.content()
                    page_html_text = remove_noise(page_html_text)
                    page_tree = HTMLParser(page_html_text)
                    
                    page_sections = get_sections(page_tree, current_url) 
                    all_sections.extend(page_sections)
                    
                    # Stop if max depth is reached (after scraping the last page)
                    if i >= MAX_SCROLL_DEPTH:
                        break 
                        
                    # B. Wait for the pagination block and define the locator
                    
                    try:
                        # Wait for any pagination control to appear
                        await page.wait_for_selector('.pagination', timeout=3000) 
                    except Exception:
                        result.errors.append(Error(message=f"No main pagination block found on page {i+1}. Ending interaction.", phase="heuristic"))
                        break
                        
                    # Define the Locator using the robust OR selector
                    target_locator = page.locator(
                        # Best for books.toscrape.com
                        'a:has-text("next") || ' + 
                        # Best for scrapethissite.com (the arrow)
                        'a[aria-label="Next"] || ' + 
                        'button:has-text("Load more")'
                    )
                    
                    # C. CRITICAL CHECK: If the target is not visible/enabled, break.
                    if not (await target_locator.is_visible() and await target_locator.is_enabled()):
                        result.errors.append(Error(message=f"Pagination link not visible/enabled on page {i+1}. Ending interaction.", phase="heuristic"))
                        break 
                    
                    # --- Perform Click and Navigation (THIS WAS MISSING) ---
                    
                    # 1. Get next URL for safety check
                    href = await target_locator.get_attribute('href')
                    if href:
                        next_url_absolute = urljoin(url, href)
                    else:
                        next_url_absolute = current_url # For a 'Load More' button

                    # 2. Check if the click leads to a new, unvisited page (or is a button)
                    is_new_page_needed = (href and next_url_absolute not in result.interactions.pages) or (not href)

                    if is_new_page_needed:
                        await target_locator.click()
                        
                        interaction_text = await target_locator.text_content()
                        if not interaction_text: 
                            interaction_text = await target_locator.get_attribute('aria-label') or 'Unknown Link/Button'

                        result.interactions.clicks.append(f"Followed '{interaction_text.strip()}' ({i+1})")
                        
                        # Wait for the next page to load
                        await page.wait_for_load_state("load") 
                        
                        new_url = page.url
                        current_url = new_url 
                        
                        if current_url not in result.interactions.pages:
                            result.interactions.pages.append(current_url)
                        
                    else:
                        # Safety break if the next link loops back 
                        result.errors.append(Error(message=f"Pagination click leads to an already visited URL or is not new. Ending interaction.", phase="heuristic"))
                        break
                
                # --- 4. Final Extraction & Update Result ---
                await browser.close()
                result.sections = all_sections
                result.meta.strategy = "js" 
                result.scrapedAt = datetime.now(timezone.utc)

        except Exception as e:
            result.errors.append(Error(message=f"Critical error during JS rendering/interaction: {type(e).__name__}: {str(e)}", phase="render"))