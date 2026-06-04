import httpx
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

BASE = "https://www.federalregister.gov/api/v1"

FR_SUBTYPE_MAP = {
    "EXECUTIVE ORDER":           "executive_order",
    "PROCLAMATION":              "presidential_proclamation",
    "MEMORANDUM":                "presidential_memorandum",
    "DETERMINATION":             "other",
    "NOTICE":                    "notice",
    "ORDER":                     "other",
}

def map_doc_type(subtype: str) -> str:
    return FR_SUBTYPE_MAP.get(subtype.upper(), "other")

def fetch_documents(doc_type: str = "PRESDOCU", per_page: int = 20, page: int = 1) -> list:
    r = httpx.get(f"{BASE}/documents.json", params={
        "conditions[type][]": doc_type,
        "per_page": per_page,
        "page": page,
        "fields[]": [
            "document_number",
            "title",
            "publication_date",
            "type",
            "subtype",
            "full_text_xml_url",
            "html_url",
        ],
    })
    r.raise_for_status()
    return r.json().get("results", [])

@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
)
def fetch_full_text(xml_url: str) -> Optional[str]:
    if not xml_url:
        return None
    r = httpx.get(xml_url, timeout=30)
    r.raise_for_status()
    return r.text