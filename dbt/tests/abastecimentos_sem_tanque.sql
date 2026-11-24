-- Aviso: abastecimentos cujo bico não foi ligado a nenhum tanque.
-- Se aparecer muita coisa aqui com dados reais, a premissa bico = Bico.codigo está errada.
{{ config(severity='warn') }}
select i.cod_empresa, i.bico, count(*) as n
from {{ ref('stg_itens_vendidos') }} i
left join {{ ref('stg_bicos') }} b
  on b.cod_empresa = i.cod_empresa and b.cod_bico = i.bico
left join {{ ref('stg_tanques') }} t
  on t.cod_empresa = b.cod_empresa and t.redesoft_tank_id = b.redesoft_tank_id
where i.bico is not null and not i.cancelado and t.cod_tanque is null
group by 1, 2
