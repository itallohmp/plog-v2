import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.routes.flows import get_flow_service
from app.repositories.flow_repository import FlowRepository
from app.services.flow_service import FlowService
from main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_events() -> List[Dict[str, Any]]:
    return json.loads((FIXTURES_DIR / "sample_flows.json").read_text(encoding="utf-8"))


@pytest.fixture
def mock_repository(sample_events: List[Dict[str, Any]]) -> MagicMock:
    repo = MagicMock(spec=FlowRepository)
    repo.fetch_raw_flows.return_value = sample_events
    return repo


@pytest.fixture
def flow_service(mock_repository: MagicMock) -> FlowService:
    return FlowService(mock_repository)


@pytest.fixture
def client(mock_repository: MagicMock):
    def override_service() -> FlowService:
        return FlowService(mock_repository)

    app.dependency_overrides[get_flow_service] = override_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
