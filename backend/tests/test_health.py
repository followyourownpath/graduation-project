def test_root_health_check(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json() == {
        "service": "smartfinn-backend",
        "status": "ok",
    }


def test_versioned_health_check_reports_unconfigured_integrations(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "service": "smartfinn-backend",
        "status": "ok",
        "integrations_configured": {
            "supabase": False,
            "azure_document_intelligence": False,
        },
    }


def test_unknown_route_uses_standard_error_shape(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
