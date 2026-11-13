{{ config(severity='warn', tags=['gold']) }}
-- Capital social com texto que não pôde ser convertido para número.
select cnpj_basico
from {{ ref('fct_empresa') }}
where capital_social_invalido
