{{ config(severity='warn', tags=['gold']) }}
-- Empresas com capital social igual ao valor-sentinela (excluídas de totais e rankings).
select cnpj_basico, capital_social
from {{ ref('fct_empresa') }}
where capital_social_suspeito
