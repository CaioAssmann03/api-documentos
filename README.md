# API de Documentos

CRUD completo de documentos com FastAPI, pensado pra ser a base dos próximos projetos do
roadmap (autenticação, agente de IA, RAG): em vez de 4 projetos soltos, uma única API que
cresce a cada etapa.

## O que a API faz

6 endpoints:
- `POST /documentos` — cria
- `GET /documentos` — lista, com paginação, filtro por categoria e busca por título
- `GET /documentos/{id}` — detalhe
- `PUT /documentos/{id}` — atualização parcial
- `DELETE /documentos/{id}` — remove
- `GET /documentos/{id}/estatisticas` — contagem de palavras/caracteres e tempo estimado de leitura

Documentação automática (Swagger) em `/docs`.

## Decisões técnicas

**SQLModel em vez de SQLAlchemy e Pydantic separados.** SQLModel (do mesmo autor do
FastAPI) deixa a mesma classe servir de schema de validação e de tabela do banco, menos
código duplicado pra um CRUD desse tamanho.

**SQLite em vez de Postgres.** Mesma ferramenta que já uso nos projetos de dados, zero
setup de infraestrutura extra pro primeiro projeto do roadmap novo. Trocar pra Postgres
mais adiante, quando entrar multi-tenancy no roadmap, é só mudar a `DATABASE_URL`.

**Banco de teste em memória, não o arquivo real.** Os testes usam
`create_engine("sqlite://", poolclass=StaticPool)`, um banco novo e vazio a cada teste,
sem tocar no `documentos.db` de desenvolvimento. O `StaticPool` é necessário porque um
banco SQLite em memória sem ele desapareceria entre uma chamada e outra dentro do mesmo
teste.

**Atualização parcial no PUT.** `DocumentoUpdate` tem todos os campos opcionais, e o
endpoint usa `model_dump(exclude_unset=True)` pra só sobrescrever o que veio no corpo da
requisição. Sem isso, mandar só `{"categoria": "x"}` apagaria título e conteúdo.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Documentação interativa em http://127.0.0.1:8000/docs. Testes com `pytest`.

## Aprendizados

- `datetime.utcnow()` está depreciado desde o Python 3.12, com remoção prevista pra uma
  versão futura. `datetime.now(timezone.utc)` é o substituto correto, timezone-aware.
- Testar API sem sujar o banco de desenvolvimento se resolve injetando uma sessão de teste
  via `app.dependency_overrides`, o próprio mecanismo de injeção de dependência do
  FastAPI. Não precisou de nenhuma biblioteca extra de mock.

## Limitações conhecidas

- Sem autenticação ainda. É o próximo item do roadmap (`roadmap-dev-caio.md`), de
  propósito: mais fácil aprender autenticação sobre uma API que já funciona do que os dois
  ao mesmo tempo.
- O banco de dados fica de fora do repositório (`*.db` no `.gitignore`). Ao contrário dos
  projetos de dados, aqui o banco é estado de execução, não o dado entregável. Quem clonar
  roda com um banco vazio.
- Sem deploy ainda. Fica pra quando o projeto tiver autenticação, pra não publicar uma API
  sem nenhum controle de acesso.
