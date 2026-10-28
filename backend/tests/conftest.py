import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-1234"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["SEED_DEMO"] = "false"
os.environ["DEMO_MODE"] = "true"
os.environ["AI_PROVIDER"] = "demo"
os.environ["SENDING_ENABLED"] = "false"
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["LOGIN_RATE_LIMIT"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.config import get_settings  # noqa: E402
from app.core.security import login_limiter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.seed import PASSWORD, seed  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

EXAMPLE = ("Hello, I am looking for a 3 BHK apartment in Jaipur under ₹80 lakh. I prefer a location near schools "
           "and would like to move within two months.")


@pytest.fixture(autouse=True)
def fresh_db():
    get_settings.cache_clear()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    login_limiter.reset()
    with SessionLocal() as db:
        seed(db)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def login(client, who="admin"):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@demo.com", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return login(client, "admin")


@pytest.fixture
def agent(client):
    return login(client, "agent")


@pytest.fixture
def analyst(client):
    return login(client, "analyst")


@pytest.fixture
def manager(client):
    return login(client, "manager")


def import_example(client, headers, email="priya@example.com", body=EXAMPLE, subject="Property enquiry", **kw):
    return client.post("/api/v1/emails/import", headers=headers, json={"sender_email": email, "sender_name": kw.get("name", "Priya Sharma"),
                                                                       "subject": subject, "body": body, "process": kw.get("process", True)})
