import requests


def test_health_smoke(live_server_url):
    response = requests.get(f'{live_server_url}/health', timeout=5)

    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'


def test_homepage_smoke(live_server_url):
    response = requests.get(live_server_url, timeout=5)

    assert response.status_code == 200
    assert 'TechStore' in response.text
