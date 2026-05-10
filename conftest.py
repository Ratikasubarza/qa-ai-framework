import pytest

@pytest.fixture(scope="session")
def base_url() -> str:
    return "https://app-dev.thehono.com"
