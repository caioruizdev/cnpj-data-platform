{{ config(severity='warn', tags=['silver']) }}
-- Duplicidade de cnpj_basico na bronze (a silver mantém a carga mais recente).
select lpad(trim(cnpj_basico), 8, '0') as cnpj_basico, count(*) as ocorrencias
from {{ source('bronze', 'empresas') }}
where _competencia = {{ competencia_alvo() }}
group by 1
having count(*) > 1
