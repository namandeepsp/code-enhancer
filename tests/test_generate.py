class TestGenerate:

    def test_generate_single_language(self, client, generate_single_language):
        r = client.post("/api/generate", json=generate_single_language)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["task"] == "generate"
        assert data["error"] is None

    def test_generate_returns_language_entries(self, client, generate_single_language):
        r = client.post("/api/generate", json=generate_single_language)
        data = r.json()
        assert data["success"] is True
        languages = data["data"]["languages"]
        assert "python" in languages
        entry = languages["python"]
        assert "title" in entry
        assert "description" in entry
        assert "code" in entry

    def test_generate_multi_language(self, client, generate_multi_language):
        r = client.post("/api/generate", json=generate_multi_language)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        languages = data["data"]["languages"]
        assert len(languages) >= 1

    def test_generate_with_technology(self, client, generate_with_technology):
        r = client.post("/api/generate", json=generate_with_technology)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_generate_cache_hit(self, client, generate_single_language):
        r1 = client.post("/api/generate", json=generate_single_language)
        r2 = client.post("/api/generate", json=generate_single_language)
        assert r2.json()["cached"] is True

    def test_generate_missing_prompt(self, client):
        r = client.post("/api/generate", json={"languages": ["python"]})
        assert r.status_code == 422

    def test_generate_missing_languages(self, client):
        r = client.post("/api/generate", json={"prompt": "hello world"})
        assert r.status_code == 422

    def test_generate_empty_prompt(self, client):
        r = client.post("/api/generate", json={"prompt": "", "languages": ["python"]})
        assert r.status_code == 422

    def test_generate_empty_languages(self, client):
        r = client.post("/api/generate", json={"prompt": "hello world", "languages": []})
        assert r.status_code == 422

    def test_generate_response_envelope(self, client, generate_single_language):
        r = client.post("/api/generate", json=generate_single_language)
        data = r.json()
        assert "success" in data
        assert "error" in data
        assert "cached" in data
        assert "task" in data
        assert "data" in data

    def test_generate_token_usage(self, client, generate_single_language):
        r = client.post("/api/generate", json=generate_single_language)
        data = r.json()
        if data["success"]:
            usage = data["data"]["token_usage"]
            assert "prompt" in usage
            assert "completion" in usage
            assert "total" in usage
