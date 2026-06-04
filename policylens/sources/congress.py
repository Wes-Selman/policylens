import os
import httpx
from typing import Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.congress.gov/v3"

CONGRESS_TYPE_MAP = {
    "HR":      "bill",
    "S":       "bill",
    "HJRES":   "resolution",
    "SJRES":   "resolution",
    "HCONRES": "resolution",
    "SCONRES": "resolution",
    "HRES":    "resolution",
    "SRES":    "resolution",
}

def map_doc_type(bill_type: str) -> str:
    return CONGRESS_TYPE_MAP.get(bill_type.upper(), "other")

def _headers():
    return {"X-Api-Key": os.environ["CONGRESS_API_KEY"]}

def fetch_bills(congress: int = 119, limit: int = 20, offset: int = 0) -> list:
    r = httpx.get(
        f"{BASE}/bill/{congress}",
        headers=_headers(),
        params={"limit": limit, "offset": offset, "format": "json"},
    )
    r.raise_for_status()
    return r.json().get("bills", [])

def fetch_bills_by_type(congress: int, bill_type: str, limit: int = 20, offset: int = 0) -> list:
    r = httpx.get(
        f"{BASE}/bill/{congress}/{bill_type.lower()}",
        headers=_headers(),
        params={"limit": limit, "offset": offset, "format": "json"},
    )
    r.raise_for_status()
    return r.json().get("bills", [])

@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
)
def fetch_bill_text(congress: int, bill_type: str, bill_number: int) -> Tuple[Optional[str], str]:
    url = f"{BASE}/bill/{congress}/{bill_type.lower()}/{bill_number}/text"
    r = httpx.get(url, headers=_headers(), params={"format": "json"})
    r.raise_for_status()
    versions = r.json().get("textVersions", [])
    if not versions:
        return None, "text"
    formats = versions[0].get("formats", [])
    for fmt in formats:
        if fmt.get("type") == "Formatted XML":
            xml_r = httpx.get(fmt["url"], timeout=30)
            xml_r.raise_for_status()
            return xml_r.text, "xml"
    for fmt in formats:
        if fmt.get("type") == "Formatted Text":
            html_r = httpx.get(fmt["url"], timeout=30)
            html_r.raise_for_status()
            return html_r.text, "html"
    return None, "text"