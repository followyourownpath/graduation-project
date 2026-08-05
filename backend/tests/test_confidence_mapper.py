from app.normalization.confidence_mapper import get_span_confidence


def test_get_span_confidence_success():
    # Mock Azure layout result
    result = {
        "analyzeResult": {
            "content": "Employee Name: April Kidd",
            "pages": [
                {
                    "pageNumber": 1,
                    "words": [
                        {"content": "Employee", "span": {"offset": 0, "length": 8}, "confidence": 0.99},
                        {"content": "Name:", "span": {"offset": 9, "length": 5}, "confidence": 0.98},
                        {"content": "April", "span": {"offset": 15, "length": 5}, "confidence": 0.95},
                        {"content": "Kidd", "span": {"offset": 21, "length": 4}, "confidence": 0.85},
                    ]
                }
            ]
        }
    }

    # Match "April Kidd" which spans from index 15 to 25
    # Both "April" and "Kidd" should be included
    # Average of 0.95 and 0.85 is 0.90
    conf = get_span_confidence(result, 15, 25)
    assert conf == 0.90


def test_get_span_confidence_single_word():
    result = {
        "analyzeResult": {
            "pages": [
                {
                    "words": [
                        {"content": "April", "span": {"offset": 15, "length": 5}, "confidence": 0.95},
                    ]
                }
            ]
        }
    }
    conf = get_span_confidence(result, 15, 20)
    assert conf == 0.95


def test_get_span_confidence_no_overlap():
    result = {
        "analyzeResult": {
            "pages": [
                {
                    "words": [
                        {"content": "April", "span": {"offset": 15, "length": 5}, "confidence": 0.95},
                    ]
                }
            ]
        }
    }
    # Span [0, 10] has no overlap with [15, 20]
    conf = get_span_confidence(result, 0, 10, default_conf=0.77)
    assert conf == 0.77


def test_get_span_confidence_invalid_indices():
    result = {"analyzeResult": {"pages": []}}
    assert get_span_confidence(result, None, 10, default_conf=0.88) == 0.88
    assert get_span_confidence(result, 10, None, default_conf=0.88) == 0.88
    assert get_span_confidence(result, 15, 10, default_conf=0.88) == 0.88


def test_get_span_confidence_multiple_spans():
    # Some older or complex Azure formats return a list of spans under 'spans' instead of a single 'span'
    result = {
        "analyzeResult": {
            "pages": [
                {
                    "words": [
                        {"content": "Kidd", "spans": [{"offset": 21, "length": 4}], "confidence": 0.85},
                    ]
                }
            ]
        }
    }
    conf = get_span_confidence(result, 20, 26)
    assert conf == 0.85
