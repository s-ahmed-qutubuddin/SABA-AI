from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _session():
    s = requests.Session()
    retries = Retry(total=2, backoff_factor=0.4, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({"User-Agent": "Saba/1.0 (Jamal Family Assistant)"})
    return s


def search_web(query, limit=6):
    query = str(query).strip()
    if not query:
        return []
    limit = max(1, min(8, int(limit)))
    with _session() as session:
        response = session.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=8)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for result in soup.select(".result")[:limit]:
        a = result.select_one(".result__a")
        sn = result.select_one(".result__snippet")
        if a:
            results.append({
                "title": a.get_text(" ", strip=True)[:240],
                "url": a.get("href", "")[:1000],
                "snippet": sn.get_text(" ", strip=True)[:500] if sn else "",
            })
    return results
