-- Conciliação diária por tanque, com dados reais do B2Click:
--   consumo_medido  = saída nos encerrantes - aferições (o que realmente saiu para clientes)
--   litros_vendidos = soma dos abastecimentos vendidos nesses bicos
--   diferenca_litros > 0: saiu mais pelo bico do que foi vendido; < 0: vendeu mais do que o encerrante marcou.
-- volume_inicio/volume_fim vêm do estoque físico do LMC. Recebimentos (descargas) ainda não entram.
with bicos as (
    select data, cod_empresa, cod_produto_tanque,
           sum(saida_encerrante)  as saida_encerrante,
           sum(afericao_litros)   as afericao_litros,
           sum(saida_liquida)     as consumo_medido,
           sum(litros_vendidos)   as litros_vendidos
    from {{ ref('fct_afericao_bico_turno') }}
    group by 1, 2, 3
),
lmc as (
    select data, cod_empresa, cod_produto_tanque,
           sum(estoque_abertura) as volume_inicio, sum(estoque_fechamento) as volume_fim
    from {{ ref('stg_b2c_tanque_lmc') }}
    group by 1, 2, 3
),
medicoes as (
    select data, cod_empresa, cod_produto_tanque, count(*) as n_retratos
    from {{ ref('stg_b2c_medicao_tanques') }}
    group by 1, 2, 3
)
select
    {{ rs_chave(['b.data', 'b.cod_empresa', 'b.cod_produto_tanque']) }}  as chave,
    {{ rs_chave(['b.cod_empresa', 'b.cod_produto_tanque'], '-') }}       as chave_tanque,
    b.data,
    b.cod_empresa,
    cast(b.cod_produto_tanque as {{ dbt.type_string() }})                as cod_tanque,
    l.volume_inicio,
    cast(null as numeric)                         as volume_recebido,
    b.consumo_medido,
    b.litros_vendidos,
    l.volume_fim,
    coalesce(m.n_retratos, 0)                     as n_retratos,
    false                                         as teve_sonda_ausente,
    b.saida_encerrante,
    b.afericao_litros,
    b.consumo_medido - b.litros_vendidos          as diferenca_litros,
    case when b.litros_vendidos > 0
         then round(100 * (b.consumo_medido - b.litros_vendidos) / b.litros_vendidos, 3) end as diferenca_pct,
    case
        when b.litros_vendidos = 0 and b.consumo_medido = 0 then 'sem_movimento'
        when b.litros_vendidos = 0 then 'sem_venda'
        when abs(100 * (b.consumo_medido - b.litros_vendidos) / b.litros_vendidos)
             > {{ var('tolerancia_pct') }} then 'fora_tolerancia'
        else 'ok'
    end                                           as status
from bicos b
left join lmc l
  on l.data = b.data and l.cod_empresa = b.cod_empresa and l.cod_produto_tanque = b.cod_produto_tanque
left join medicoes m
  on m.data = b.data and m.cod_empresa = b.cod_empresa and m.cod_produto_tanque = b.cod_produto_tanque
