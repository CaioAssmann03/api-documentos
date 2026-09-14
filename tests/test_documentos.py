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


def test_criar_documento(client: TestClient):
    resposta = client.post(
        "/documentos",
        json={
            "titulo": "Manual de onboarding",
            "conteudo": "Bem-vindo a empresa.",
            "categoria": "manual",
        },
    )
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["titulo"] == "Manual de onboarding"
    assert dados["id"] is not None


def test_listar_documentos_vazio(client: TestClient):
    resposta = client.get("/documentos")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_obter_documento_inexistente(client: TestClient):
    resposta = client.get("/documentos/999")
    assert resposta.status_code == 404


def test_fluxo_completo_crud(client: TestClient):
    criar = client.post(
        "/documentos",
        json={
            "titulo": "Contrato de aluguel",
            "conteudo": "Texto do contrato " * 50,
            "categoria": "contrato",
        },
    )
    documento_id = criar.json()["id"]

    obter = client.get(f"/documentos/{documento_id}")
    assert obter.status_code == 200
    assert obter.json()["categoria"] == "contrato"

    atualizar = client.put(
        f"/documentos/{documento_id}", json={"categoria": "contrato-assinado"}
    )
    assert atualizar.status_code == 200
    assert atualizar.json()["categoria"] == "contrato-assinado"
    assert atualizar.json()["titulo"] == "Contrato de aluguel"  # não mudou, PATCH parcial

    estatisticas = client.get(f"/documentos/{documento_id}/estatisticas")
    assert estatisticas.status_code == 200
    assert estatisticas.json()["total_palavras"] == 150  # "Texto do contrato " x 50 = 3 palavras x 50

    remover = client.delete(f"/documentos/{documento_id}")
    assert remover.status_code == 204

    obter_apos_remocao = client.get(f"/documentos/{documento_id}")
    assert obter_apos_remocao.status_code == 404


def test_filtro_por_categoria(client: TestClient):
    client.post("/documentos", json={"titulo": "A", "conteudo": "x", "categoria": "nota"})
    client.post("/documentos", json={"titulo": "B", "conteudo": "y", "categoria": "manual"})

    resposta = client.get("/documentos", params={"categoria": "nota"})
    assert resposta.status_code == 200
    resultado = resposta.json()
    assert len(resultado) == 1
    assert resultado[0]["titulo"] == "A"


def test_busca_por_titulo(client: TestClient):
    client.post(
        "/documentos",
        json={"titulo": "Relatorio anual 2026", "conteudo": "x", "categoria": "relatorio"},
    )
    client.post("/documentos", json={"titulo": "Outra coisa", "conteudo": "y", "categoria": "nota"})

    resposta = client.get("/documentos", params={"busca": "anual"})
    assert resposta.status_code == 200
    resultado = resposta.json()
    assert len(resultado) == 1
    assert "anual" in resultado[0]["titulo"].lower()


def test_paginacao(client: TestClient):
    for i in range(5):
        client.post(
            "/documentos", json={"titulo": f"Doc {i}", "conteudo": "x", "categoria": "nota"}
        )

    pagina_1 = client.get("/documentos", params={"limite": 2, "offset": 0})
    pagina_2 = client.get("/documentos", params={"limite": 2, "offset": 2})

    assert len(pagina_1.json()) == 2
    assert len(pagina_2.json()) == 2
    assert pagina_1.json() != pagina_2.json()
