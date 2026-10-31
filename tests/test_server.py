import threading
import httpx
from maintainerops.server.app import start_server


def test_server_rest_api():
    # Bind to port 0 to let OS pick an available ephemeral port
    httpd = start_server(host="127.0.0.1", port=0)
    actual_port = httpd.server_address[1]

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{actual_port}"

    try:
        with httpx.Client(base_url=base_url) as client:
            # 1. Root dashboard HTML
            r_root = client.get("/")
            assert r_root.status_code == 200
            assert "MaintainerOps" in r_root.text

            # 2. Health endpoint
            r_health = client.get("/api/health")
            assert r_health.status_code == 200
            data = r_health.json()
            assert data["status"] == "healthy"

            # 3. Fixtures endpoint
            r_fixtures = client.get("/api/fixtures")
            assert r_fixtures.status_code == 200
            fixtures = r_fixtures.json()["fixtures"]
            assert any(f["name"] == "sample_repo" for f in fixtures)

            # 4. Report endpoint with fixture target
            r_report = client.get("/api/report?target=tests/fixtures/sample_repo.json")
            assert r_report.status_code == 200
            report = r_report.json()
            assert report["repository"] == "maintainerops/sample-repo"
            assert "metrics" in report
            assert "findings" in report

            # 5. POST /api/action to record triage decision
            r_action = client.post(
                "/api/action",
                json={
                    "action": "approve_draft",
                    "item_number": 101,
                    "finding_id": "test_id",
                    "note": "Approved by maintainer",
                },
            )
            assert r_action.status_code == 200
            assert r_action.json()["status"] == "success"

            # 6. GET /api/actions
            r_actions = client.get("/api/actions")
            assert r_actions.status_code == 200
            assert len(r_actions.json()["actions"]) >= 1

            # 7. POST /api/scan with custom simulation config
            r_scan = client.post(
                "/api/scan",
                json={
                    "target": "tests/fixtures/sample_repo.json",
                    "config": {
                        "similarity_threshold": 0.4,
                        "min_body_length": 30,
                    },
                },
            )
            assert r_scan.status_code == 200
            assert r_scan.json()["repository"] == "maintainerops/sample-repo"

    finally:
        httpd.shutdown()
        httpd.server_close()
