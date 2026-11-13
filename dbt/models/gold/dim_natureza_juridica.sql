-- Dimensão de natureza jurídica. Códigos presentes nos dados e ausentes da tabela de
-- referência entram como 'NÃO MAPEADA', mantendo a integridade referencial e a visibilidade.

with mapeadas as (
    select codigo, descricao from {{ ref('natureza_juridica') }}
),

usadas as (
    select distinct natureza_juridica as codigo from {{ ref('stg_empresas') }}
),

nao_mapeadas as (
    select u.codigo, 'NÃO MAPEADA' as descricao
    from usadas u
    left join mapeadas m on m.codigo = u.codigo
    where m.codigo is null
),

todas as (
    select codigo, descricao, true as mapeada from mapeadas
    union all
    select codigo, descricao, false as mapeada from nao_mapeadas
)

select
    codigo,
    descricao,
    case left(codigo, 1)
        when '1' then 'Administração Pública'
        when '2' then 'Entidades Empresariais'
        when '3' then 'Entidades sem Fins Lucrativos'
        when '4' then 'Pessoas Físicas'
        when '5' then 'Organizações Internacionais e Outras Instituições Extraterritoriais'
        else 'Não classificado'
    end as grupo,
    mapeada
from todas
