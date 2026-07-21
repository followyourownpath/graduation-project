from app.services.azure_document_intelligence import (
    AzureDocumentIntelligenceClient,
    DocumentIntelligenceError,
)


class Response:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


class Session:
    def __init__(self, post_response, get_responses=()):
        self.post_response = post_response
        self.get_responses = iter(get_responses)
        self.post_call = None

    def post(self, url, **kwargs):
        self.post_call = (url, kwargs)
        return self.post_response

    def get(self, _url, **_kwargs):
        return next(self.get_responses)


def client(session):
    return AzureDocumentIntelligenceClient(
        "https://example.test",
        "secret-key",
        "prebuilt-layout",
        "2024-11-30",
        poll_interval=0,
        session=session,
        sleep=lambda _seconds: None,
    )


def test_analyze_submits_and_polls_until_succeeded():
    result = {"status": "succeeded", "analyzeResult": {"content": "hello"}}
    session = Session(
        Response(202, headers={"Operation-Location": "https://operation.test/1"}),
        [Response(200, {"status": "running"}), Response(200, result)],
    )

    actual = client(session).analyze(b"%PDF-test", "application/pdf")

    assert actual == result
    assert session.post_call[1]["params"] == {"api-version": "2024-11-30"}
    assert session.post_call[1]["headers"]["Content-Type"] == "application/pdf"


def test_analyze_rejects_missing_operation_location():
    session = Session(Response(202))

    try:
        client(session).analyze(b"content", "application/pdf")
        raise AssertionError("expected DocumentIntelligenceError")
    except DocumentIntelligenceError as error:
        assert error.code == "azure_invalid_response"


def test_analyze_maps_rate_limit_without_leaking_response():
    session = Session(Response(429, {"error": {"message": "sensitive detail"}}))

    try:
        client(session).analyze(b"content", "application/pdf")
        raise AssertionError("expected DocumentIntelligenceError")
    except DocumentIntelligenceError as error:
        assert error.code == "azure_rate_limited"
        assert "sensitive detail" not in error.message


def test_analyze_maps_failed_operation():
    session = Session(
        Response(202, headers={"Operation-Location": "https://operation.test/1"}),
        [Response(200, {"status": "failed", "error": {"message": "private"}})],
    )

    try:
        client(session).analyze(b"content", "application/pdf")
        raise AssertionError("expected DocumentIntelligenceError")
    except DocumentIntelligenceError as error:
        assert error.code == "azure_analysis_failed"
        assert "private" not in error.message
