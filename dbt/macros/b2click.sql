{# Conversões dos campos CSV do B2Click, em PostgreSQL (payload jsonb) e BigQuery (colunas STRING).
   Cada macro escolhe a versão pelo banco do target: default__ = PostgreSQL, bigquery__ = BigQuery. #}

{% macro b2c_txt(campo) -%} {{ return(adapter.dispatch('b2c_txt')(campo)) }} {%- endmacro %}
{% macro default__b2c_txt(campo) -%} nullif(payload->>'{{ campo }}', '') {%- endmacro %}
{% macro bigquery__b2c_txt(campo) -%} nullif(`{{ campo }}`, '') {%- endmacro %}

{% macro b2c_int(campo) -%} {{ return(adapter.dispatch('b2c_int')(campo)) }} {%- endmacro %}
{% macro default__b2c_int(campo) -%} nullif(payload->>'{{ campo }}', '')::bigint {%- endmacro %}
{% macro bigquery__b2c_int(campo) -%} safe_cast(nullif(`{{ campo }}`, '') as int64) {%- endmacro %}

{# vírgula decimal: "1460066,25" -> 1460066.25 #}
{% macro b2c_num(campo) -%} {{ return(adapter.dispatch('b2c_num')(campo)) }} {%- endmacro %}
{% macro default__b2c_num(campo) -%} replace(nullif(payload->>'{{ campo }}', ''), ',', '.')::numeric {%- endmacro %}
{% macro bigquery__b2c_num(campo) -%} safe_cast(replace(nullif(`{{ campo }}`, ''), ',', '.') as numeric) {%- endmacro %}

{% macro b2c_data(campo) -%} {{ return(adapter.dispatch('b2c_data')(campo)) }} {%- endmacro %}
{% macro default__b2c_data(campo) -%} to_date(nullif(payload->>'{{ campo }}', ''), 'DD/MM/YYYY') {%- endmacro %}
{% macro bigquery__b2c_data(campo) -%} safe.parse_date('%d/%m/%Y', nullif(`{{ campo }}`, '')) {%- endmacro %}

{# data dd/mm/aaaa + hora hh:mi:ss em colunas separadas #}
{% macro b2c_ts(campo_data, campo_hora) -%} {{ return(adapter.dispatch('b2c_ts')(campo_data, campo_hora)) }} {%- endmacro %}
{% macro default__b2c_ts(campo_data, campo_hora) -%}
to_timestamp(nullif(payload->>'{{ campo_data }}', '') || ' ' || coalesce(nullif(payload->>'{{ campo_hora }}', ''), '00:00:00'),
             'DD/MM/YYYY HH24:MI:SS')::timestamp
{%- endmacro %}
{% macro bigquery__b2c_ts(campo_data, campo_hora) -%}
safe.parse_datetime('%d/%m/%Y %H:%M:%S', concat(nullif(`{{ campo_data }}`, ''), ' ', coalesce(nullif(`{{ campo_hora }}`, ''), '00:00:00')))
{%- endmacro %}

{% macro b2c_bool(campo) -%} {{ return(adapter.dispatch('b2c_bool')(campo)) }} {%- endmacro %}
{% macro default__b2c_bool(campo) -%} coalesce(upper(payload->>'{{ campo }}') in ('SIM', 'S', 'TRUE', '1'), false) {%- endmacro %}
{% macro bigquery__b2c_bool(campo) -%} coalesce(upper(`{{ campo }}`) in ('SIM', 'S', 'TRUE', '1'), false) {%- endmacro %}

{# Chave de texto a partir de várias colunas: rs_chave(['a', 'b'], '|') #}
{% macro rs_chave(colunas, sep='|') -%} {{ return(adapter.dispatch('rs_chave')(colunas, sep)) }} {%- endmacro %}
{% macro default__rs_chave(colunas, sep) -%} concat_ws('{{ sep }}', {{ colunas | join(', ') }}) {%- endmacro %}
{% macro bigquery__rs_chave(colunas, sep) -%}
array_to_string([{% for c in colunas %}cast({{ c }} as string){% if not loop.last %}, {% endif %}{% endfor %}], '{{ sep }}')
{%- endmacro %}
