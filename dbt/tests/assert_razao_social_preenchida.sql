{{ config(severity='warn', tags=['gold']) }}
select cnpj_basico
from {{ ref('fct_empresa') }}
where razao_social is null
