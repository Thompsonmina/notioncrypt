from typing import Any, Dict
from urllib.parse import urlparse
from uuid import UUID

def get_url(object_id: str) -> str:
    """Return the URL for the object with the given id."""
    return "https://notion.so/" + UUID(object_id).hex


def get_id(url: str) -> str:
    """Return the id of the object behind the given URL."""
    parsed = urlparse(url)
    if "notion.so" != parsed.netloc[-9:]:
        raise ValueError("Not a valid Notion URL.")
    path = parsed.path
    if len(path) < 32:
        raise ValueError("The path in the URL seems to be incorrect.")
    raw_id = path[-32:]
    return str(UUID(raw_id))