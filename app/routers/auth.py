import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    RefreshRequest,
    TokenRefresh,
    TokenResponse,
    Usuario,
    UsuarioCreate,
    UsuarioRead,
    garantir_utc,
)
from app.security import (
    REFRESH_TOKEN_DIAS,
    criar_access_token,
    hash_senha,
    obter_usuario_atual,
    verificar_senha,
)

router = APIRouter(prefix="/auth", tags=["autenticacao"])


def _hash_refresh_token(token: str) -> str:
    # SHA-256, nao bcrypt: o refresh token ja' nasce aleatorio de alta
    # entropia (secrets.token_urlsafe), diferente de senha, que e' escolhida
    # por humano e precisa do custo computacional do bcrypt. Um hash rapido
    # ja' impede que quem tiver acesso de leitura ao banco use o token direto.
    return hashlib.sha256(token.encode()).hexdigest()


def _criar_refresh_token(usuario_id: int, session: Session) -> str:
    token = secrets.token_urlsafe(32)
    registro = TokenRefresh(
        usuario_id=usuario_id,
        token_hash=_hash_refresh_token(token),
        expira_em=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DIAS),
    )
    session.add(registro)
    session.commit()
    return token


@router.post("/registrar", response_model=UsuarioRead, status_code=201)
def registrar(dados: UsuarioCreate, session: Session = Depends(get_session)):
    existe = session.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    if existe:
        raise HTTPException(status_code=400, detail="E-mail ja cadastrado")

    usuario = Usuario(email=dados.email, senha_hash=hash_senha(dados.senha))
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)
):
    # OAuth2PasswordRequestForm usa "username"/"password" por convencao do
    # padrao OAuth2, mesmo o campo sendo um e-mail aqui.
    usuario = session.exec(select(Usuario).where(Usuario.email == form.username)).first()
    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    return TokenResponse(
        access_token=criar_access_token(usuario.id),
        refresh_token=_criar_refresh_token(usuario.id, session),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(dados: RefreshRequest, session: Session = Depends(get_session)):
    token_hash = _hash_refresh_token(dados.refresh_token)
    registro = session.exec(
        select(TokenRefresh).where(TokenRefresh.token_hash == token_hash)
    ).first()

    if not registro or registro.revogado:
        raise HTTPException(status_code=401, detail="Refresh token invalido")
    if garantir_utc(registro.expira_em) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expirado")

    # Rotaciona a cada uso: revoga o token antigo e emite um par novo. Se um
    # refresh token vazado for usado por um atacante, o dono legitimo tenta
    # usar o mesmo token depois, encontra ele ja revogado, e da' pra saber
    # que houve vazamento (em producao, isso dispararia um alerta).
    registro.revogado = True
    session.add(registro)
    session.commit()

    return TokenResponse(
        access_token=criar_access_token(registro.usuario_id),
        refresh_token=_criar_refresh_token(registro.usuario_id, session),
    )


@router.post("/logout", status_code=204)
def logout(dados: RefreshRequest, session: Session = Depends(get_session)):
    token_hash = _hash_refresh_token(dados.refresh_token)
    registro = session.exec(
        select(TokenRefresh).where(TokenRefresh.token_hash == token_hash)
    ).first()
    if registro:
        registro.revogado = True
        session.add(registro)
        session.commit()


@router.get("/me", response_model=UsuarioRead)
def me(usuario: Usuario = Depends(obter_usuario_atual)):
    return usuario
