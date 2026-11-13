-- Pergunta 2: top N empresas por capital social em cada porte.
-- Usa arg_max(..., N) para manter apenas os N maiores valores por porte
-- sem calcular ROW_NUMBER sobre todas as empresas elegiveis.
-- Desempate: menor CNPJ basico primeiro (o identificador tem 8 digitos).
-- As regras de elegibilidade permanecem inalteradas.

with top_por_porte as (
    select
        porte_codigo,
        arg_max(
            struct_pack(
                cnpj_basico := cnpj_basico,
                razao_social := razao_social,
                natureza_juridica_codigo := natureza_juridica_codigo,
                capital_social := capital_social
            ),
            struct_pack(
                capital := capital_social,
                desempate := -cast(cnpj_basico as bigint)
            ),
            {{ var('top_n_por_porte', 10) }}
        ) as empresas
    from {{ ref('fct_empresa') }}
    where capital_social > 0
      and not coalesce(capital_social_suspeito, false)
    group by porte_codigo
),
ranqueadas as (
    select
        porte_codigo,
        unnest(empresas) as empresa,
        generate_subscripts(empresas, 1) as posicao
    from top_por_porte
)
select
    r.porte_codigo,
    p.descricao as porte,
    r.posicao,
    r.empresa.cnpj_basico as cnpj_basico,
    r.empresa.razao_social as razao_social,
    n.descricao as natureza_juridica,
    r.empresa.capital_social as capital_social
from ranqueadas r
inner join {{ ref('dim_porte') }} p on p.codigo = r.porte_codigo
left join {{ ref('dim_natureza_juridica') }} n
    on n.codigo = r.empresa.natureza_juridica_codigo
order by r.porte_codigo, r.posicao
