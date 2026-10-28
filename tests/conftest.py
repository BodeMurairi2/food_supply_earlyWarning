import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="session")
def api_client():
    with TestClient(app) as c:  # runs the lifespan, so the models load once
        yield c
