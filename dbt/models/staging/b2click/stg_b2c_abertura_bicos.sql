-- Encerrantes por bico e turno (registro LMC do bico). afericao_litros = volume aferido e devolvido.
select
    {{ b2c_int('COD_LMC_BICO') }}             as cod_lmc_bico,
    {{ b2c_int('COD_EMPRESA') }}              as cod_empresa,
    {{ b2c_int('COD_PAF_BANCO') }}            as cod_paf_banco,   -- COD_LMC_BICO só é único por empresa + PAF
    {{ b2c_data('DATA') }}                    as data,
    {{ b2c_int('COD_CAIXA_ABERTURA_TURNO') }} as cod_caixa_abertura_turno,
    {{ b2c_int('ORDEM') }}                    as ordem,
    {{ b2c_int('COD_PRODUTO_TANQUE_BICO') }}  as bico,
    {{ b2c_int('COD_PRODUTO_TANQUE') }}       as cod_produto_tanque,
    {{ b2c_int('COD_PRODUTO') }}              as cod_produto,
    {{ b2c_num('LEITURA_INICIAL') }}          as encerrante_inicial,
    {{ b2c_num('LEITURA_FINAL') }}            as encerrante_final,
    {{ b2c_num('LEITURA_FINAL') }} - {{ b2c_num('LEITURA_INICIAL') }} as saida_encerrante,
    coalesce({{ b2c_num('AFERICAO') }}, 0)    as afericao_litros
from {{ source('raw_b2click', 'abertura_bicos') }}
