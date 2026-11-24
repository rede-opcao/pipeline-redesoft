{# Usa o schema configurado (staging/gold) sem prefixar o schema do target. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}

{# Payload da execução mais recente de uma fonte snapshot (cadastros). #}
{% macro ultimo_snapshot(tabela) %}
select r.payload
from {{ source('raw', tabela) }} r
where r.run_id = (select run_id from {{ source('raw', tabela) }} order by carregado_em desc, id desc limit 1)
{% endmacro %}

{# Versão mais recente de cada registro de uma fonte incremental (janelas se sobrepõem entre execuções). #}
{% macro deduplicado(tabela, chave) %}
select payload
from (
    select payload,
           row_number() over (partition by {{ chave }} order by carregado_em desc, id desc) as rn
    from {{ source('raw', tabela) }}
) d
where rn = 1
{% endmacro %}
