class TestEnhance:

    def test_enhance_basic(self, client, enhance_basic):
        r = client.post("/api/enhance", json=enhance_basic)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["task"] == "enhance"
        assert "already_optimal" in data
        assert data["error"] is None

    def test_enhance_returns_variants(self, client, enhance_basic):
        r = client.post("/api/enhance", json=enhance_basic)
        data = r.json()
        assert data["success"] is True
        if not data["already_optimal"]:
            assert "variants" in data["data"]
            assert len(data["data"]["variants"]) >= 1
            variant = data["data"]["variants"][0]
            assert "title" in variant
            assert "description" in variant
            assert "code" in variant

    def test_enhance_with_technology(self, client, enhance_with_technology):
        r = client.post("/api/enhance", json=enhance_with_technology)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_enhance_with_context(self, client, enhance_with_context):
        r = client.post("/api/enhance", json=enhance_with_context)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_enhance_multi_variant(self, client, enhance_multi_variant):
        r = client.post("/api/enhance", json=enhance_multi_variant)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_enhance_cache_hit(self, client, enhance_basic):
        r1 = client.post("/api/enhance", json=enhance_basic)
        r2 = client.post("/api/enhance", json=enhance_basic)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["cached"] is True

    def test_enhance_missing_code(self, client):
        r = client.post("/api/enhance", json={"language": "python"})
        assert r.status_code == 422

    def test_enhance_missing_language(self, client):
        r = client.post("/api/enhance", json={"code": "def foo(): pass"})
        assert r.status_code == 422

    def test_enhance_empty_code(self, client):
        r = client.post("/api/enhance", json={"code": "", "language": "python"})
        assert r.status_code == 422

    def test_enhance_variants_out_of_range(self, client):
        r = client.post("/api/enhance", json={"code": "def foo(): pass", "language": "python", "variants": 10})
        assert r.status_code == 422

    def test_enhance_response_envelope(self, client, enhance_basic):
        r = client.post("/api/enhance", json=enhance_basic)
        data = r.json()
        assert "success" in data
        assert "error" in data
        assert "cached" in data
        assert "task" in data
        assert "already_optimal" in data
        assert "data" in data

    def test_enhance_token_usage(self, client, enhance_basic):
        r = client.post("/api/enhance", json=enhance_basic)
        data = r.json()
        if data["success"] and not data["already_optimal"]:
            usage = data["data"]["token_usage"]
            assert "prompt" in usage
            assert "completion" in usage
            assert "total" in usage
