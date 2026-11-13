{{ config(severity='error', tags=['gold']) }}
-- Cada empresa deve contribuir uma vez para cada agrupamento analitico.
with totais as (
    select
        (select count(*) from {{ ref('fct_empresa') }}) as qtd_fato,
        (select coalesce(sum(qtd_empresas), 0) from {{ ref('mart_natureza_juridica') }}) as qtd_natureza,
        (select coalesce(sum(qtd_empresas), 0) from {{ ref('mart_porte_distribuicao') }}) as qtd_porte
)
select * from totais
where qtd_fato <> qtd_natureza or qtd_fato <> qtd_porte
