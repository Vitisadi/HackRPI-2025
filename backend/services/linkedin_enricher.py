import json
import re
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse, urlunparse, unquote
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By

SEARCH_URL = "https://duckduckgo.com/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_LINKEDIN_HTML_CHARS = 100000
HTTP_TIMEOUT = 15

# ======================================================
# MAIN ENTRY POINT
# ======================================================
def enrich_linkedin_profile(
    person_name: Optional[str],
    keywords: Optional[Sequence[str]],
    conversation: Optional[Sequence[Any]],
    gemini_client,
) -> Dict[str, str]:
    """
    Use DuckDuckGo search to find LinkedIn profile URLs.
    Returns {"linkedin": "...", "bio": "..."} when available.
    """
    if not person_name:
        return {}

    # Debug: print original inputs
    print(f"📝 Original person_name: '{person_name}'")
    print(f"📝 Original keywords: {keywords}")
    
    # Filter keywords using Gemini to keep only relevant ones
    filtered_keywords = _filter_keywords_with_gemini(person_name, keywords or [], gemini_client)
    
    query = _build_search_query(person_name, filtered_keywords, conversation or [])
    print(f"🔎 Final search query: {query}")

    # Fetch search results using DuckDuckGo
    search_html = _fetch_duckduckgo_html(query)
    if not search_html:
        return {}

    # Extract LinkedIn profile URLs
    profile_urls = _extract_linkedin_profiles(search_html)
    
    print(f"\n🔹 Found {len(profile_urls)} LinkedIn profile(s)")
    for idx, url in enumerate(profile_urls, 1):
        print(f"   {idx}. {url}")
    
    if not profile_urls:
        print("⚠️ No LinkedIn profiles found")
        return {}
    
    # Use the first profile URL found
    linkedin_url = profile_urls[0]
    print(f"✅ Selected: {linkedin_url}")

    return {"linkedin": linkedin_url}


# ======================================================
# FILTER KEYWORDS WITH GEMINI
# ======================================================
def _filter_keywords_with_gemini(
    person_name: str,
    keywords: Sequence[str],
    gemini_client,
) -> List[str]:
    """
    Use Gemini to filter keywords, keeping only relevant ones for LinkedIn search.
    Removes generic terms like programming languages, keeps companies, locations, schools.
    """
    if not gemini_client or not keywords:
        return list(keywords)
    
    # Remove person's name from keywords if it exists (case-insensitive)
    person_name_lower = person_name.lower()
    filtered_input = [kw for kw in keywords if kw.lower() != person_name_lower]
    
    if not filtered_input:
        return []
    
    keywords_str = ", ".join(filtered_input)
    
    prompt = f"""
You are filtering keywords for a LinkedIn search. DO NOT modify or return the person's name.

Keywords to filter: {keywords_str}

Task: Return ONLY the filtered keywords array. Do NOT include the person's name in your response.

KEEP these types of keywords:
- Company names (e.g., Datadog, Google, Microsoft)
- Schools/Universities (e.g., RPI, MIT, Stanford)
- Locations/Cities (e.g., NYC, New York City, San Francisco)
- Specific roles like "intern"

REMOVE these types of keywords:
- Programming languages (e.g., Java, Python, JavaScript)
- Technologies/frameworks (e.g., React, Django, AWS)
- Generic job titles (e.g., backend engineer, software engineer, developer)
- Generic skills
- Duplicate locations (e.g., keep "NYC" but remove "New York area")

CRITICAL: Do NOT modify spellings. Return keywords EXACTLY as they appear in the input list.
CRITICAL: Do NOT include any person names in the filtered keywords.

Return ONLY a JSON array of the filtered keywords (maximum 5-6):
["keyword1", "keyword2", ...]

Example input: "Datadog, intern, New York City, RPI, New York area, Java"
Example output: ["Datadog", "intern", "New York City", "RPI"]
"""
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt,
        )
        text = (response.text or "").strip()
        
        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
            if text.startswith("json"):
                text = text[4:].strip()
        
        filtered = json.loads(text)
        print(f"🧠 Gemini filtered keywords: {keywords} → {filtered}")
        return filtered if isinstance(filtered, list) else list(keywords)
    except Exception as e:
        print(f"⚠️ Keyword filtering failed: {e}, using original keywords")
        return list(keywords)


# ======================================================
# BUILD SIMPLE GOOGLE QUERY (NEW)
# ======================================================
def _build_search_query(
    person_name: str,
    keywords: Sequence[str],
    conversation: Sequence[Any],
) -> str:
    """
    Build search query: keywords + name + "linkedin" + "site:linkedin.com/in"
    Example:
    keywords=["datadog","intern","nyc","rpi"], name="shimu"
    → "datadog intern nyc rpi shimu linkedin site:linkedin.com/in"
    """
    tokens: List[str] = []

    for kw in keywords:
        kw = kw.strip()
        if kw:
            tokens.append(kw)

    if person_name:
        name_clean = person_name.strip()
        print(f"🔤 Adding name to query: '{name_clean}'")
        tokens.append(name_clean)
    
    # Always add LinkedIn to narrow search
    tokens.append("linkedin")

    return " ".join(tokens)


# ======================================================
# HTML FETCH
# ======================================================
def _fetch_html(url: str, params: Optional[Dict[str, str]] = None) -> Optional[str]:
    try:
        response = requests.get(
            url,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.text
    except Exception as exc:
        print(f"⚠️ HTTP fetch failed for {url}: {exc}")
        return None


def _fetch_duckduckgo_html(query: str) -> Optional[str]:
    """Fetch search results using DuckDuckGo with Firefox (no robot checks)."""
    options = FirefoxOptions()
    options.add_argument("--headless")
    
    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        print(f"🌐 Loading DuckDuckGo...")
        driver.get(SEARCH_URL)
        
        print(f"🔍 Searching for: {query}")
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(query)
        search_box.submit()
        
        print("⏳ Waiting for results...")
        time.sleep(5)
        
        html = driver.page_source
        print(f"📄 Got HTML ({len(html)} chars)")
        return html
    except Exception as exc:
        print(f"⚠️ DuckDuckGo search failed: {exc}")
        return None
    finally:
        if driver:
            driver.quit()


def _extract_linkedin_profiles(html: str) -> List[str]:
    """Extract unique LinkedIn profile URLs (/in/) from HTML, excluding posts."""
    soup = BeautifulSoup(html, 'html.parser')
    
    all_links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        all_links.append(href)
    
    # Filter LinkedIn links
    linkedin_links = []
    for link in all_links:
        if 'linkedin.com' in link.lower():
            # Clean up redirect URLs
            if '/url?q=' in link:
                match = re.search(r'/url\?q=([^&]+)', link)
                if match:
                    link = unquote(match.group(1))
            linkedin_links.append(link)
    
    # Filter to only profile links (/in/) and remove posts
    profile_links = []
    for link in linkedin_links:
        if '/in/' in link and '/posts/' not in link:
            profile_links.append(link)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_profiles = []
    for link in profile_links:
        # Normalize by removing query params and fragments
        base_url = link.split('?')[0].split('#')[0]
        if base_url not in seen:
            seen.add(base_url)
            unique_profiles.append(base_url)
    
    return unique_profiles