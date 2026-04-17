class TestCache:

    def test_enhance_cache_miss_then_hit(self, client):
        payload = {"code": "def cache_test_fn(): return 1", "language": "python", "variants": 1}
        r1 = client.post("/api/enhance", json=payload)
        r2 = client.post("/api/enhance", json=payload)
        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is True

    def test_complete_cache_miss_then_hit(self, client):
        payload = {"code": "def cache_complete_fn(): pass", "language": "python", "variants": 1}
        r1 = client.post("/api/complete", json=payload)
        r2 = client.post("/api/complete", json=payload)
        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is True

    def test_generate_cache_miss_then_hit(self, client):
        payload = {"prompt": "unique cache test prompt xyz", "languages": ["python"], "variants": 1}
        r1 = client.post("/api/generate", json=payload)
        r2 = client.post("/api/generate", json=payload)
        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is True

    def test_different_languages_different_cache_entries(self, client):
        payload_py = {"code": "def foo(): pass", "language": "python", "variants": 1}
        payload_go = {"code": "def foo(): pass", "language": "go", "variants": 1}
        r1 = client.post("/api/enhance", json=payload_py)
        r2 = client.post("/api/enhance", json=payload_go)
        # both should be cache misses — different languages = different keys
        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is False

    def test_different_tasks_different_cache_entries(self, client):
        code = "def isolated_task_test(): pass"
        r1 = client.post("/api/enhance", json={"code": code, "language": "python", "variants": 1})
        r2 = client.post("/api/complete", json={"code": code, "language": "python", "variants": 1})
        # enhance and complete are different tasks — should not share cache
        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is False

    def test_different_technology_different_cache_entries(self, client):
        code = "def tech_cache_test(): pass"
        r1 = client.post("/api/enhance", json={"code": code, "language": "python", "technology": "fastapi", "variants": 1})
        r2 = client.post("/api/enhance", json={"code": code, "language": "python", "technology": "django", "variants": 1})
        assert r1.json()["cached"] is False
        assert r2.json()["cached"] is False

    def test_cached_response_has_same_data(self, client):
        payload = {"code": "def same_data_test(): return 42", "language": "python", "variants": 1}
        r1 = client.post("/api/enhance", json=payload)
        r2 = client.post("/api/enhance", json=payload)
        d1 = r1.json()
        d2 = r2.json()
        assert d1["success"] == d2["success"]
        assert d1["task"] == d2["task"]
        assert d1["already_optimal"] == d2["already_optimal"]
        assert d1["data"] == d2["data"]
