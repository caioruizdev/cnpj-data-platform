# Pipeline ELT do CNPJ (Empresas0)

Plataforma de dados para processamento e análise da base pública de empresas do CNPJ da Receita Federal, utilizando o arquivo `Empresas0.zip` como fonte.

A solução organiza os dados em camadas Bronze, Silver e Gold, com orquestração pelo Apache Airflow, transformações pelo dbt e armazenamento analítico em DuckDB.

## Arquitetura

O ambiente utiliza Docker Compose para executar os serviços necessários ao pipeline:

| Componente | Responsabilidade |
|---|---|
| Apache Airflow | Orquestração e acompanhamento das execuções |
| PostgreSQL | Armazenamento dos metadados do Airflow |
| Azurite | Emulação local do Azure Blob Storage |
| DuckDB | Armazenamento analítico |
| dbt | Transformações e testes das camadas Silver e Gold |

A infraestrutura foi projetada para execução local, sem dependência de serviços pagos.

## Pré-requisitos

- Docker com suporte ao Docker Compose.
- Recursos disponíveis para processar a base completa de empresas do CNPJ.

Não é necessário instalar Python, Airflow, dbt ou DuckDB diretamente na máquina.

## Configuração inicial

Crie o arquivo de configuração local a partir do exemplo:

```bash
cp .env.example .env
```

## Inicialização

Para construir a imagem e iniciar os serviços:

```bash
docker compose up -d --build
```

Para verificar os containers:

```bash
docker compose ps
```

A interface do Airflow fica disponível em http://localhost:8080.

O ambiente utiliza o modo `standalone` do Airflow, adequado à execução local e à validação da solução.

## Persistência dos dados

O Docker Compose utiliza volumes para preservar:

- Metadados do Airflow no PostgreSQL.
- Arquivos armazenados no Azurite.
- Warehouse analítico no DuckDB.
- Logs do Airflow.

Os dados permanecem disponíveis quando os containers são interrompidos e iniciados novamente.

## Comandos operacionais

Acompanhar os logs:

```bash
docker compose logs -f airflow
```

Interromper os serviços sem apagar os dados:

```bash
docker compose down
```

Executar os testes Python:

```bash
docker compose exec airflow python -m pytest -c /opt/airflow/pyproject.toml /opt/airflow/tests
```

Executar a análise estática:

```bash
docker compose exec airflow ruff check /opt/airflow/src /opt/airflow/dags /opt/airflow/tests
```

O projeto também disponibiliza um `Makefile` com atalhos para ambientes com GNU Make.

**Atenção:** `docker compose down -v` remove todos os volumes persistentes, incluindo os metadados do Airflow, os arquivos do Azurite e o warehouse DuckDB.

## Organização do projeto

O código está organizado por responsabilidades, separando infraestrutura, ingestão, transformação, orquestração e testes.

As regras de negócio, os procedimentos de reprocessamento, as decisões técnicas e as limitações serão detalhados nas seções correspondentes ao pipeline.
