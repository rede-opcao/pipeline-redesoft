-- Um registro por bico e turno: o que saiu pelo encerrante, quanto foi aferido (e devolvido
-- ao tanque) e quanto foi vendido. diferenca_litros > 0 = saiu combustível sem venda registrada.
-- Chave do encerrante: empresa + banco do PDV (COD_PAF_BANCO) + COD_LMC_BICO.
-- A venda pode ser registrada em outro PDV, então a ligação venda -> encerrante usa
-- empresa + COD_LMC_BICO + dia (combinação única nos dados testados).
-- Só entram os dias em que os itens vendidos foram carregados.
with vendido as (
    select cod_empresa, cod_lmc_bico, data_venda,
           count(*)                  as n_abastecimentos,
           sum(quantidade_liquida)   as litros_vendidos
    from {{ ref('stg_b2c_itens_vendidos') }}
    where especie_codigo = 'C' and cod_lmc_bico is not null
    group by 1, 2, 3
),
dias_carregados as (
    select distinct cod_empresa, data_venda as data from {{ ref('stg_b2c_itens_vendidos') }}
)
select
    {{ rs_chave(['a.cod_empresa', 'a.cod_paf_banco', 'a.cod_lmc_bico'], '-') }} as chave,
    a.cod_lmc_bico,
    a.cod_paf_banco,
    a.cod_empresa,
    a.data,
    a.cod_caixa_abertura_turno,
    a.ordem,
    a.bico,
    {{ rs_chave(['a.cod_empresa', 'a.cod_produto_tanque'], '-') }}          as chave_tanque,
    a.cod_produto_tanque,
    a.cod_produto,
    a.encerrante_inicial,
    a.encerrante_final,
    a.saida_encerrante,
    a.afericao_litros,
    a.saida_encerrante - a.afericao_litros                  as saida_liquida,
    coalesce(v.litros_vendidos, 0)                          as litros_vendidos,
    coalesce(v.n_abastecimentos, 0)                         as n_abastecimentos,
    a.saida_encerrante - a.afericao_litros - coalesce(v.litros_vendidos, 0) as diferenca_litros
from {{ ref('stg_b2c_abertura_bicos') }} a
join dias_carregados d on d.cod_empresa = a.cod_empresa and d.data = a.data
left join vendido v
  on v.cod_empresa = a.cod_empresa and v.cod_lmc_bico = a.cod_lmc_bico and v.data_venda = a.data
