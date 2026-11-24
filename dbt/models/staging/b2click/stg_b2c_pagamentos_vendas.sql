select
    {{ b2c_int('COD_EMPRESA') }}               as cod_empresa,
    {{ b2c_int('COD_VENDA') }}                 as cod_venda,
    {{ b2c_int('COD_PAF_BANCO') }}             as cod_paf_banco,
    {{ b2c_int('COD_VENDA_FECHAMENTO') }}      as cod_venda_fechamento,
    {{ b2c_int('ORDEM') }}                     as ordem,
    {{ b2c_int('COD_FORMA_PAGTO') }}           as cod_forma_pagto,
    {{ b2c_num('VALOR') }}                     as valor,
    {{ b2c_num('TROCO') }}                     as troco,
    {{ b2c_int('TIPO') }}                      as tipo,
    {{ b2c_bool('CANCELADA') }} or {{ b2c_bool('CANCELADO') }} as cancelado,
    coalesce({{ b2c_data('DATA_VENDA') }}, {{ b2c_data('DATA') }}) as data_venda,
    {{ b2c_int('COD_CAIXA_ABERTURA_TURNO') }}  as cod_caixa_abertura_turno
from {{ source('raw_b2click', 'pagamentos_vendas') }}
