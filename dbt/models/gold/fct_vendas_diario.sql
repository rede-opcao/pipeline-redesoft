-- Vendas por dia, posto e produto (itens cancelados excluídos).
select
    concat_ws('|', i.data_hora_venda::date, i.cod_empresa, i.cod_produto) as chave,
    i.data_hora_venda::date        as data,
    i.cod_empresa,
    i.cod_produto,
    p.nome                         as produto,
    p.especie,
    count(distinct i.cod_venda)    as n_vendas,
    sum(i.quantidade)              as quantidade,
    sum(i.valor_total)             as valor_total
from {{ ref('stg_itens_vendidos') }} i
left join {{ ref('stg_produtos') }} p using (cod_produto)
where not i.cancelado
group by 2, 3, 4, 5, 6
