# backend/app/adapters/html_adapter.py
import re
from html.parser import HTMLParser
from typing import Dict, Optional, Set
import httpx

from app.adapters.base import (
    BaseAdapter,
    AdapterResult,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
)
from app.adapters.hashing import compute_content_hash

BOILERPLATE_TAGS: Set[str] = {
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "head",
    "title",
    "aside",
    "noscript",
    "svg",
    "form",
    "iframe",
}

AD_CLASS_KEYWORDS: Set[str] = {
    "ad-",
    "ads-",
    "advertisement",
    "banner",
    "cookie",
    "consent",
    "popup",
    "modal",
    "newsletter",
}

NOISE_ROLES: Set[str] = {"navigation", "banner", "contentinfo"}

VOID_ELEMENTS: Set[str] = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class _BoilerplateStripper(HTMLParser):
    """
    Zero-dependency standard library HTML parser that strips boilerplate tags,
    advertisement/cookie noise elements, and extracts structured text.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress_depth = 0
        self.stack = []  # list of (tag_lower, is_suppressed)
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        attr_dict = dict(attrs)
        classes = (attr_dict.get("class") or "").lower()
        element_id = (attr_dict.get("id") or "").lower()
        role = (attr_dict.get("role") or "").lower()

        is_noise = (
            tag_lower in BOILERPLATE_TAGS
            or any(kw in classes or kw in element_id for kw in AD_CLASS_KEYWORDS)
            or role in NOISE_ROLES
        )

        if tag_lower in VOID_ELEMENTS:
            if tag_lower == "br" and self.suppress_depth == 0:
                self.text_parts.append("\n")
            return

        should_suppress = (self.suppress_depth > 0) or is_noise
        if should_suppress:
            self.suppress_depth += 1
            self.stack.append((tag_lower, True))
        else:
            self.stack.append((tag_lower, False))
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in VOID_ELEMENTS:
            return

        # Find matching tag in reverse in stack
        for idx in range(len(self.stack) - 1, -1, -1):
            if self.stack[idx][0] == tag_lower:
                while len(self.stack) > idx:
                    _, suppressed = self.stack.pop()
                    if suppressed:
                        self.suppress_depth = max(0, self.suppress_depth - 1)
                break

        if self.suppress_depth == 0:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self.suppress_depth == 0:
            self.text_parts.append(data)


class HtmlAdapter(BaseAdapter):
    """
    Ingestion adapter for HTML sources.
    Extracts core content, suppresses boilerplate elements, and normalizes whitespace.
    """

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    @staticmethod
    def _pre_clean(html: str) -> str:
        """
        Pre-process raw HTML before any parser sees it:
        - Strip unclosed HTML comments (<!-- without a matching -->) that cause
          html.parser and BeautifulSoup to swallow all subsequent text nodes.
        - Strip closed comments too, as they never contain useful page content.
        """
        # Remove fully closed comments first
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        # Remove any remaining unclosed comment opener (<!-- to end of string)
        html = re.sub(r'<!--.*$', '', html, flags=re.DOTALL)
        # Auto-close unclosed <title> tag before next newline or tag so it doesn't swallow body elements
        html = re.sub(r'(<title(?:\s+[^>]*)?>)([^<\n]*)(?!\s*</title>)', r'\1\2</title></head>', html, flags=re.IGNORECASE)
        return html


    def normalize(self, raw_content: str) -> str:
        """
        Extract core text from raw HTML, strip boilerplate tags and noise,
        and perform strict whitespace normalization.
        """
        if not raw_content:
            return ""

        # Pre-clean: remove HTML comments (closed and unclosed) before parsing
        clean_input = self._pre_clean(raw_content)

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(clean_input, "html.parser")
            for tag in list(soup.find_all(list(BOILERPLATE_TAGS))):
                tag.decompose()
            for el in list(soup.find_all(True)):
                if el.parent is None and el != soup:
                    continue
                classes = " ".join(el.get("class", [])) if isinstance(el.get("class"), list) else str(el.get("class", ""))
                classes_lower = classes.lower()
                el_id_lower = str(el.get("id", "")).lower()
                role_lower = str(el.get("role", "")).lower()
                if (
                    any(kw in classes_lower or kw in el_id_lower for kw in AD_CLASS_KEYWORDS)
                    or role_lower in NOISE_ROLES
                ):
                    el.decompose()
            raw_text = soup.get_text(separator="\n")
        except ImportError:
            stripper = _BoilerplateStripper()
            stripper.feed(clean_input)
            raw_text = "".join(stripper.text_parts)

        # Strict whitespace normalization
        lines = []
        for raw_line in raw_text.splitlines():
            cleaned = raw_line.replace("\xa0", " ")
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines)

