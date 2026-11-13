-- Silver: tipagem, limpeza e tratamento de dados inconsistentes.
-- Granularidade: uma linha por cnpj_basico na competência processada.

with origem as (
    select
        lpad(trim(cnpj_basico), 8, '0') as cnpj_basico,
        razao_social as razao_social_bruta,
        natureza_juridica,
        qualificacao_responsavel,
        capital_social as capital_social_bruto,
        porte_empresa,
        ente_federativo_responsavel,
        _competencia,
        _arquivo,
        _carregado_em,
        row_number() over (
            partition by lpad(trim(cnpj_basico), 8, '0')
            order by
                _carregado_em desc nulls last,
                _run_id desc nulls last,
                _sha256 desc nulls last,
                _arquivo desc nulls last,
                razao_social desc nulls last,
                natureza_juridica desc nulls last,
                qualificacao_responsavel desc nulls last,
                capital_social desc nulls last,
                porte_empresa desc nulls last,
                ente_federativo_responsavel desc nulls last,
                cnpj_basico desc nulls last
        ) as _ordem
    from {{ source('bronze', 'empresas') }}
    where _competencia = {{ competencia_alvo() }}
),

tratado as (
    select
        cnpj_basico,

        -- Razão social de empresário individual costuma trazer CPF (e, às vezes, o CNPJ
        -- base formatado no início). O CPF é mascarado e o prefixo é removido.
        nullif(
            trim(
                regexp_replace(
                    regexp_replace(trim(razao_social_bruta), '^\d{2}\.\d{3}\.\d{3}\s+', ''),
                    '\b\d{11}\b', '[CPF]', 'g'
                )
            ),
            ''
        ) as razao_social,
        coalesce(regexp_matches(razao_social_bruta, '\b\d{11}\b'), false)
            as razao_social_continha_cpf,

        lpad(trim(natureza_juridica), 4, '0') as natureza_juridica,
        lpad(trim(qualificacao_responsavel), 2, '0') as qualificacao_responsavel,

        -- Capital social vem como texto com vírgula decimal ("5000,00").
        try_cast(replace(trim(capital_social_bruto), ',', '.') as decimal(20, 2))
            as capital_social,
        (
            trim(coalesce(capital_social_bruto, '')) <> ''
            and try_cast(replace(trim(capital_social_bruto), ',', '.') as decimal(20, 2)) is null
        ) as capital_social_invalido,

        -- Porte vazio vira '00' (não informado), conforme o dicionário da Receita.
        lpad(coalesce(trim(porte_empresa), ''), 2, '0') as porte_empresa,
        nullif(trim(ente_federativo_responsavel), '') as ente_federativo_responsavel,

        _competencia as competencia,
        _arquivo as arquivo_origem
    from origem
    where _ordem = 1
)

select * from tratado
