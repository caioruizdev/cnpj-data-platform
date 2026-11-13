{{ config(severity='error', tags=['gold']) }}
-- O top N nao deve incluir empresas sem capital positivo ou sinalizadas.
select
    r.cnpj_basico, r.porte_codigo, r.posicao, r.capital_social,
    f.capital_social_suspeito
from {{ ref('mart_top_empresas_por_porte') }} r
left join {{ ref('fct_empresa') }} f on r.cnpj_basico = f.cnpj_basico
where f.cnpj_basico is null
   or r.capital_social is null
   or r.capital_social <= 0
   or coalesce(f.capital_social_suspeito, false)
   or r.capital_social is distinct from f.capital_social
   or r.porte_codigo is distinct from f.porte_codigo
