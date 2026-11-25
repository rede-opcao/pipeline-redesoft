select
    {{ rs_chave(['t.cod_empresa', 't.cod_produto_tanque'], '-') }}  as chave_tanque,
    t.cod_empresa,
    e.nome_fantasia,
    cast(t.cod_produto_tanque as {{ dbt.type_string() }})   as cod_tanque,
    t.cod_produto                                            as cod_tipo_combustivel,
    p.nome                                                   as combustivel,
    t.titulo                                                 as combustivel_apelido,
    t.capacidade_litros,
    t.cod_produto_tanque                                     as redesoft_tank_id,
    cast(null as {{ dbt.type_int() }})                       as veeder_root_tank_id,
    t.ativo
from {{ ref('stg_b2c_tanques') }} t
left join {{ ref('stg_b2c_produtos') }} p using (cod_produto)
left join {{ ref('stg_b2c_empresas') }} e using (cod_empresa)
