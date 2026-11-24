-- Aviso: abastecimentos de combustível cujo COD_LMC_BICO não aparece nos encerrantes (aberturaBicos).
-- Esses litros ficam fora da conciliação por tanque.
{{ config(severity='warn') }}
select i.cod_empresa, i.data_venda, count(*) as n, sum(i.quantidade_liquida) as litros
from {{ ref('stg_b2c_itens_vendidos') }} i
left join {{ ref('stg_b2c_abertura_bicos') }} a
  on a.cod_empresa = i.cod_empresa and a.cod_lmc_bico = i.cod_lmc_bico and a.data = i.data_venda
where i.especie_codigo = 'C' and a.cod_lmc_bico is null
group by 1, 2
