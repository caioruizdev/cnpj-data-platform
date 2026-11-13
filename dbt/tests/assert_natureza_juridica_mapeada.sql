{{ config(severity='warn', tags=['gold']) }}
-- Códigos de natureza jurídica presentes nos dados e ausentes da tabela de referência.
select codigo
from {{ ref('dim_natureza_juridica') }}
where not mapeada
