import os
import time
import pytest
from fastapi.testclient import TestClient
from api.middleware.rate_limit import rate_limiter

os.environ["ENVIRONMENT"] = "development"
os.environ["TESTING"] = "true"
os.environ["CACHE_PATH"] = "/tmp/test-cache-enhancer"

from api.main import app


@pytest.fixture(scope="session")
def client():
    time.sleep(0.5)
    test_client = TestClient(app)
    r = test_client.get("/ping")
    assert r.status_code == 200
    return test_client


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    with rate_limiter.lock:
        rate_limiter.requests.clear()
    # Clear cache between tests to prevent cross-test cache hits
    from api.dependencies import get_cache_service
    get_cache_service().clear()
    yield
    time.sleep(0.05)


# --- Enhance payloads ---

@pytest.fixture
def enhance_basic():
    return {"code": "def add(a, b):\n    return a", "language": "python", "variants": 1}

@pytest.fixture
def enhance_with_technology():
    return {"code": "def add(a, b):\n    return a", "language": "python", "technology": "fastapi", "variants": 1}

@pytest.fixture
def enhance_with_context():
    return {
        "code": "def add(a, b):\n    return a",
        "language": "python",
        "context": "# This is a math utilities module",
        "variants": 1,
    }

@pytest.fixture
def enhance_multi_variant():
    return {"code": "def add(a, b):\n    return a", "language": "python", "variants": 3}


# --- Complete payloads ---

@pytest.fixture
def complete_basic():
    return {"code": "def calculate(x, y):\n    pass", "language": "python", "variants": 1}

@pytest.fixture
def complete_with_context():
    return {
        "code": "def calculate(x, y):\n    pass",
        "language": "python",
        "context": "# Calculator module\nPI = 3.14159",
        "variants": 1,
    }


# --- Generate payloads ---

@pytest.fixture
def generate_single_language():
    return {"prompt": "Create a hello world function", "languages": ["python"], "variants": 1}

@pytest.fixture
def generate_multi_language():
    return {
        "prompt": "generate python and javascript code for a simple logger",
        "languages": ["python", "javascript"],
        "variants": 1,
    }

@pytest.fixture
def generate_with_technology():
    return {
        "prompt": "generate python code for JWT middleware",
        "languages": ["python"],
        "technology_per_language": {"python": "fastapi"},
        "variants": 1,
    }
