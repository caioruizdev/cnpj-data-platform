{{ config(tags=['gold']) }}
select cnpj_basico, capital_social
from {{ ref('fct_empresa') }}
where capital_social < 0
