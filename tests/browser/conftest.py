"""Runs the real app on a local port for Playwright. API calls are faked in each test with page.route."""
import socket
import threading
import time

import pytest
import uvicorn


@pytest.fixture(scope="session")
def server_url(tmp_path_factory):
    import os
    os.environ.pop("OPENROUTER_API_KEY", None)
    os.environ["STORAGE_DIR"] = str(tmp_path_factory.mktemp("generated"))
    from app.main import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)
