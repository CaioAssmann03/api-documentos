import os

os.environ.setdefault("SECRET_KEY", "chave-de-teste-nao-usar-em-producao")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    # Banco em memoria, um novo por teste: StaticPool garante que a mesma
    # conexao seja reaproveitada (senao um banco em memoria sumiria entre
    # uma chamada e outra, cada uma abriria uma conexao/banco diferente).
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient):
    client.post("/auth/registrar", json={"email": "teste@exemplo.com", "senha": "senha12345"})
    resposta = client.post(
        "/auth/login", data={"username": "teste@exemplo.com", "password": "senha12345"}
    )
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
