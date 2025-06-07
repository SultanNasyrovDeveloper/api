

def test_healthcheck(api_client):
    url = 'api/v1/healthcheck'
    response = api_client.get(url)
    assert response.json() == 'Ok'
