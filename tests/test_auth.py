from fastapi.testclient import TestClient


def test_registrar_usuario(client: TestClient):
    resposta = client.post(
        "/auth/registrar", json={"email": "novo@exemplo.com", "senha": "senha12345"}
    )
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["email"] == "novo@exemplo.com"
    assert "senha" not in dados
    assert "senha_hash" not in dados


def test_registrar_email_duplicado(client: TestClient):
    client.post("/auth/registrar", json={"email": "dup@exemplo.com", "senha": "senha12345"})
    resposta = client.post(
        "/auth/registrar", json={"email": "dup@exemplo.com", "senha": "outrasenha"}
    )
    assert resposta.status_code == 400


def test_registrar_senha_curta_e_rejeitada(client: TestClient):
    resposta = client.post(
        "/auth/registrar", json={"email": "curta@exemplo.com", "senha": "123"}
    )
    assert resposta.status_code == 422


def test_login_com_sucesso(client: TestClient):
    client.post("/auth/registrar", json={"email": "login@exemplo.com", "senha": "senha12345"})
    resposta = client.post(
        "/auth/login", data={"username": "login@exemplo.com", "password": "senha12345"}
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert "access_token" in dados
    assert "refresh_token" in dados
    assert dados["token_type"] == "bearer"


def test_login_senha_errada(client: TestClient):
    client.post("/auth/registrar", json={"email": "senha@exemplo.com", "senha": "senha12345"})
    resposta = client.post(
        "/auth/login", data={"username": "senha@exemplo.com", "password": "senhaerrada"}
    )
    assert resposta.status_code == 401


def test_login_usuario_inexistente(client: TestClient):
    resposta = client.post(
        "/auth/login", data={"username": "naoexiste@exemplo.com", "password": "qualquer1"}
    )
    assert resposta.status_code == 401


def test_me_com_token_valido(client: TestClient, auth_headers: dict):
    resposta = client.get("/auth/me", headers=auth_headers)
    assert resposta.status_code == 200
    assert resposta.json()["email"] == "teste@exemplo.com"


def test_me_sem_token(client: TestClient):
    resposta = client.get("/auth/me")
    assert resposta.status_code == 401


def test_me_com_token_invalido(client: TestClient):
    resposta = client.get("/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert resposta.status_code == 401


def test_refresh_emite_novo_par_de_tokens(client: TestClient):
    client.post("/auth/registrar", json={"email": "refresh@exemplo.com", "senha": "senha12345"})
    login = client.post(
        "/auth/login", data={"username": "refresh@exemplo.com", "password": "senha12345"}
    )
    refresh_token_original = login.json()["refresh_token"]

    resposta = client.post("/auth/refresh", json={"refresh_token": refresh_token_original})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["refresh_token"] != refresh_token_original

    # o token novo funciona pra pegar um access token
    novo_access = dados["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {novo_access}"})
    assert me.status_code == 200


def test_refresh_token_usado_duas_vezes_e_rejeitado(client: TestClient):
    # simula reuso de um token ja rotacionado (ex: token vazado e usado por
    # duas partes diferentes)
    client.post("/auth/registrar", json={"email": "reuso@exemplo.com", "senha": "senha12345"})
    login = client.post(
        "/auth/login", data={"username": "reuso@exemplo.com", "password": "senha12345"}
    )
    token_original = login.json()["refresh_token"]

    primeira_vez = client.post("/auth/refresh", json={"refresh_token": token_original})
    assert primeira_vez.status_code == 200

    segunda_vez = client.post("/auth/refresh", json={"refresh_token": token_original})
    assert segunda_vez.status_code == 401


def test_refresh_token_invalido(client: TestClient):
    resposta = client.post("/auth/refresh", json={"refresh_token": "token-que-nao-existe"})
    assert resposta.status_code == 401


def test_logout_revoga_refresh_token(client: TestClient):
    client.post("/auth/registrar", json={"email": "logout@exemplo.com", "senha": "senha12345"})
    login = client.post(
        "/auth/login", data={"username": "logout@exemplo.com", "password": "senha12345"}
    )
    refresh_token = login.json()["refresh_token"]

    logout = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    tentativa_pos_logout = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert tentativa_pos_logout.status_code == 401
