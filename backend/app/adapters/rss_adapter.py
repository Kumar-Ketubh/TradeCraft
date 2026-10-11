# backend/app/adapters/rss_adapter.py
import re
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

from app.adapters.base import (
    BaseAdapter,
    AdapterResult,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
)


class RssAdapter(BaseAdapter):
    """
    Ingestion adapter for RSS and Atom syndication feeds.
    Parses entry titles, links, publication timestamps, and summaries.
    """

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        }

    def normalize(self, raw_content: str) -> str:
        """
        Normalize raw RSS/Atom feed content into structured, deterministic text.
        Strips HTML tags from summaries and normalizes whitespace.
        """
        if not raw_content:
            return ""

        entries = self._extract_entries(raw_content)
        if not entries:
            return ""

        lines: List[str] = []
        for e in entries:
            clean_summary = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
            clean_summary = clean_summary.replace("\xa0", " ")
            clean_summary = re.sub(r"\s+", " ", clean_summary).strip()

            lines.append(f"Title: {e.get('title', '').strip()}")
            lines.append(f"Link: {e.get('link', '').strip()}")
            lines.append(f"Published: {e.get('published', '').strip()}")
            lines.append(f"Summary: {clean_summary}")
            lines.append("---")

        return "\n".join(lines)

    def _extract_entries(self, raw_content: str) -> List[Dict[str, str]]:
        """
        Extract entries from feed using feedparser as primary parser,
        falling back to xml.etree.ElementTree if feedparser is unavailable.
        """
        try:
            import feedparser

            feed = feedparser.parse(raw_content)
            entries: List[Dict[str, str]] = []
            for item in feed.entries:
                title = str(item.get("title", "") or "").strip()
                link = str(item.get("link", "") or "").strip()
                published = str(
                    item.get("published", "")
                    or item.get("updated", "")
                    or item.get("pubDate", "")
                    or ""
                ).strip()
                summary = str(
                    item.get("summary", "")
                    or item.get("description", "")
                    or ""
                ).strip()
                entries.append({
                    "title": title,
                    "link": link,
                    "published": published,
                    "summary": summary,
                })
            return entries
        except ImportError:
            return self._extract_entries_element_tree(raw_content)

    def _extract_entries_element_tree(self, raw_content: str) -> List[Dict[str, str]]:
        """
        Built-in fallback entry extractor using Python's standard library ElementTree.
        """
        try:
            root = ET.fromstring(raw_content)
        except Exception:
            return []

        entries: List[Dict[str, str]] = []

        # 1. RSS 2.0 / 0.9x / 1.0 item extraction
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (
                item.findtext("pubDate")
                or item.findtext("date")
                or item.findtext("{http://purl.org/dc/elements/1.1/}date")
                or ""
            ).strip()
            summary = (
                item.findtext("description")
                or item.findtext("summary")
                or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                or ""
            ).strip()

            entries.append({
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
            })

        # 2. Atom entry extraction
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        atom_entries = root.findall(".//atom:entry", ns)
        if not atom_entries:
            atom_entries = [elem for elem in root.iter() if elem.tag.endswith("entry")]

        for item in atom_entries:
            # Title
            t_elem = item.find("atom:title", ns) if item.find("atom:title", ns) is not None else next((e for e in item if e.tag.endswith("title")), None)
            title = "".join(t_elem.itertext()).strip() if t_elem is not None else ""

            # Link
            l_elem = item.find("atom:link", ns) if item.find("atom:link", ns) is not None else next((e for e in item if e.tag.endswith("link")), None)
            link = ""
            if l_elem is not None:
                link = (l_elem.get("href") or "".join(l_elem.itertext())).strip()

            # Published / Updated
            p_elem = (
                item.find("atom:updated", ns)
                if item.find("atom:updated", ns) is not None
                else item.find("atom:published", ns)
                if item.find("atom:published", ns) is not None
                else next((e for e in item if e.tag.endswith("updated") or e.tag.endswith("published")), None)
            )
            published = "".join(p_elem.itertext()).strip() if p_elem is not None else ""

            # Summary / Content
            s_elem = (
                item.find("atom:summary", ns)
                if item.find("atom:summary", ns) is not None
                else item.find("atom:content", ns)
                if item.find("atom:content", ns) is not None
                else next((e for e in item if e.tag.endswith("summary") or e.tag.endswith("content")), None)
            )
            summary = "".join(s_elem.itertext()).strip() if s_elem is not None else ""

            entries.append({
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
            })

        return entries
