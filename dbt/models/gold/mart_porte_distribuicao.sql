-- Pergunta 2 (parte 1): distribuição do capital social por porte da empresa.
-- As estatísticas excluem o valor-sentinela (capital_social_suspeito).

select
    d.codigo as porte_codigo,
    d.descricao as porte,
    count(*) as qtd_empresas,
    count(f.capital_social) as qtd_com_capital_informado,
    count(*) filter (where f.capital_social_suspeito) as qtd_capital_suspeito,
    sum(f.capital_social) filter (where not f.capital_social_suspeito) as capital_social_total,
    round(avg(f.capital_social) filter (where not f.capital_social_suspeito), 2)
        as capital_social_medio,
    min(f.capital_social) filter (where not f.capital_social_suspeito) as capital_social_minimo,
    round(quantile_cont(f.capital_social, 0.5) filter (where not f.capital_social_suspeito), 2)
        as capital_social_mediano,
    round(quantile_cont(f.capital_social, 0.9) filter (where not f.capital_social_suspeito), 2)
        as capital_social_p90,
    max(f.capital_social) filter (where not f.capital_social_suspeito) as capital_social_maximo
from {{ ref('fct_empresa') }} f
inner join {{ ref('dim_porte') }} d on d.codigo = f.porte_codigo
group by d.codigo, d.descricao
order by d.codigo
