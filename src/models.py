"""Clean record schema + the normalisation that turns raw strings into it. Raw and clean values live side by side."""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class Book(BaseModel):
    title: str = Field(min_length=1)
    product_url: str                      # canonical, absolute URL = the record's identity
    price_text: str                       # raw, as shown ("£51.77")
    price_gbp: float = Field(gt=0)        # clean number
    availability_text: str                # raw ("In stock (22 available)")
    in_stock: bool
    stock_count: Optional[int] = Field(default=None, ge=0)
    rating_text: Literal["One", "Two", "Three", "Four", "Five"]
    rating: int = Field(ge=1, le=5)
    description: Optional[str] = None     # optional: some books have none
    source_page: str                      # provenance: which catalogue page linked to it
    fetched_at: str                       # provenance: when the HTML came from the site

    @field_validator("product_url", "source_page")
    @classmethod
    def absolute_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("must be an absolute https:// URL")
        return v


def normalize(raw: dict) -> dict:
    """Raw strings → clean values. Anything unparseable becomes None and the schema will reject it."""
    price = re.search(r"\d+(?:\.\d+)?", raw.get("price_text") or "")
    avail = raw.get("availability_text") or ""
    count = re.search(r"\((\d+) available\)", avail)
    return {
        **raw,
        "price_gbp": float(price.group()) if price else None,
        "in_stock": avail.lower().startswith("in stock"),
        "stock_count": int(count.group(1)) if count else None,
        "rating": RATINGS.get(raw.get("rating_text") or ""),
    }
