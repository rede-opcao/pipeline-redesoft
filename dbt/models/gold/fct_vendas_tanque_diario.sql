-- Litros que saíram pelos bicos, por tanque e dia.
-- Liga item vendido -> bico -> tanque pelo redesoftTankId.
-- PREMISSA A CONFIRMAR com dados reais: ItemVendido.bico corresponde a Bico.codigo.
select
    concat_ws('|', coalesce(i.data_hora_abastecimento, i.data_hora_venda)::date, i.cod_empresa, t.cod_tanque) as chave,
    coalesce(i.data_hora_abastecimento, i.data_hora_venda)::date as data,
    i.cod_empresa,
    t.cod_tanque,
    count(*)            as n_abastecimentos,
    sum(i.quantidade)   as litros_vendidos,
    sum(i.valor_total)  as valor_total
from {{ ref('stg_itens_vendidos') }} i
join {{ ref('stg_bicos') }} b
  on b.cod_empresa = i.cod_empresa and b.cod_bico = i.bico
join {{ ref('stg_tanques') }} t
  on t.cod_empresa = b.cod_empresa and t.redesoft_tank_id = b.redesoft_tank_id
where not i.cancelado
  and i.bico is not null
group by 2, 3, 4
