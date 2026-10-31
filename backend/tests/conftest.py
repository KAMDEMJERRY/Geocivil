import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ADMIN_EMAIL"] = "admin@test.cm"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.state.limiter.enabled = False
    with TestClient(app) as c:
        yield c


def signup(client, email="a@test.cm"):
    r = client.post("/auth/register", json={"email": email, "password": "motdepasse1"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


PROJECT = {
    "name": "Villa test", "city": "Yaoundé", "building_type": "maison",
    "soil": {"soil_type": "laterite", "bearing_capacity_kpa": 200, "water_table_depth_m": 3},
    "building": {"footprint_m2": 120, "floors": 1},
}
