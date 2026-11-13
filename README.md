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

## Origem e extração dos dados

A fonte utilizada é o arquivo `Empresas0.zip` da base pública do CNPJ da Receita Federal. O pipeline aceita uma origem local ou uma URL configurada por variável de ambiente.

### Configuração da origem

Na execução local, o arquivo deve estar disponível em `data/Empresas0.zip`. Esse diretório é montado no container em `/opt/airflow/data`.

A variável `CNPJ_LOCAL_ZIP` define o caminho do arquivo dentro do container. Alternativamente, `CNPJ_SOURCE_URL` permite configurar uma origem HTTP, com substituição do marcador `{competencia}` pelo mês de referência no formato `AAAA-MM`.

O arquivo de origem não é versionado no repositório.

### Armazenamento e rastreabilidade

A extração utiliza `fsspec` e `adlfs` para armazenar o ZIP no Azurite, em um caminho organizado por competência:

`source-files/cnpj/competencia=AAAA-MM/Empresas0.zip`

Um arquivo `.sha256` é gravado ao término da transferência, permitindo identificar a versão armazenada e verificar sua integridade antes do reaproveitamento.

A transferência ocorre em blocos de 8 MB, sem necessidade de carregar o ZIP completo na memória. Para origens HTTP, são configuradas novas tentativas em falhas transitórias.

### Reexecução e falhas

Quando o arquivo e seu checksum já existem, a extração confere o SHA-256 do conteúdo armazenado antes de reutilizá-lo.

O parâmetro `force=True` permite realizar uma nova extração. Em caso de erro durante a transferência, o arquivo parcial é removido e o checksum anterior não é mantido.

A substituição forçada não é atômica: uma falha pode deixar a competência temporariamente sem o arquivo armazenado. Para cargas que exigem continuidade de leitura durante substituições, uma evolução possível é utilizar um caminho temporário e publicar o novo objeto após sua validação.

O SHA-256 verifica a consistência entre o conteúdo recebido e o armazenado; não comprova, isoladamente, a integridade ou a procedência da publicação na origem.

### Testes da extração

Os testes utilizam um ZIP sintético e um filesystem em memória. Cobrem extração local, cálculo de checksum, reaproveitamento, substituição forçada, origem ausente, competência inválida, conteúdo inválido e detecção de corrupção.

```bash
docker compose exec airflow python -m pytest tests/test_extract.py -v
```

## Camada Bronze e controle operacional

A camada Bronze recebe os registros do arquivo original armazenado no Azurite e os persiste no DuckDB, preservando os sete campos de origem como texto. A tipagem e as regras de negócio são aplicadas posteriormente pela camada Silver.

### Estrutura e granularidade

A tabela `bronze.empresas` representa os registros de empresas recebidos em cada competência. Sua granularidade é uma linha do arquivo de origem por competência.

Os campos originais são:

- `cnpj_basico`
- `razao_social`
- `natureza_juridica`
- `qualificacao_responsavel`
- `capital_social`
- `porte_empresa`
- `ente_federativo_responsavel`

São acrescentados os metadados `_competencia`, `_arquivo`, `_sha256`, `_carregado_em` e `_run_id`, que permitem identificar a origem e a execução responsável pela carga.

A Bronze não impõe unicidade de CNPJ básico. A consistência das chaves e os tratamentos dos domínios são avaliados nas transformações posteriores.

### Processamento e codificação

A carga verifica o checksum do ZIP armazenado, extrai o arquivo CSV e converte seu conteúdo de ISO-8859-1 para UTF-8 em blocos.

O DuckDB lê os sete campos como `VARCHAR`, sem converter valores monetários ou códigos durante a ingestão.

Os arquivos intermediários são mantidos em diretório temporário e removidos ao final da operação.

### Idempotência e reprocessamento

A carga é executada por competência, no formato `AAAA-MM`.

Para reprocessar uma competência, os registros anteriores daquele mês são removidos e substituídos dentro de uma transação DuckDB. Em caso de falha durante a inserção ou reconciliação, a transação é revertida, preservando a carga anterior.

Competências diferentes podem coexistir na Bronze.

### Reconciliação e registros rejeitados

O pipeline compara a quantidade de linhas do CSV com a quantidade efetivamente carregada.

A leitura utiliza `ignore_errors=true` e aplica o limite configurável `MAX_REJEITADAS_PCT`, cujo padrão é `0.1`, correspondente a 0,1%.

Se a diferença ultrapassar o limite permitido, a carga falha e a transação é revertida.

A implementação registra a quantidade de linhas rejeitadas no resultado da carga, mas ainda não mantém uma tabela de quarentena com o conteúdo individual desses registros.

### Controle operacional

A tabela `ops.execucoes` registra o identificador da execução, a competência, a etapa, o status, os horários de início e término e uma mensagem de diagnóstico.

Quando disponíveis, também são registrados a quantidade de linhas do arquivo, a quantidade carregada na Bronze e o checksum SHA-256.

Falhas são registradas e suas exceções são propagadas para permitir que o orquestrador identifique a execução malsucedida.

O histórico operacional é mantido separadamente da transação de carga da Bronze.

### Testes da Bronze

Os testes automatizados verificam carga e metadados, preservação de caracteres, idempotência, coexistência de competências, ausência da origem, corrupção do ZIP, rollback, registro de falhas e conversão de codificação.

```bash
docker compose exec airflow python -m pytest tests/test_bronze.py tests/test_controle.py tests/test_utf8.py -v
```

## Camada Silver

A camada Silver transforma os registros da Bronze em dados tipados e padronizados, utilizando o dbt com DuckDB.

### Granularidade e competência

O modelo `silver.stg_empresas` contém uma linha por CNPJ básico na competência processada.

A competência pode ser informada pela variável `competencia` do dbt. Na ausência desse parâmetro, a macro utiliza a competência mais recente encontrada na Bronze.

Quando existem registros repetidos para um CNPJ básico, o modelo mantém o registro com `_carregado_em` mais recente. A presença de duplicidades na origem é monitorada por teste de qualidade.

### Tratamentos aplicados

- Padronização do CNPJ básico para oito caracteres.
- Remoção de espaços e padronização de códigos.
- Conversão do capital social para `DECIMAL(20,2)`, considerando a vírgula decimal da origem.
- Identificação de valores de capital social que não podem ser convertidos.
- Padronização do porte empresarial, utilizando `00` para valores não informados.
- Tratamento de razão social vazia.
- Mascaramento de sequências identificadas como CPF na razão social.

O capital social inválido permanece nulo na coluna tipada e é identificado pelo indicador `capital_social_invalido`. Os valores originais permanecem disponíveis na Bronze.

### Qualidade dos dados

A Silver possui verificações de unicidade e preenchimento do CNPJ básico, preenchimento da natureza jurídica e do porte, códigos de porte aceitos e reconciliação com a Bronze.

A validação de duplicidades na origem é classificada como aviso, permitindo identificar ocorrências sem interromper automaticamente a transformação.

### Execução dos testes

Para executar somente os testes da Silver da competência de outubro de 2026:

```bash
docker compose exec airflow /opt/dbt-venv/bin/dbt test --select tag:silver --indirect-selection cautious --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt --vars '{"competencia":"2026-10"}'
```

A seleção cautelosa evita incluir testes que também dependam de modelos da Gold.

A materialização da Silver é realizada pelo dbt e será integrada à execução orquestrada do pipeline.
