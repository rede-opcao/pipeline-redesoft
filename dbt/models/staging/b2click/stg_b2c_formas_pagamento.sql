select
    {{ b2c_int('COD_FORMA_PAGTO') }}  as cod_forma_pagto,
    {{ b2c_txt('NOME') }}             as nome,
    {{ b2c_int('TIPO') }}             as tipo,
    {{ b2c_bool('ATIVO') }}           as ativo
from {{ source('raw_b2click', 'formas_pagamento') }}
