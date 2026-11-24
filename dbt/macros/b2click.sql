{# Conversões dos campos CSV do B2Click (tudo chega como texto no payload). #}

{% macro b2c_txt(campo) -%} nullif(payload->>'{{ campo }}', '') {%- endmacro %}

{% macro b2c_int(campo) -%} nullif(payload->>'{{ campo }}', '')::bigint {%- endmacro %}

{# vírgula decimal: "1460066,25" -> 1460066.25 #}
{% macro b2c_num(campo) -%} replace(nullif(payload->>'{{ campo }}', ''), ',', '.')::numeric {%- endmacro %}

{% macro b2c_data(campo) -%} to_date(nullif(payload->>'{{ campo }}', ''), 'DD/MM/YYYY') {%- endmacro %}

{# data dd/mm/aaaa + hora hh:mi:ss em colunas separadas #}
{% macro b2c_ts(campo_data, campo_hora) -%}
to_timestamp(nullif(payload->>'{{ campo_data }}', '') || ' ' || coalesce(nullif(payload->>'{{ campo_hora }}', ''), '00:00:00'),
             'DD/MM/YYYY HH24:MI:SS')::timestamp
{%- endmacro %}

{# "dd/mm/aaaa hh:mi:ss" numa coluna só #}
{% macro b2c_momento(campo) -%} to_timestamp(nullif(payload->>'{{ campo }}', ''), 'DD/MM/YYYY HH24:MI:SS')::timestamp {%- endmacro %}

{% macro b2c_bool(campo) -%} coalesce(upper(payload->>'{{ campo }}') in ('SIM', 'S', 'TRUE', '1'), false) {%- endmacro %}
