import json


def _add_product(client, product_id=1, quantity=1):
    return client.post(
        '/api/cart/add',
        data=json.dumps({'product_id': product_id, 'quantity': quantity}),
        content_type='application/json'
    )


def test_add_to_cart(client):
    response = _add_product(client, 1)
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert data['cart_count'] == 1


def test_multiple_add_increments_cart_count(client):
    _add_product(client, 1)
    response = _add_product(client, 1)
    data = json.loads(response.data)

    assert data['cart_count'] == 2


def test_cart_count_with_multiple_products(client):
    _add_product(client, 1)
    _add_product(client, 2, quantity=2)

    response = client.get('/cart')

    assert response.status_code == 200
    assert b'Samsung' in response.data
    assert b'MacBook' in response.data


def test_invalid_product_add_returns_404(client):
    response = _add_product(client, 999999)
    data = json.loads(response.data)

    assert response.status_code == 404
    assert data['success'] is False


def test_legacy_cart_add_redirects_home(client):
    response = client.get('/cart/add/1')

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')
