from app import create_app
from app.config import TestConfig


class Auth:
    def authenticate_staff(self, _token):
        return {"user": {"id": "u"}, "staff_profile": {"is_active": True, "role": "admin"}}


class Pipeline:
    def process(self, token, document_id):
        return {"job_id": "j", "document_id": document_id, "status": "completed", "pages": 1, "tables": 2, "cells": 10, "fields": 8}


def test_ocr_route_runs_pipeline():
    app = create_app(TestConfig, auth_service=Auth(), ocr_pipeline=Pipeline())
    response = app.test_client().post(
        "/api/v1/documents/123e4567-e89b-12d3-a456-426614174000/ocr",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "completed"


def test_ocr_route_rejects_invalid_uuid():
    app = create_app(TestConfig, auth_service=Auth(), ocr_pipeline=Pipeline())
    response = app.test_client().post(
        "/api/v1/documents/not-a-uuid/ocr",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 400
