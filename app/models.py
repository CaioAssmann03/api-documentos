from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class DocumentoBase(SQLModel):
    titulo: str = Field(index=True, min_length=1, max_length=200)
    conteudo: str
    categoria: str = Field(index=True, max_length=50)


class Documento(DocumentoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    criado_em: datetime = Field(default_factory=agora_utc)
    atualizado_em: datetime = Field(default_factory=agora_utc)


class DocumentoCreate(DocumentoBase):
    pass


class DocumentoUpdate(SQLModel):
    titulo: Optional[str] = None
    conteudo: Optional[str] = None
    categoria: Optional[str] = None


class DocumentoRead(DocumentoBase):
    id: int
    criado_em: datetime
    atualizado_em: datetime


class DocumentoEstatisticas(SQLModel):
    id: int
    titulo: str
    total_palavras: int
    total_caracteres: int
    tempo_leitura_minutos: float
