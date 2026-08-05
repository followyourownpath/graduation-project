"""Helper module to map text regex offsets to Azure Word objects and compute average confidence."""

from __future__ import annotations


def get_span_confidence(
    result: dict,
    start_index: int | None,
    end_index: int | None,
    default_conf: float = 0.90,
) -> float:
    """Calculate the average confidence score of words within a character span.

    If start_index/end_index is None, or if the layout words list is missing,
    returns default_conf.
    """
    if start_index is None or end_index is None or start_index >= end_index:
        return default_conf

    analysis = result.get("analyzeResult") or {}
    pages = analysis.get("pages") or []

    confidences = []
    for page in pages:
        words = page.get("words") or []
        for word in words:
            span = word.get("span")
            spans = word.get("spans") or ([span] if span else [])

            for s in spans:
                offset = s.get("offset")
                length = s.get("length")
                if offset is not None and length is not None:
                    # Check for overlap between [offset, offset + length] and [start_index, end_index]
                    w_start = offset
                    w_end = offset + length
                    if w_start < end_index and w_end > start_index:
                        confidence = word.get("confidence")
                        if confidence is not None:
                            confidences.append(confidence)
                            break  # Only count this word once

    if not confidences:
        return default_conf

    return round(sum(confidences) / len(confidences), 4)
