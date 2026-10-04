"""Small, dependency-free helpers for trustworthy article descriptions."""

from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth and data.strip():
            self.parts.append(data.strip())


def normalize_summary_text(value: str | None) -> str:
    """Normalize text for title/description equality checks."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).casefold()


def is_duplicate_description(title: str | None, description: str | None) -> bool:
    """Return True when a supposed description is only a copy of the title."""
    normalized_title = normalize_summary_text(title)
    normalized_description = normalize_summary_text(description)
    return bool(normalized_title and normalized_title == normalized_description)


def finalize_article_description(value: str | None, length: int = 76) -> str:
    """Keep a description compact and make it end with a Chinese full stop."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    limit = max(24, int(length))
    sentence_end = re.search(r"[。！？!?]", text[: limit + 1])
    if sentence_end:
        text = text[: sentence_end.end()]
    elif len(text) > limit:
        text = text[:limit]
    text = re.sub(r"[。！？!?；;，,、：:\s…—-]+$", "", text).strip()
    return f"{text}。" if text else ""


def derive_article_description(
    content: str | None,
    title: str | None = None,
    length: int = 160,
) -> str:
    """Build a short description from HTML already cached by the collector."""
    if not (content or "").strip():
        return ""

    parser = _TextExtractor()
    try:
        parser.feed(str(content))
        parser.close()
    except Exception:
        return ""
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    if not text:
        return ""

    title_text = re.sub(r"\s+", " ", str(title or "")).strip()
    if title_text and text.startswith(title_text):
        text = text[len(title_text):].lstrip(" ：:|｜·-—")
    if not text or is_duplicate_description(title, text):
        return ""

    return finalize_article_description(text, length)
