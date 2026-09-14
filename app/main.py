from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, select

from app.database import criar_banco, get_session
from app.models import (
    Documento,
    DocumentoCreate,
    DocumentoEstatisticas,
    DocumentoRead,
    DocumentoUpdate,
    agora_utc,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_banco()
    yield


app = FastAPI(
    title="API de Documentos",
    description="CRUD de documentos, com paginação, filtro por categoria e busca por título.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/documentos", response_model=DocumentoRead, status_code=201)
def criar_documento(documento: DocumentoCreate, session: Session = Depends(get_session)):
    db_documento = Documento.model_validate(documento)
    session.add(db_documento)
    session.commit()
    session.refresh(db_documento)
    return db_documento


@app.get("/documentos", response_model=list[DocumentoRead])
def listar_documentos(
    categoria: Optional[str] = None,
    busca: Optional[str] = Query(default=None, description="Busca por texto no título"),
    offset: int = Query(default=0, ge=0),
    limite: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    query = select(Documento)
    if categoria:
        query = query.where(Documento.categoria == categoria)
    if busca:
        query = query.where(Documento.titulo.contains(busca))
    query = query.offset(offset).limit(limite)
    return session.exec(query).all()


@app.get("/documentos/{documento_id}", response_model=DocumentoRead)
def obter_documento(documento_id: int, session: Session = Depends(get_session)):
    documento = session.get(Documento, documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return documento


@app.put("/documentos/{documento_id}", response_model=DocumentoRead)
def atualizar_documento(
    documento_id: int, dados: DocumentoUpdate, session: Session = Depends(get_session)
):
    documento = session.get(Documento, documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    atualizacoes = dados.model_dump(exclude_unset=True)
    for campo, valor in atualizacoes.items():
        setattr(documento, campo, valor)
    documento.atualizado_em = agora_utc()

    session.add(documento)
    session.commit()
    session.refresh(documento)
    return documento


@app.delete("/documentos/{documento_id}", status_code=204)
def remover_documento(documento_id: int, session: Session = Depends(get_session)):
    documento = session.get(Documento, documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    session.delete(documento)
    session.commit()


@app.get("/documentos/{documento_id}/estatisticas", response_model=DocumentoEstatisticas)
def estatisticas_documento(documento_id: int, session: Session = Depends(get_session)):
    documento = session.get(Documento, documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    total_palavras = len(documento.conteudo.split())
    return DocumentoEstatisticas(
        id=documento.id,
        titulo=documento.titulo,
        total_palavras=total_palavras,
        total_caracteres=len(documento.conteudo),
        tempo_leitura_minutos=round(total_palavras / 200, 1),
    )
