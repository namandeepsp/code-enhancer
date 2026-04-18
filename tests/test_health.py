import time


class TestHealth:

    def test_ping(self, client):
        r = client.get("/ping")
        assert r.status_code == 200
        assert r.text == "pong"

    def test_ping_response_time(self, client):
        start = time.time()
        r = client.get("/ping")
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 0.1

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code in (200, 503)
        data = r.json()
        assert data["status"] in ("healthy", "degraded", "warning")
        assert "timestamp" in data
        assert "memory_usage_mb" in data
        assert "ai" in data

    def test_health_ai_field(self, client):
        r = client.get("/health")
        data = r.json()
        assert "available" in data["ai"]

    def test_metrics(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "memory_mb" in data
        assert "cpu_percent" in data
        assert "uptime_seconds" in data
        assert data["memory_mb"] > 0
        assert data["uptime_seconds"] >= 0

    def test_languages(self, client):
        r = client.get("/api/languages")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "languages" in data["data"]
        langs = data["data"]["languages"]
        assert isinstance(langs, list)
        assert len(langs) > 0
        assert "fastapi" in langs
        assert "django" in langs
        assert "react" in langs

    def test_enhancer_health(self, client):
        r = client.get("/api/health")
        assert r.status_code in (200, 503)
        data = r.json()
        assert data["service"] == "enhancer"
        assert data["status"] in ("healthy", "degraded")
        assert "ai_available" in data
