class TestComplete:

    def test_complete_basic(self, client, complete_basic):
        r = client.post("/api/complete", json=complete_basic)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["task"] == "complete"
        assert data["error"] is None

    def test_complete_returns_variants(self, client, complete_basic):
        r = client.post("/api/complete", json=complete_basic)
        data = r.json()
        assert data["success"] is True
        if not data["already_optimal"]:
            assert "variants" in data["data"]
            variant = data["data"]["variants"][0]
            assert "title" in variant
            assert "description" in variant
            assert "code" in variant

    def test_complete_with_context(self, client, complete_with_context):
        r = client.post("/api/complete", json=complete_with_context)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_complete_cache_hit(self, client, complete_basic):
        r1 = client.post("/api/complete", json=complete_basic)
        r2 = client.post("/api/complete", json=complete_basic)
        assert r2.json()["cached"] is True

    def test_complete_missing_code(self, client):
        r = client.post("/api/complete", json={"language": "python"})
        assert r.status_code == 422

    def test_complete_missing_language(self, client):
        r = client.post("/api/complete", json={"code": "def foo(): pass"})
        assert r.status_code == 422

    def test_complete_empty_code(self, client):
        r = client.post("/api/complete", json={"code": "", "language": "python"})
        assert r.status_code == 422

    def test_complete_response_envelope(self, client, complete_basic):
        r = client.post("/api/complete", json=complete_basic)
        data = r.json()
        assert "success" in data
        assert "error" in data
        assert "cached" in data
        assert "task" in data
        assert "already_optimal" in data
        assert "data" in data

    def test_complete_token_usage(self, client, complete_basic):
        r = client.post("/api/complete", json=complete_basic)
        data = r.json()
        if data["success"] and not data["already_optimal"]:
            usage = data["data"]["token_usage"]
            assert "prompt" in usage
            assert "completion" in usage
            assert "total" in usage
