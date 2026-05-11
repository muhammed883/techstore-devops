import socket
import sys
import threading
import time
from pathlib import Path

import pytest
from werkzeug.serving import make_server

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['cart'] = {}
        yield client


def _is_port_open(host='127.0.0.1', port=5000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope='session')
def live_server_url():
    host = '127.0.0.1'
    port = 5000
    url = f'http://{host}:{port}'

    if _is_port_open(host, port):
        yield url
        return

    server = make_server(host, port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(1)

    yield url

    server.shutdown()
    thread.join(timeout=5)
