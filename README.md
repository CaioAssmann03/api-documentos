# API de Documentos

CRUD de documentos com FastAPI, autenticado por usuário com JWT, pensado pra ser a base
dos próximos projetos do roadmap (agente de IA, RAG): em vez de projetos soltos, uma única
API que cresce a cada etapa.

## O que a API faz

**Autenticação** (`/auth`):
- `POST /auth/registrar` — cria usuário (e-mail + senha)
- `POST /auth/login` — devolve access token (30 min) e refresh token (7 dias)
- `POST /auth/refresh` — troca um refresh token válido por um par novo
- `POST /auth/logout` — revoga o refresh token
- `GET /auth/me` — dados do usuário autenticado

**Documentos** (`/documentos`, todos exigem token, cada usuário só vê os próprios):
- `POST /documentos` — cria
- `GET /documentos` — lista, com paginação, filtro por categoria e busca por título
- `GET /documentos/{id}` — detalhe
- `PUT /documentos/{id}` — atualização parcial
- `DELETE /documentos/{id}` — remove
- `GET /documentos/{id}/estatisticas` — contagem de palavras/caracteres e tempo estimado de leitura

Documentação automática (Swagger, com botão "Authorize") em `/docs`.

## Decisões técnicas

**SQLModel em vez de SQLAlchemy e Pydantic separados.** SQLModel (do mesmo autor do
FastAPI) deixa a mesma classe servir de schema de validação e de tabela do banco, menos
código duplicado pra um CRUD desse tamanho.

**SQLite em vez de Postgres.** Mesma ferramenta que já uso nos projetos de dados, zero
setup de infraestrutura extra. Trocar pra Postgres mais adiante, quando entrar
multi-tenancy no roadmap, é só mudar a `DATABASE_URL`.

**JWT "do zero", mas não a criptografia do zero.** "Sem biblioteca pronta" aqui significa
sem `fastapi-users` ou equivalente escondendo o fluxo de registro/login/refresh. A
assinatura do token usa `PyJWT`, e o hash de senha usa `bcrypt`: implementar HMAC ou um
KDF de senha na mão seria reinventar criptografia, que é exatamente o tipo de coisa que
não se deve fazer por conta própria.

**Access token curto (JWT stateless) + refresh token longo (guardado no banco).** Um JWT
não dá pra revogar antes de expirar, só existe validação matemática da assinatura. Por
isso o access token dura só 30 minutos: se vazar, o estrago é limitado. O refresh token
mora numa tabela (`TokenRefresh`, guardado como hash SHA-256, não em texto puro) porque
login/logout/revogação exigem poder invalidar um token específico, o que só é possível
com estado no servidor.

**Refresh token rotativo.** Cada uso de `/auth/refresh` revoga o token antigo e emite um
par novo. Se um token vazado for usado por um atacante e depois pelo dono legítimo (ou
vice-versa), a segunda tentativa encontra o token já revogado, sinal de que algo vazou.

**404, não 403, pra documento de outro usuário.** Tentar acessar `/documentos/{id}` de
outra pessoa devolve "não encontrado", não "acesso negado". Não revela se aquele id existe
no banco pra quem não tem permissão de ver.

**Atualização parcial no PUT.** `DocumentoUpdate` tem todos os campos opcionais, e o
endpoint usa `model_dump(exclude_unset=True)` pra só sobrescrever o que veio no corpo da
requisição.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Crie um `.env` a partir do `.env.example` com uma `SECRET_KEY` própria:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

```bash
uvicorn app.main:app --reload
```

Documentação interativa em http://127.0.0.1:8000/docs. Testes com `pytest` (a suíte usa
uma `SECRET_KEY` de teste fixa, não depende do `.env`).

## Aprendizados

- `datetime.utcnow()` está depreciado desde o Python 3.12, com remoção prevista pra uma
  versão futura. `datetime.now(timezone.utc)` é o substituto correto, timezone-aware.
- SQLite não tem tipo de data nativo (guarda como TEXT) e devolve `datetime` "naive" na
  leitura, mesmo quando o valor foi salvo com timezone. Comparar isso direto com
  `datetime.now(timezone.utc)` derruba com `TypeError: can't compare offset-naive and
  offset-aware datetimes`. Resolvido reanexando o timezone na leitura (`garantir_utc` em
  `app/models.py`), já que toda data da aplicação é UTC por convenção.
- Testar API sem sujar o banco de desenvolvimento se resolve injetando uma sessão de teste
  via `app.dependency_overrides`, o próprio mecanismo de injeção de dependência do
  FastAPI. Não precisou de nenhuma biblioteca extra de mock.

## Limitações conhecidas

- Sem rate limiting no `/auth/login`. Em produção isso é obrigatório (evita força bruta de
  senha); fica pra um projeto futuro do roadmap que trata isso especificamente (API #3,
  rate limiting e cache).
- Sem verificação de e-mail nem fluxo de "esqueci minha senha". Registro cria a conta
  direto, sem confirmação.
- O banco de dados fica de fora do repositório (`*.db` no `.gitignore`). Quem clonar roda
  com um banco vazio.
- Sem deploy ainda.
