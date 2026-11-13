{{ config(severity='error', tags=['gold']) }}
-- A camada Gold deve preservar uma linha por empresa da Silver.
with totais as (
    select
        (select count(*) from {{ ref('stg_empresas') }}) as qtd_silver,
        (select count(*) from {{ ref('fct_empresa') }}) as qtd_gold
)
select * from totais where qtd_silver <> qtd_gold
