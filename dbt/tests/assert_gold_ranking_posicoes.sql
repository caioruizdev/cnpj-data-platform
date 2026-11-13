{{ config(severity='error', tags=['gold']) }}
-- Cada porte tem posicoes sem repeticao, de 1 ate o tamanho efetivo do top N.
with por_porte as (
    select
        porte_codigo,
        count(*) as qtd,
        count(distinct posicao) as qtd_posicoes,
        min(posicao) as primeira_posicao,
        max(posicao) as ultima_posicao
    from {{ ref('mart_top_empresas_por_porte') }}
    group by porte_codigo
)
select * from por_porte
where qtd <> qtd_posicoes
   or primeira_posicao <> 1
   or ultima_posicao <> qtd
   or qtd > {{ var('top_n_por_porte', 10) }}
