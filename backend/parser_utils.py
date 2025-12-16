from selectolax.parser import HTMLParser
from urllib.parse import urljoin
import re
from typing import List, Optional, Literal, Dict, Any
from .models import Meta, Content, Section, Link, Image, ScrapeResult, Error

def get_meta(tree: HTMLParser, url: str) -> Meta:
    canonical_node = tree.css_first("link[rel='canonical']")
    canonical_href = canonical_node.attributes.get('href') if canonical_node else None
    
    """Extracts required metadata from the HTML tree."""
    title = tree.css_first("title")
    og_title = tree.css_first("meta[property='og:title']")

    # Ensure to handle description gracefully, as it can be Optional[str] or HttpUrl
    description_node = tree.css_first("meta[name='description']")
    description = description_node.attributes.get('content', '') if description_node else None
    
    meta = Meta(
        title=(title.text() if title else og_title.attributes.get('content', '') if og_title else ""),
        description=description, # Corrected assignment
        language=tree.root.attributes.get('lang', 'en'),
        # Keep ONLY the correct, absolute assignment for canonical:
        canonical=urljoin(url, canonical_href) if canonical_href else None 
    )
    return meta

# Define a character limit for rawHtml truncation
TRUNCATION_LIMIT = 500

def extract_section_content(node, base_url: str) -> Content:
    """Extracts content components (headings, text, links, images, lists) from a given node."""

    # 1. Headings (h1-h6 inside the section)
    headings = [h.text(strip=True) for h in node.css('h1, h2, h3, h4, h5, h6') if h.text(strip=True)]

    # 2. Text (Cleaned, consolidated text)
    text_content = re.sub(r'\s+', ' ', node.text(separator=' ', strip=True)).strip()

    # 3. Links
    links = []
    for a in node.css('a[href]'):
        href = a.attributes.get('href')
        if href:
            # Make absolute URL
            absolute_href = urljoin(base_url, href)
            links.append(Link(text=a.text(strip=True) or absolute_href, href=absolute_href))

    # 4. Images
    images = []
    for img in node.css('img[src]'):
        src = img.attributes.get('src')
        if src:
            # Make absolute URL
            absolute_src = urljoin(base_url, src)
            images.append(Image(src=absolute_src, alt=img.attributes.get('alt', '')))

    # 5. Lists (simple list items)
    lists = []
    for ul_ol in node.css('ul, ol'):
        list_items = [li.text(strip=True) for li in ul_ol.css('li') if li.text(strip=True)]
        if list_items:
            lists.append(list_items)

    # 6. Tables (Simplification: return the table HTML as a string)
    tables = [t.html for t in node.css('table')]

    return Content(
        headings=headings,
        text=text_content,
        links=links,
        images=images,
        lists=lists,
        tables=tables
    )

def determine_section_type(node) -> Literal["hero", "section", "nav", "footer", "list", "grid", "faq", "pricing", "unknown"]:
    """Guesses the section type based on tag name and attributes."""
    tag = node.tag
    role = node.attributes.get('role', '').lower()

    if tag == 'header': return 'nav'
    if tag == 'nav' or role == 'navigation': return 'nav'
    if tag == 'footer': return 'footer'
    if tag == 'section':
        # Look for common classes/IDs
        if re.search(r'hero|banner', node.attributes.get('id', '') + node.attributes.get('class', ''), re.I):
            return 'hero'
        return 'section'
    if tag in ['ul', 'ol']: return 'list'
    if tag == 'main': return 'section'
    if tag == 'div':
        # Look for grid/list/card patterns in classes
        if re.search(r'grid|list|cards|faqs', node.attributes.get('class', ''), re.I):
            return 'grid' if 'grid' in node.attributes.get('class', '') else 'list'
        if re.search(r'faq', node.attributes.get('id', '') + node.attributes.get('class', ''), re.I):
            return 'faq'

    return 'unknown'

def create_section(node, base_url: str, section_index: int) -> Section:
    """Creates a Section object from a selectolax node."""

    raw_html = node.html
    truncated = len(raw_html) > TRUNCATION_LIMIT

    content = extract_section_content(node, base_url)

    # Determine type and label
    section_type = determine_section_type(node)

    # Derive label from heading or text
    if content.headings:
        label = content.headings[0]
    elif content.text:
        label = ' '.join(content.text.split()[:7]) + ('...' if len(content.text.split()) > 7 else '')
    else:
        label = f"{section_type.capitalize()} Section"

    return Section(
        id=f"{section_type}-{section_index}",
        type=section_type,
        label=label,
        sourceUrl=base_url,
        content=content,
        rawHtml=raw_html[:TRUNCATION_LIMIT],
        truncated=truncated
    )

def get_sections(tree: HTMLParser, base_url: str) -> List[Section]:
    """Groups the HTML content into structured sections."""
    sections = []

    # Priority 1: Semantic HTML (main, header, footer, nav, section)
    semantic_selectors = ['main', 'section', 'nav', 'header', 'footer']
    for i, selector in enumerate(semantic_selectors):
        for node in tree.css(selector):
            sections.append(create_section(node, base_url, len(sections)))

    # Priority 2: High-level divs (if main content is missing or for further breakdown)
    if not sections:
         for node in tree.css('body > div'):
            sections.append(create_section(node, base_url, len(sections)))

    # Basic filtering to remove empty or noise sections
    sections = [s for s in sections if s.content.text or s.content.images or s.content.links]

    return sections

# --- Noise Filtering ---
# Common selectors for noise elements (cookie banners, modals, etc.)
NOISE_SELECTORS = [
    '[class*="cookie"]', 
    '[id*="modal"]', 
    '[id*="popup"]', 
    '[aria-modal="true"]', 
    '[role="dialog"]',
    '.newsletter-signup',
    '.ad-banner'
]

def remove_noise(html_content: str) -> str:
    """Removes common noise elements from the HTML content."""
    tree = HTMLParser(html_content)
    for selector in NOISE_SELECTORS:
        for node in tree.css(selector):
            node.remove()
    return tree.html