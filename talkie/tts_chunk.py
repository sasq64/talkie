"""Utilities for chunking text for Text-to-Speech engines.

This module provides a function to split long-form text into chunks that are
appropriate for OpenAI-style Text-to-Speech (TTS) APIs. The implementation
prefers natural boundaries (paragraphs, sentence endings, newlines), then
falls back to punctuation and finally whitespace, and only slices mid-word as
an absolute last resort.

Usage:
    chunks = split_for_tts(long_text, max_chars=3000)

Notes:
- The default `max_chars` value aims to stay well within typical TTS input
  limits while keeping chunks reasonably large to minimize request overhead.
- The function does not modify content beyond trimming leading/trailing
  whitespace of each chunk.
"""

from __future__ import annotations

import re
from typing import Final

# Ordered breakpoint strategies, evaluated from strongest to weakest.
# Each entry is a compiled regex; the last match within the window is used.
_BREAK_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # Paragraph boundary: one or more blank lines
    re.compile(r"\n{2,}"),
    # Sentence end + optional closing quotes/brackets then whitespace/newline
    re.compile(r"(?<=[.!?])[\)\]\"'”’]*\s+"),
    # Sentence end at end-of-window (no trailing space available)
    re.compile(r"(?<=[.!?])[\)\]\"'”’]*(?=$)"),
    # Single newline
    re.compile(r"\n"),
    # Comma/semicolon followed by space
    re.compile(r"[;,]\s+"),
    # Any whitespace
    re.compile(r"\s+"),
)

_SENTENCE_BREAK: Final[re.Pattern[str]] = _BREAK_PATTERNS[1]


def _last_match_within(pattern: re.Pattern[str], s: str) -> int | None:
    """Return the end index of the last match of `pattern` within `s`.

    Args:
        pattern: Compiled regular expression
        s: The string window to search within

    Returns:
        The end index (relative to `s`) of the last match, or None if no match.
    """
    last_end: int | None = None
    for m in pattern.finditer(s):
        last_end = m.end()
    return last_end


def _choose_break(window: str) -> int | None:
    """Choose the best break position within `window` using priority rules.

    Returns the index where the chunk should end (exclusive). If None,
    no suitable breakpoint was found and caller may hard-split.
    """
    for pat in _BREAK_PATTERNS:
        idx = _last_match_within(pat, window)
        if idx is not None:
            return idx
    return None


def _coalesce_whitespace(s: str) -> str:
    """Trim leading/trailing whitespace from a chunk, preserving internal newlines."""
    # We avoid collapsing internal whitespace to keep the text natural for TTS.
    return s.strip()


def split_for_tts(text: str, *, max_chars: int = 3000) -> list[str]:
    """Split long-form `text` into TTS-friendly chunks.

    Strategy:
    - Prefer paragraph boundaries (blank lines) and sentence endings.
    - Then fall back to newlines, punctuation, and spaces.
    - As a last resort, split exactly at `max_chars`.

    Args:
        text: The input text to split.
        max_chars: Maximum characters per chunk (hard cap).

    Returns:
        List of non-empty chunks, each length <= `max_chars`.
    """
    if not text:
        return []
    if max_chars <= 0:
        return [text]

    n = len(text)
    i = 0
    out: list[str] = []

    while i < n:
        # If the remainder fits in one chunk, emit it and break.
        remaining = n - i
        if remaining <= max_chars:
            chunk = _coalesce_whitespace(text[i:n])
            if chunk:
                out.append(chunk)
            break

        # Consider window of size max_chars
        end = i + max_chars
        window = text[i:end]
        j = _choose_break(window)

        if j is None:
            # No soft break within limit; hard split at max_chars
            chunk = _coalesce_whitespace(window)
            if chunk:
                out.append(chunk)
            i = end
            continue

        # Soft break found; prefer snapping to the last sentence boundary
        snap = _last_match_within(_SENTENCE_BREAK, window[:j])
        if snap is not None:
            j = snap

        chunk = _coalesce_whitespace(window[:j])
        if chunk:
            out.append(chunk)

        # Advance to next position, skipping any whitespace already consumed
        i = i + j

    return out


__all__ = ["split_for_tts"]
