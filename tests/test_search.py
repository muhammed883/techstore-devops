import json


def test_search_existing_product(client):
    response = client.get('/api/search?q=samsung')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert any('Samsung' in product['name'] for product in data)


def test_search_missing_product(client):
    response = client.get('/api/search?q=doesnotexist')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data == []


def test_empty_search_returns_all_products(client):
    response = client.get('/api/search')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert len(data) == 8


def test_case_insensitive_search(client):
    response = client.get('/api/search?q=SaMsUnG')
    data = json.loads(response.data)

    assert any(product['name'] == 'Samsung Galaxy S24 Ultra' for product in data)


def test_search_page_renders_results(client):
    response = client.get('/search?q=laptop')

    assert response.status_code == 200
    assert b'MacBook' in response.data
