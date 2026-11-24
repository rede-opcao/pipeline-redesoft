select
    {{ b2c_int('COD_EMPRESA') }}         as cod_empresa,
    {{ b2c_int('COD_PRODUTO_TANQUE') }}  as cod_produto_tanque,
    {{ b2c_int('COD_PRODUTO') }}         as cod_produto,
    {{ b2c_num('CAPACIDADE') }}          as capacidade_litros,
    {{ b2c_txt('TITULO') }}              as titulo,
    coalesce({{ b2c_txt('TITULO') }}, '') <> 'INATIVO' as ativo
from {{ source('raw_b2click', 'tanques') }}
