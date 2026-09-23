from fastapi.testclient import TestClient


def test_criar_documento(client: TestClient, auth_headers: dict):
    resposta = client.post(
        "/documentos",
        json={
            "titulo": "Manual de onboarding",
            "conteudo": "Bem-vindo a empresa.",
            "categoria": "manual",
        },
        headers=auth_headers,
    )
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["titulo"] == "Manual de onboarding"
    assert dados["id"] is not None


def test_criar_documento_sem_token(client: TestClient):
    resposta = client.post(
        "/documentos",
        json={"titulo": "X", "conteudo": "y", "categoria": "nota"},
    )
    assert resposta.status_code == 401


def test_listar_documentos_vazio(client: TestClient, auth_headers: dict):
    resposta = client.get("/documentos", headers=auth_headers)
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_obter_documento_inexistente(client: TestClient, auth_headers: dict):
    resposta = client.get("/documentos/999", headers=auth_headers)
    assert resposta.status_code == 404


def test_fluxo_completo_crud(client: TestClient, auth_headers: dict):
    criar = client.post(
        "/documentos",
        json={
            "titulo": "Contrato de aluguel",
            "conteudo": "Texto do contrato " * 50,
            "categoria": "contrato",
        },
        headers=auth_headers,
    )
    documento_id = criar.json()["id"]

    obter = client.get(f"/documentos/{documento_id}", headers=auth_headers)
    assert obter.status_code == 200
    assert obter.json()["categoria"] == "contrato"

    atualizar = client.put(
        f"/documentos/{documento_id}",
        json={"categoria": "contrato-assinado"},
        headers=auth_headers,
    )
    assert atualizar.status_code == 200
    assert atualizar.json()["categoria"] == "contrato-assinado"
    assert atualizar.json()["titulo"] == "Contrato de aluguel"  # não mudou, PATCH parcial

    estatisticas = client.get(
        f"/documentos/{documento_id}/estatisticas", headers=auth_headers
    )
    assert estatisticas.status_code == 200
    assert estatisticas.json()["total_palavras"] == 150  # "Texto do contrato " x 50 = 3 palavras x 50

    remover = client.delete(f"/documentos/{documento_id}", headers=auth_headers)
    assert remover.status_code == 204

    obter_apos_remocao = client.get(f"/documentos/{documento_id}", headers=auth_headers)
    assert obter_apos_remocao.status_code == 404


def test_filtro_por_categoria(client: TestClient, auth_headers: dict):
    client.post(
        "/documentos",
        json={"titulo": "A", "conteudo": "x", "categoria": "nota"},
        headers=auth_headers,
    )
    client.post(
        "/documentos",
        json={"titulo": "B", "conteudo": "y", "categoria": "manual"},
        headers=auth_headers,
    )

    resposta = client.get("/documentos", params={"categoria": "nota"}, headers=auth_headers)
    assert resposta.status_code == 200
    resultado = resposta.json()
    assert len(resultado) == 1
    assert resultado[0]["titulo"] == "A"


def test_busca_por_titulo(client: TestClient, auth_headers: dict):
    client.post(
        "/documentos",
        json={"titulo": "Relatorio anual 2026", "conteudo": "x", "categoria": "relatorio"},
        headers=auth_headers,
    )
    client.post(
        "/documentos",
        json={"titulo": "Outra coisa", "conteudo": "y", "categoria": "nota"},
        headers=auth_headers,
    )

    resposta = client.get("/documentos", params={"busca": "anual"}, headers=auth_headers)
    assert resposta.status_code == 200
    resultado = resposta.json()
    assert len(resultado) == 1
    assert "anual" in resultado[0]["titulo"].lower()


def test_paginacao(client: TestClient, auth_headers: dict):
    for i in range(5):
        client.post(
            "/documentos",
            json={"titulo": f"Doc {i}", "conteudo": "x", "categoria": "nota"},
            headers=auth_headers,
        )

    pagina_1 = client.get("/documentos", params={"limite": 2, "offset": 0}, headers=auth_headers)
    pagina_2 = client.get("/documentos", params={"limite": 2, "offset": 2}, headers=auth_headers)

    assert len(pagina_1.json()) == 2
    assert len(pagina_2.json()) == 2
    assert pagina_1.json() != pagina_2.json()


def test_documento_isolado_por_usuario(client: TestClient, auth_headers: dict):
    # Segundo usuario, token proprio
    client.post("/auth/registrar", json={"email": "outra@exemplo.com", "senha": "outrasenha1"})
    login_outra = client.post(
        "/auth/login", data={"username": "outra@exemplo.com", "password": "outrasenha1"}
    )
    headers_outra = {"Authorization": f"Bearer {login_outra.json()['access_token']}"}

    criar = client.post(
        "/documentos",
        json={"titulo": "Privado", "conteudo": "x", "categoria": "nota"},
        headers=auth_headers,
    )
    documento_id = criar.json()["id"]

    # a outra usuaria nao enxerga o documento nem na listagem, nem por id direto
    listagem_outra = client.get("/documentos", headers=headers_outra)
    assert listagem_outra.json() == []

    obter_outra = client.get(f"/documentos/{documento_id}", headers=headers_outra)
    assert obter_outra.status_code == 404
