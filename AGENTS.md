Always make sure to comply to these rules. Under Project Stack, you will find technology you have to STRICTLY adhere to. Make sure to comply to instructions.
Project Stack:
uv: Dependency management for Python runtime
Alembic: Database migrations
FastAPI: Backend Logic
SQLAlchemy ORM: Python database ORM
PostgreSQL/SQLITE: Target databases
Pytest: Test suite under tests
NextJS/React: Frontend Code under frontend/
GitLab: Code Repository/ CI CD
.gitlab-ci.yml: Gitlab Runner Config
ruff: Linting and Code Quality Control
docker: Deployment is done via docker-compose.yml
pyproject.toml: Project Setup Config
Coding/Implentation Instructions:
Always use alembic for database structure. Using Base.create_all() and similar syntax is PROHIBITED!
Use alembic revision -m <revision explanation> to create new revisions. Making arbitrary strings as versions etc. is PROHIBITED!
ALWAYS run uv run ruff check --fix after all changes at the end and fix linting issues
ALWAYS run uv run pytest to run test suite after all changes and fix issues shown by tests.
ALWAYS add test cases if relevant.
NEVER use emojis! Use icon packs (for example lucid-react) if needed.
NEVER commit changes. It is upto user to review your code and commit and push it. Unless user specifically asks for it, commiting code is PROHIBITED!