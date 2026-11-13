{{ config(tags=['silver']) }}
-- Toda empresa distinta da bronze (na competência) precisa existir na silver.
with bronze as (
    select count(distinct lpad(trim(cnpj_basico), 8, '0')) as qtd
    from {{ source('bronze', 'empresas') }}
    where _competencia = {{ competencia_alvo() }}
),

silver as (
    select count(*) as qtd from {{ ref('stg_empresas') }}
)

select bronze.qtd as qtd_bronze, silver.qtd as qtd_silver
from bronze, silver
where bronze.qtd <> silver.qtd
