-- Medições registradas no LMC. A unidade de MEDICAO não está documentada (confirmar: litros ou cm).
select
    {{ b2c_int('COD_LMC_TANQUE_MEDICAO') }}  as cod_lmc_tanque_medicao,
    {{ b2c_int('COD_EMPRESA') }}             as cod_empresa,
    {{ b2c_int('COD_PRODUTO_TANQUE') }}      as cod_produto_tanque,
    {{ b2c_int('COD_PRODUTO') }}             as cod_produto,
    {{ b2c_ts('DATA', 'HORA') }}             as momento,
    {{ b2c_data('DATA') }}                   as data,
    {{ b2c_num('MEDICAO') }}                 as medicao,
    {{ b2c_int('TURNO') }}                   as turno
from {{ source('raw_b2click', 'medicao_tanques') }}
