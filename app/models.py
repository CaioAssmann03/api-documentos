from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def garantir_utc(momento: datetime) -> datetime:
    # SQLite nao tem tipo de data nativo (guarda como TEXT) e devolve
    # datetime "naive" na leitura, mesmo quando o valor foi salvo com
    # timezone. Como toda data desta aplicacao e' sempre UTC por convencao,
    # e' seguro reanexar o timezone aqui antes de comparar com
    # datetime.now(timezone.utc) (comparar aware com naive gera TypeError).
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


class DocumentoBase(SQLModel):
    titulo: str = Field(index=True, min_length=1, max_length=200)
    conteudo: str
    categoria: str = Field(index=True, max_length=50)


class Documento(DocumentoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
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
    usuario_id: int
    criado_em: datetime
    atualizado_em: datetime


class DocumentoEstatisticas(SQLModel):
    id: int
    titulo: str
    total_palavras: int
    total_caracteres: int
    tempo_leitura_minutos: float


class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    senha_hash: str
    criado_em: datetime = Field(default_factory=agora_utc)


class UsuarioCreate(SQLModel):
    email: str
    senha: str = Field(min_length=8)


class UsuarioRead(SQLModel):
    id: int
    email: str
    criado_em: datetime


class TokenRefresh(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    criado_em: datetime = Field(default_factory=agora_utc)
    expira_em: datetime
    revogado: bool = Field(default=False)


class TokenResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(SQLModel):
    refresh_token: str
