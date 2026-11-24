-- Itens vendidos (abastecimentos e produtos). quantidade_liquida desconta cancelamentos parciais.
with base as (
    select
        {{ b2c_int('COD_EMPRESA') }}                as cod_empresa,
        {{ b2c_int('COD_VENDA') }}                  as cod_venda,
        {{ b2c_int('COD_VENDA_ITENS') }}            as cod_venda_itens,
        {{ b2c_int('COD_PAF_BANCO') }}              as cod_paf_banco,
        {{ b2c_int('COD_PRODUTO') }}                as cod_produto,
        {{ b2c_txt('ESPECIE') }}                    as especie_codigo,
        {{ b2c_txt('UNIDADE') }}                    as unidade,
        {{ b2c_num('QUANTIDADE') }}                 as quantidade,
        coalesce({{ b2c_num('QTD_CANCELADA') }}, 0) as qtd_cancelada,
        {{ b2c_num('PRECO') }}                      as preco_unitario,
        {{ b2c_num('TOTAL_ITEM') }}                 as valor_total,
        {{ b2c_num('PCUSTO') }}                     as preco_custo,
        {{ b2c_data('DATA_VENDA') }}                as data_venda,
        {{ b2c_ts('DATA_VENDA', 'HORA') }}          as data_hora_venda,
        {{ b2c_ts('DATA_ABASTECIMENTO', 'HORA_ABASTECIMENTO') }} as data_hora_abastecimento,
        {{ b2c_int('COD_CAIXA_ABERTURA_TURNO') }}   as cod_caixa_abertura_turno,
        {{ b2c_int('COD_ABASTECIMENTO') }}          as cod_abastecimento,
        {{ b2c_int('COD_LMC_BICO') }}               as cod_lmc_bico,
        {{ b2c_int('BICO') }}                       as bico,
        {{ b2c_bool('CANCELADO') }}                 as cancelado,
        {{ b2c_data('DATA') }}                      as data_ref
    from {{ source('raw_b2click', 'itens_vendidos') }}
)
select
    base.*,
    case when cancelado then 0 else greatest(quantidade - qtd_cancelada, 0) end as quantidade_liquida,
    case when cancelado or quantidade = 0 then 0
         else valor_total * greatest(quantidade - qtd_cancelada, 0) / quantidade end as valor_liquido
from base
