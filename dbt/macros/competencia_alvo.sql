{#- Competência processada: a informada em --vars ou, sem ela, a mais recente na bronze. -#}
{% macro competencia_alvo() -%}
    {%- set competencia = var('competencia', none) -%}
    {%- if competencia -%}
        '{{ competencia }}'
    {%- else -%}
        (select max(_competencia) from {{ source('bronze', 'empresas') }})
    {%- endif -%}
{%- endmacro %}
