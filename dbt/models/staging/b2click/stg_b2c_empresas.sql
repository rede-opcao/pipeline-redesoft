select
    {{ b2c_int('COD_EMPRESA') }}    as cod_empresa,
    {{ b2c_txt('NOME_FANTASIA') }}  as nome_fantasia,
    {{ b2c_txt('RAZAO_SOCIAL') }}   as razao_social,
    {{ b2c_txt('CNPJ') }}           as cnpj,
    {{ b2c_txt('CIDADE') }}         as cidade,
    {{ b2c_txt('UF') }}             as uf,
    {{ b2c_bool('ATIVA') }}         as ativa
from {{ source('raw_b2click', 'empresas') }}
