import json


def test_health_returns_healthy_status(client):
    response = client.get('/health')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'techstore'


def test_metrics_returns_prometheus_text(client):
    client.get('/')
    response = client.get('/metrics')

    assert response.status_code == 200
    assert b'http_requests_total' in response.data
    assert response.content_type.startswith('text/plain')


def test_missing_product_returns_404(client):
    response = client.get('/product/999999')

    assert response.status_code == 404


def test_unknown_route_returns_404(client):
    response = client.get('/not-a-real-page')

    assert response.status_code == 404
