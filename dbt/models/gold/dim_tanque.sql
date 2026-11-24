select
    t.cod_empresa || '-' || t.cod_tanque  as chave_tanque,
    t.cod_empresa,
    e.nome_fantasia,
    t.cod_tanque,
    t.cod_tipo_combustivel,
    tc.nome                               as combustivel,
    tc.apelido                            as combustivel_apelido,
    t.capacidade_litros,
    t.redesoft_tank_id,
    t.veeder_root_tank_id
from {{ ref('stg_tanques') }} t
left join {{ ref('stg_tipos_combustivel') }} tc using (cod_tipo_combustivel)
left join {{ ref('stg_empresas') }} e using (cod_empresa)
