import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.database import get_session
from app.models import Usuario

load_dotenv()

# Falha alto e cedo se faltar: uma API de autenticacao sem SECRET_KEY nao
# tem como funcionar com seguranca, entao nao faz sentido ter um valor
# padrao "soh pra nao quebrar".
SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTOS = 30
REFRESH_TOKEN_DIAS = 7

# tokenUrl aponta pro endpoint de login (registrado em routers/auth.py). E'
# o que faz o Swagger mostrar o botao "Authorize" e anexar o Bearer token
# sozinho nas chamadas de "Try it out" depois do login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hash_armazenado.encode())


def criar_access_token(usuario_id: int) -> str:
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTOS)
    payload = {"sub": str(usuario_id), "exp": expira_em, "tipo": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")


def obter_usuario_atual(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> Usuario:
    payload = decodificar_token(token)
    if payload.get("tipo") != "access":
        raise HTTPException(status_code=401, detail="Tipo de token incorreto")

    usuario = session.get(Usuario, int(payload["sub"]))
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return usuario
