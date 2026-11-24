select
    t.cod_empresa || '-' || t.cod_produto_tanque  as chave_tanque,
    t.cod_empresa,
    e.nome_fantasia,
    t.cod_produto_tanque::text                    as cod_tanque,
    t.cod_produto                                 as cod_tipo_combustivel,
    p.nome                                        as combustivel,
    t.titulo                                      as combustivel_apelido,
    t.capacidade_litros,
    t.cod_produto_tanque                          as redesoft_tank_id,
    null::int                                     as veeder_root_tank_id,
    t.ativo
from {{ ref('stg_b2c_tanques') }} t
left join {{ ref('stg_b2c_produtos') }} p using (cod_produto)
left join {{ ref('stg_b2c_empresas') }} e using (cod_empresa)
