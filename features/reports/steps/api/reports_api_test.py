"""Reports API Tests — POST /v1/reports"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints

pytestmark = allure.feature("Reports")

ENDPOINT = APIEndpoints.REPORTS

VALID_PAYLOAD = {
    "subject":     "QA automated test report",
    "report_type": "BUG",
    "message":     "Automated test submission — please ignore.",
}


@pytest.mark.smoke
@pytest.mark.api
async def test_TC_RPT_001_submit_report_valid(reports_token):
    """TC-RPT-001 | Smoke | Submit valid report returns 201"""
    async with HonoAPIClient() as client:
        response = await client.post(
            ENDPOINT,
            json=VALID_PAYLOAD,
            headers={"Authorization": f"Bearer {reports_token}"},
        )
    SchemaValidator(response).status_in(200, 201)
    body = response.json()
    data = body.get("data", {})
    assert "id" in data or body.get("code") == "OK"


@pytest.mark.negative
@pytest.mark.api
async def test_TC_RPT_002_submit_report_no_token():
    """TC-RPT-002 | Security | Submit report without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(ENDPOINT, json=VALID_PAYLOAD)
    SchemaValidator(response).status(401)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_RPT_003_submit_report_invalid_type(reports_token):
    """TC-RPT-003 | Negative | Invalid report_type returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(
            ENDPOINT,
            json={
                "subject":     "Test",
                "report_type": "INVALID_TYPE",
                "message":     "Test message",
            },
            headers={"Authorization": f"Bearer {reports_token}"},
        )
    SchemaValidator(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_RPT_004_submit_report_missing_required_fields(reports_token):
    """TC-RPT-004 | Negative | Missing required fields returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(
            ENDPOINT,
            json={"subject": "Incomplete"},
            headers={"Authorization": f"Bearer {reports_token}"},
        )
    SchemaValidator(response).status_in(400, 422)
