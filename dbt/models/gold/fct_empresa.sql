-- Fato: uma linha por empresa (cnpj_basico) na competência processada.
--
-- capital_social_suspeito marca valores que distorcem totais e rankings:
--   1. igual ou acima do valor-sentinela (999.999.999.999);
--   2. de 1 bilhão para cima formado só por noves seguidos de zeros (999.999.999.000,
--      999.999.000.000...), variações do mesmo preenchimento padrão;
--   3. porte 00, 01 ou 03 com capital muito elevado (limiar heuristico).
-- A classificacao e um alerta analitico, NAO uma comprovacao de fraude/erro.
-- Capital original permanece preservado; marts atuais excluem sinalizados
-- de totais, medias e rankings, conforme politica analitica provisoria.
select
    cnpj_basico,
    razao_social,
    natureza_juridica as natureza_juridica_codigo,
    porte_empresa as porte_codigo,
    qualificacao_responsavel,
    capital_social,
    capital_social_invalido,
    coalesce(
        case
            when capital_social is null then false
            when capital_social >= {{ var('capital_social_valor_sentinela') }} then true
            when
                capital_social >= 1000000000
                and regexp_matches(
                    cast(cast(floor(capital_social) as bigint) as varchar), '^9{6,}0*$'
                ) then true
            when
                porte_empresa in ('00', '01', '03')
                and capital_social >= {{ var('capital_social_limite_porte_pequeno') }} then true
            else false
        end,
        false
    ) as capital_social_suspeito,
    razao_social_continha_cpf,
    competencia
from {{ ref('stg_empresas') }}
