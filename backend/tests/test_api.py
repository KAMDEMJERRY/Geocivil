from copy import deepcopy

from .conftest import PROJECT, signup


def test_auth_flow(client):
    h = signup(client)
    assert client.get("/auth/me", headers=h).json()["email"] == "a@test.cm"
    assert client.post("/auth/register", json={"email": "A@test.cm", "password": "motdepasse1"}).status_code == 409
    assert client.post("/auth/login", json={"email": "a@test.cm", "password": "mauvais123"}).status_code == 401
    assert client.post("/auth/login", json={"email": "a@test.cm", "password": "motdepasse1"}).status_code == 200
    assert client.get("/auth/me").status_code == 401


def test_weak_password_rejected(client):
    assert client.post("/auth/register", json={"email": "b@test.cm", "password": "court"}).status_code == 422


def test_project_crud_and_isolation(client):
    a, b = signup(client), signup(client, "b@test.cm")
    r = client.post("/projects", json=PROJECT, headers=a)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.get(f"/projects/{pid}", headers=b).status_code == 404
    assert len(client.get("/projects", headers=b).json()) == 0
    upd = deepcopy(PROJECT)
    upd["building"]["floors"] = 2
    assert client.put(f"/projects/{pid}", json=upd, headers=a).json()["building"]["floors"] == 2
    assert client.delete(f"/projects/{pid}", headers=a).status_code == 204
    assert client.get(f"/projects/{pid}", headers=a).status_code == 404


def test_phase1_validation(client):
    h = signup(client)
    bad = deepcopy(PROJECT)
    bad["building"]["floors"] = 3
    assert client.post("/projects", json=bad, headers=h).status_code == 422
    bad = deepcopy(PROJECT)
    bad["building_type"] = "hangar"
    assert client.post("/projects", json=bad, headers=h).status_code == 422


def test_prices_layers(client):
    u, adm = signup(client), signup(client, "admin@test.cm")
    p = {x["key"]: x for x in client.get("/prices?city=Douala", headers=u).json()}
    assert p["ciment"]["source"] == "default" and p["ciment"]["value"] == 6500
    assert client.put("/admin/prices", json={"key": "ciment", "city": "Douala", "value": 7000}, headers=u).status_code == 403
    assert client.put("/admin/prices", json={"key": "ciment", "city": "Douala", "value": 7000}, headers=adm).status_code == 200
    p = {x["key"]: x for x in client.get("/prices?city=douala", headers=u).json()}
    assert p["ciment"]["source"] == "city" and p["ciment"]["value"] == 7000
    client.put("/prices/overrides", json={"key": "ciment", "value": 6800}, headers=u)
    p = {x["key"]: x for x in client.get("/prices?city=Douala", headers=u).json()}
    assert p["ciment"]["source"] == "user" and p["ciment"]["value"] == 6800
    other = {x["key"]: x for x in client.get("/prices?city=Douala", headers=adm).json()}
    assert other["ciment"]["value"] == 7000
    client.delete("/prices/overrides/ciment", headers=u)
    assert client.get("/prices?city=Douala", headers=u).json()[0]["source"] in ("city", "default")


def test_analysis_endpoint(client):
    h = signup(client)
    pid = client.post("/projects", json=PROJECT, headers=h).json()["id"]
    assert client.get(f"/projects/{pid}/analysis", headers=h).status_code == 404
    r = client.post(f"/projects/{pid}/analysis", headers=h)
    assert r.status_code == 200 and r.json()["toutes_verifications_ok"]
    assert client.get(f"/projects/{pid}/analysis", headers=h).json()["norme"].startswith("BAEL")
    other = signup(client, "c@test.cm")
    assert client.post(f"/projects/{pid}/analysis", headers=other).status_code == 404
