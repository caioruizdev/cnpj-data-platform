{{ config(severity='error', tags=['gold']) }}
-- Os totais dos marts usam a politica de exclusao definida na fct_empresa.
-- Comparacao em DECIMAL: nao usar FLOAT e nem tolerancia financeira arbitraria.
with totais as (
    select
        (select coalesce(sum(capital_social), 0)::decimal(38,2)
         from {{ ref('fct_empresa') }}
         where not coalesce(capital_social_suspeito, false)) as capital_fato,
        (select coalesce(sum(capital_social_total), 0)::decimal(38,2)
         from {{ ref('mart_natureza_juridica') }}) as capital_natureza,
        (select coalesce(sum(capital_social_total), 0)::decimal(38,2)
         from {{ ref('mart_porte_distribuicao') }}) as capital_porte
)
select * from totais
where capital_fato <> capital_natureza or capital_fato <> capital_porte
