from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    Documento,
    DocumentoCreate,
    DocumentoEstatisticas,
    DocumentoRead,
    DocumentoUpdate,
    Usuario,
    agora_utc,
)
from app.security import obter_usuario_atual

router = APIRouter(prefix="/documentos", tags=["documentos"])


def _obter_documento_do_usuario(
    documento_id: int, usuario: Usuario, session: Session
) -> Documento:
    documento = session.get(Documento, documento_id)
    # 404 (nao 403) quando o documento existe mas e' de outro usuario: nao
    # revela pra quem esta' tentando acessar se o id existe ou nao.
    if not documento or documento.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return documento


@router.post("", response_model=DocumentoRead, status_code=201)
def criar_documento(
    documento: DocumentoCreate,
    usuario: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session),
):
    db_documento = Documento.model_validate(documento, update={"usuario_id": usuario.id})
    session.add(db_documento)
    session.commit()
    session.refresh(db_documento)
    return db_documento


@router.get("", response_model=list[DocumentoRead])
def listar_documentos(
    categoria: Optional[str] = None,
    busca: Optional[str] = Query(default=None, description="Busca por texto no título"),
    offset: int = Query(default=0, ge=0),
    limite: int = Query(default=20, ge=1, le=100),
    usuario: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session),
):
    query = select(Documento).where(Documento.usuario_id == usuario.id)
    if categoria:
        query = query.where(Documento.categoria == categoria)
    if busca:
        query = query.where(Documento.titulo.contains(busca))
    query = query.offset(offset).limit(limite)
    return session.exec(query).all()


@router.get("/{documento_id}", response_model=DocumentoRead)
def obter_documento(
    documento_id: int,
    usuario: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session),
):
    return _obter_documento_do_usuario(documento_id, usuario, session)


@router.put("/{documento_id}", response_model=DocumentoRead)
def atualizar_documento(
    documento_id: int,
    dados: DocumentoUpdate,
    usuario: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session),
):
    documento = _obter_documento_do_usuario(documento_id, usuario, session)

    atualizacoes = dados.model_dump(exclude_unset=True)
    for campo, valor in atualizacoes.items():
        setattr(documento, campo, valor)
    documento.atualizado_em = agora_utc()

    session.add(documento)
    session.commit()
    session.refresh(documento)
    return documento


@router.delete("/{documento_id}", status_code=204)
def remover_documento(
    documento_id: int,
    usuario: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session),
):
    documento = _obter_documento_do_usuario(documento_id, usuario, session)
    session.delete(documento)
    session.commit()


@router.get("/{documento_id}/estatisticas", response_model=DocumentoEstatisticas)
def estatisticas_documento(
    documento_id: int,
    usuario: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session),
):
    documento = _obter_documento_do_usuario(documento_id, usuario, session)

    total_palavras = len(documento.conteudo.split())
    return DocumentoEstatisticas(
        id=documento.id,
        titulo=documento.titulo,
        total_palavras=total_palavras,
        total_caracteres=len(documento.conteudo),
        tempo_leitura_minutos=round(total_palavras / 200, 1),
    )
