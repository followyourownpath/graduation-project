class MercuryError(Exception):
    """Base exception class for all Mercury CRM integration errors."""
    def __init__(self, message: str, code: str = "mercury_error"):
        super().__init__(message)
        self.code = code


class MercuryWriteBlockedError(MercuryError):
    """Raised when a POST/PUT request is blocked due to configuration safety switches."""
    def __init__(self, message: str):
        super().__init__(message, code="mercury_write_blocked")


class MercuryApiError(MercuryError):
    """Raised when Mercury CRM returns a non-2xx HTTP response."""
    def __init__(self, message: str, status_code: int, response_body: str = ""):
        super().__init__(f"Mercury API error ({status_code}): {message}", code="mercury_api_error")
        self.status_code = status_code
        self.response_body = response_body


class MercuryNetworkError(MercuryError):
    """Raised on connection timeout, DNS failure, or other network errors."""
    def __init__(self, message: str):
        super().__init__(f"Mercury network error: {message}", code="mercury_network_error")


class MercuryInvalidResponseError(MercuryError):
    """Raised when the Mercury API returns an unexpected or malformed response body."""
    def __init__(self, message: str):
        super().__init__(f"Mercury invalid response: {message}", code="mercury_invalid_response")
