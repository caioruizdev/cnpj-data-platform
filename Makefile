# Atalhos. No Windows puro o `make` não existe: use os comandos `docker compose` do README.
# No Codespaces / WSL / Linux / Mac, `make` funciona normalmente.

.PHONY: setup up down logs test lint reset

setup:
	cp -n .env.example .env || true

up: setup
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f airflow

test:
	docker compose exec airflow python -m pytest -c /opt/airflow/pyproject.toml /opt/airflow/tests

lint:
	docker compose exec airflow ruff check /opt/airflow/src /opt/airflow/dags /opt/airflow/tests

# Remove todos os volumes persistentes: metadados do Airflow, blobs do Azurite e warehouse DuckDB.
reset:
	docker compose down -v
