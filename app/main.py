from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import criar_banco
from app.routers import auth, documentos


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_banco()
    yield


app = FastAPI(
    title="API de Documentos",
    description=(
        "CRUD de documentos autenticado por usuário, com JWT (access token curto "
        "+ refresh token revogável)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(documentos.router)
