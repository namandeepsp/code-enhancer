import time
import pytest
import concurrent.futures


class TestStability:

    def test_bad_inputs_dont_crash(self, client):
        bad_inputs = [
            {"language": "python"},
            {"code": "def foo(): pass"},
            {},
            {"code": None, "language": "python"},
            {"code": "def foo(): pass", "language": None},
            {"code": 12345, "language": "python"},
            {"code": "", "language": ""},
            {"code": "def foo(): pass", "language": "python", "variants": 0},
            {"code": "def foo(): pass", "language": "python", "variants": 99},
        ]
        for i, payload in enumerate(bad_inputs):
            r = client.post("/api/enhance", json=payload)
            assert r.status_code in (200, 400, 422), f"Input {i} crashed with {r.status_code}"
            if r.status_code == 200:
                assert "success" in r.json()

    def test_large_code_handled_gracefully(self, client):
        large_code = "def test():\n    pass\n" * 5000
        r = client.post("/api/enhance", json={"code": large_code, "language": "python", "variants": 1})
        assert r.status_code in (200, 413, 422)

    def test_unicode_code(self, client):
        r = client.post("/api/enhance", json={
            "code": "def greet():\n    print('héllo wörld 🌍')",
            "language": "python",
            "variants": 1,
        })
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_recovery_after_bad_inputs(self, client):
        # send bad inputs
        for _ in range(3):
            client.post("/api/enhance", json={"language": "python"})

        # service should still handle valid requests
        time.sleep(0.3)
        r = client.post("/api/enhance", json={"code": "def foo(): return 1", "language": "python", "variants": 1})
        assert r.status_code == 200
        assert r.json()["success"] is True

    @pytest.mark.slow
    def test_concurrent_requests(self, client):
        def make_request(i):
            try:
                r = client.post("/api/enhance", json={
                    "code": f"def concurrent_{i}(): pass",
                    "language": "python",
                    "variants": 1,
                })
                return r.status_code == 200
            except Exception:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request, i) for i in range(6)]
            results = [f.result() for f in futures]

        success_rate = sum(results) / len(results)
        assert success_rate >= 0.5, f"Success rate too low: {success_rate:.0%}"

    @pytest.mark.slow
    def test_memory_stability(self, client):
        memory_readings = []
        for i in range(10):
            client.post("/api/enhance", json={
                "code": f"def mem_test_{i}(): pass",
                "language": "python",
                "variants": 1,
            })
            if i % 3 == 0:
                r = client.get("/metrics")
                if r.status_code == 200:
                    memory_readings.append(r.json().get("memory_mb", 0))
            time.sleep(0.1)

        if len(memory_readings) >= 2:
            growth = memory_readings[-1] - memory_readings[0]
            assert growth < 100, f"Memory grew by {growth:.1f}MB"

    def test_mixed_endpoints(self, client):
        requests = [
            ("POST", "/api/enhance", {"code": "def foo(): pass", "language": "python", "variants": 1}),
            ("POST", "/api/complete", {"code": "def bar(): pass", "language": "python", "variants": 1}),
            ("POST", "/api/generate", {"prompt": "generate python code for a logger", "languages": ["python"], "variants": 1}),
            ("GET",  "/api/languages", None),
            ("GET",  "/health", None),
        ]
        for method, path, payload in requests:
            if method == "POST":
                r = client.post(path, json=payload)
            else:
                r = client.get(path)
            assert r.status_code in (200, 503), f"{path} returned {r.status_code}"
            time.sleep(0.1)
