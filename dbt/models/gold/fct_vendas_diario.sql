-- Vendas por dia, posto e produto, já descontados cancelamentos.
select
    concat_ws('|', i.data_venda, i.cod_empresa, i.cod_produto) as chave,
    i.data_venda                         as data,
    i.cod_empresa,
    i.cod_produto,
    p.nome                               as produto,
    p.especie,
    count(distinct i.cod_venda)          as n_vendas,
    sum(i.quantidade_liquida)            as quantidade,
    sum(i.valor_liquido)                 as valor_total
from {{ ref('stg_b2c_itens_vendidos') }} i
left join {{ ref('stg_b2c_produtos') }} p using (cod_produto)
where i.data_venda is not null
group by 2, 3, 4, 5, 6
