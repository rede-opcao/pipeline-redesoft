select
    {{ b2c_int('COD_EMPRESA') }}                     as cod_empresa,
    {{ b2c_int('COD_CAIXA_ABERTURA_TURNO') }}        as cod_caixa_abertura_turno,
    {{ b2c_int('COD_PAF_BANCO') }}                   as cod_paf_banco,
    {{ b2c_int('TURNO') }}                           as turno,
    {{ b2c_ts('ABERTURA_DATA', 'ABERTURA_HORA') }}   as abertura,
    {{ b2c_ts('FECHAMENTO_DATA', 'FECHAMENTO_HORA') }} as fechamento,
    {{ b2c_num('FALTA_DE_CAIXA') }}                  as falta_de_caixa,
    {{ b2c_bool('PROCESSADO') }}                     as processado,
    {{ b2c_int('COD_AGENTE') }}                      as cod_agente
from {{ source('raw_b2click', 'caixas') }}
