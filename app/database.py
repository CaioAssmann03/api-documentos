from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///./documentos.db"

# check_same_thread=False: o SQLite por padrao so' permite uso na thread que
# abriu a conexao. O FastAPI atende cada requisicao numa thread do pool,
# entao precisa dessa flag pra nao dar erro em runtime.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def criar_banco() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
