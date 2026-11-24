select
    {{ b2c_int('COD_EMPRESA') }}         as cod_empresa,
    {{ b2c_int('CODIGO') }}              as bico,
    {{ b2c_int('COD_PRODUTO_TANQUE') }}  as cod_produto_tanque
from {{ source('raw_b2click', 'bicos') }}
