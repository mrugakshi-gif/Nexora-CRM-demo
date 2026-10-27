"""
Test CORS preflight and actual request handling for Nexora CRM demo backend.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_cors_preflight_production_vercel_origin():
    """Verify that OPTIONS preflight from the exact deployed Vercel domain succeeds with 200."""
    response = client.options(
        "/api/analytics/dashboard",
        headers={
            "Origin": "https://nexora-crm-demo-u4fy.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://nexora-crm-demo-u4fy.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")

def test_cors_preflight_vercel_preview_origin():
    """Verify that OPTIONS preflight from a Vercel preview deployment for this project succeeds via regex."""
    response = client.options(
        "/api/companies",
        headers={
            "Origin": "https://nexora-crm-demo-git-main-mrugakshis-projects.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://nexora-crm-demo-git-main-mrugakshis-projects.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_preflight_localhost_origin():
    """Verify that local development origins remain allowed."""
    response = client.options(
        "/api/auth/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_preflight_unauthorized_origin_rejected():
    """Verify that an unauthorized random origin is rejected with 400 Disallowed CORS origin."""
    response = client.options(
        "/api/analytics/dashboard",
        headers={
            "Origin": "https://evil-attacker-site.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 400
    assert "Disallowed CORS origin" in response.text
    assert "access-control-allow-origin" not in response.headers
