-- Pergunta 1: naturezas jurídicas com mais empresas, e capital social total e médio de cada uma.
-- Totais e médias excluem o valor-sentinela (capital_social_suspeito); a coluna
-- capital_social_total_com_suspeitos mostra o total sem esse tratamento.
-- A média considera as empresas com capital social informado (zero incluído).

select
    d.codigo as natureza_juridica_codigo,
    d.descricao as natureza_juridica,
    d.grupo,
    count(*) as qtd_empresas,
    count(f.capital_social) as qtd_com_capital_informado,
    count(*) filter (where f.capital_social_suspeito) as qtd_capital_suspeito,
    sum(f.capital_social) filter (where not f.capital_social_suspeito) as capital_social_total,
    round(avg(f.capital_social) filter (where not f.capital_social_suspeito), 2)
        as capital_social_medio,
    sum(f.capital_social) as capital_social_total_com_suspeitos,
    round(100.0 * count(*) / sum(count(*)) over (), 2) as pct_empresas,
    rank() over (order by count(*) desc) as ranking_qtd_empresas
from {{ ref('fct_empresa') }} f
inner join {{ ref('dim_natureza_juridica') }} d on d.codigo = f.natureza_juridica_codigo
group by d.codigo, d.descricao, d.grupo
order by qtd_empresas desc
