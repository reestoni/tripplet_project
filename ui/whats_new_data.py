# ui/whats_new_data.py
"""Qt-free part of "Fresh off the Spool" (ui/whats_new.py): version numbers and
dates, which versions a user has not seen, sections per version and the search
over all feature cards. Shared with the web app (tripplet_web); moved unchanged
2026-11-13 (unseen_versions/has_unseen take the user's "whats_new_seen" as an
optional argument). Data: ui/widgets/whats_new_texts.py."""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple

from ui.widgets import whats_new_texts as _texts
from ui.widgets.whats_new_texts import CURRENT_LABEL


def _rel(releases):
    """releases=None: the real list (ui/whats_new.py passes its own, tests replace it there)."""
    return _texts.RELEASES if releases is None else releases

# ── versions ─────────────────────────────────────────────────────────────
def release_version(release: Dict[str, Any]) -> str:
    v = str(release.get("version") or "")
    if v == "current":
        import app_meta
        return str(app_meta.APP_VERSION)
    return v


def current_release_id(releases: Optional[list] = None) -> Optional[str]:
    rel = _rel(releases)
    return release_version(rel[0]) if rel else None


def _date_text(iso: str, lang: str) -> str:
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return d.strftime("%d %b %Y") if lang == "en" else d.strftime("%d.%m.%Y" if lang == "de" else "%d/%m/%Y")


def _current_when(lang: str) -> str:
    """Date of the version being worked on: in the compiled exe the day the
    exe was built (the entry only gets its fixed date after the compile),
    from source "in progress"."""
    import os
    import sys
    if getattr(sys, "frozen", False):
        try:
            built = datetime.date.fromtimestamp(os.path.getmtime(sys.executable))
            return _date_text(built.isoformat(), lang)
        except OSError:
            return ""
    return CURRENT_LABEL[lang]


def release_when(release: Dict[str, Any], lang: str) -> str:
    return _date_text(release["date"], lang) if release.get("date") else _current_when(lang)


def unseen_versions(seen: Optional[str] = None, releases: Optional[list] = None) -> List[str]:
    """Versions newer than the one the user has seen (all if none seen).
    seen: "whats_new_seen" of the user; None = the desktop user (ui/display_prefs.py)."""
    if seen is None:
        from ui import display_prefs
        seen = display_prefs.current().get("whats_new_seen") or ""
    versions = [release_version(r) for r in _rel(releases)]
    return versions[:versions.index(seen)] if seen in versions else versions


def has_unseen(seen: Optional[str] = None, releases: Optional[list] = None) -> bool:
    return bool(_rel(releases)) and bool(unseen_versions(seen, releases))


def release_sections(release: Dict[str, Any], lang: str) -> List[Tuple[str, List[tuple]]]:
    """[(heading, blocks)] - one entry per ("h", …) heading; blocks before
    the first heading go into the first section (or an untitled one)."""
    sections: List[Tuple[str, List[tuple]]] = []
    lead: List[tuple] = []
    for block in release["texts"][lang]:
        if block[0] == "h":
            sections.append((str(block[1]), list(lead) if not sections else []))
            lead = []
        elif sections:
            sections[-1][1].append(block)
        else:
            lead.append(block)
    if lead:  # no heading at all
        sections.append(("", lead))
    return sections


# ── search ───────────────────────────────────────────────────────────────
def _search_index(releases: Optional[list] = None) -> List[Tuple[int, int, set, set]]:
    """(release idx, block idx, words, synonym concepts) per feature card;
    words of title, text and "where" in all languages together."""
    from ui.help_index import _phrase_concepts, concepts_of, normalize
    idx = []
    for ri, r in enumerate(_rel(releases)):
        for bi, block in enumerate(r["texts"]["en"]):
            if block[0] != "feature":
                continue
            norm = normalize(" ".join(" ".join(str(x) for x in blocks[bi][1:4])
                                      for blocks in r["texts"].values()))
            words = set(norm.split())
            concepts = set(_phrase_concepts(norm))
            for w in words:
                concepts |= concepts_of(w)
            idx.append((ri, bi, words, concepts))
    return idx


def search_features(query: str, releases: Optional[list] = None) -> List[Tuple[int, int]]:
    """Feature cards matching every search word, as (release idx, block idx),
    newest version first. A word matches literally (also as the start of a
    word, from 3 letters: "ref" -> "reference"), in any language, or via the
    synonyms of the help search."""
    from ui.help_index import _word_match, concepts_of, tokens
    toks = tokens(query)
    if not toks:
        return []
    terms = [(t, concepts_of(t)) for t in toks]
    hits = []
    for ri, bi, words, concepts in _search_index(releases):
        if all(bool(cons & concepts) or any(_word_match(t, w) or (len(t) >= 3 and w.startswith(t)) for w in words)
               for t, cons in terms):
            hits.append((ri, bi))
    return hits
