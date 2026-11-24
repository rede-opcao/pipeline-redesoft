-- Estoque físico (medido) de abertura e fechamento por tanque e dia, conforme o LMC.
select
    {{ b2c_int('COD_LMC_TANQUE') }}               as cod_lmc_tanque,
    {{ b2c_int('COD_EMPRESA') }}                  as cod_empresa,
    {{ b2c_int('COD_PRODUTO_TANQUE') }}           as cod_produto_tanque,
    {{ b2c_int('COD_PRODUTO') }}                  as cod_produto,
    {{ b2c_data('DATA') }}                        as data,
    {{ b2c_num('ESTOQUE_FISICO_ABERTURA') }}      as estoque_abertura,
    {{ b2c_num('ESTOQUE_FISICO_FECHAMENTO') }}    as estoque_fechamento,
    {{ b2c_num('ESTOQUE_FISICO_FECH_ANTES') }}    as estoque_fechamento_anterior,
    {{ b2c_bool('PROCESSADO') }}                  as processado
from {{ source('raw_b2click', 'tanque_lmc') }}
