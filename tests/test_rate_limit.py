def test_login_rate_limited_after_burst(client):
    for _ in range(10):
        client.post("/auth/login", json={"email": "nobody@example.com", "password": "x"})
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert r.status_code == 429
