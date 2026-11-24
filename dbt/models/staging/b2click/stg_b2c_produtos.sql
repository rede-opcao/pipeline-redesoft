select
    p.cod_produto,
    p.cod_produto_grupo,
    g.nome_grupo,
    p.nome,
    p.especie_codigo,
    case p.especie_codigo when 'C' then 'COMBUSTIVEL' when 'P' then 'PRODUTO' when 'S' then 'SERVICO'
         else p.especie_codigo end as especie
from (
    select
        {{ b2c_int('COD_PRODUTO') }}        as cod_produto,
        {{ b2c_int('COD_PRODUTO_GRUPO') }}  as cod_produto_grupo,
        {{ b2c_txt('NOME') }}               as nome,
        {{ b2c_txt('ESPECIE') }}            as especie_codigo
    from {{ source('raw_b2click', 'produtos') }}
) p
left join (
    select {{ b2c_int('COD_PRODUTO_GRUPO') }} as cod_produto_grupo, {{ b2c_txt('NOME') }} as nome_grupo
    from {{ source('raw_b2click', 'grupos_produto') }}
) g using (cod_produto_grupo)
