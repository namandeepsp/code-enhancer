import time


class TestRateLimit:

    def test_rate_limit_triggers(self, client):
        responses = []
        for i in range(60):
            r = client.post("/api/enhance", json={
                "code": f"def rate_test_{i}(): pass",
                "language": "python",
                "variants": 1,
            })
            responses.append(r.status_code)
            time.sleep(0.02)

        assert any(s == 429 for s in responses), "Rate limit never triggered"

    def test_rate_limit_response_shape(self, client):
        for i in range(60):
            r = client.post("/api/enhance", json={
                "code": f"def shape_test_{i}(): pass",
                "language": "python",
                "variants": 1,
            })
            if r.status_code == 429:
                data = r.json()
                assert data["success"] is False
                assert "error" in data
                break

    def test_non_api_routes_not_rate_limited(self, client):
        # /ping and /health should never be rate limited in testing mode
        for _ in range(20):
            r = client.get("/ping")
            assert r.status_code == 200
