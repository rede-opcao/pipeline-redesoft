-- Conciliação diária por tanque: consumo medido pelo Veeder-Root x litros vendidos nos bicos.
-- diferenca_litros > 0: saiu mais do tanque do que foi vendido (perda);
-- diferenca_litros < 0: vendeu mais do que saiu do tanque (sobra).
with consumo as (
    select * from {{ ref('stg_medicoes_consumo') }}
),
vendas as (
    select * from {{ ref('fct_vendas_tanque_diario') }}
),
base as (
    select
        coalesce(c.data, v.data)               as data,
        coalesce(c.cod_empresa, v.cod_empresa) as cod_empresa,
        coalesce(c.cod_tanque, v.cod_tanque)   as cod_tanque,
        c.volume_inicio,
        c.volume_recebido,
        c.consumo_liquido                      as consumo_medido,
        v.litros_vendidos,
        c.volume_fim,
        c.n_retratos,
        c.teve_sonda_ausente
    from consumo c
    full outer join vendas v
      on v.data = c.data and v.cod_empresa = c.cod_empresa and v.cod_tanque = c.cod_tanque
)
select
    concat_ws('|', data, cod_empresa, cod_tanque) as chave,
    cod_empresa || '-' || cod_tanque              as chave_tanque,
    base.*,
    consumo_medido - coalesce(litros_vendidos, 0) as diferenca_litros,
    case when litros_vendidos > 0
         then round(100 * (consumo_medido - litros_vendidos) / litros_vendidos, 3)
    end                                           as diferenca_pct,
    case
        when consumo_medido is null then 'sem_medicao'
        when litros_vendidos is null then 'sem_venda'
        when teve_sonda_ausente then 'sonda_ausente'
        when abs(100 * (consumo_medido - litros_vendidos) / nullif(litros_vendidos, 0))
             > {{ var('tolerancia_pct') }} then 'fora_tolerancia'
        else 'ok'
    end                                           as status
from base
