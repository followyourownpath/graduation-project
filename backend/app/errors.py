from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge


def _error_response(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        return _error_response(
            "file_too_large",
            "The uploaded file exceeds the configured size limit.",
            413,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        code = (error.name or "http_error").lower().replace(" ", "_")
        return _error_response(code, error.description, error.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled application error", exc_info=error)
        return _error_response(
            "internal_server_error",
            "An unexpected error occurred.",
            500,
        )
