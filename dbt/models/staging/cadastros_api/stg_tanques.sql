select
    (payload->>'codEmpresa')::int          as cod_empresa,
    payload->>'codTanque'                  as cod_tanque,
    (payload->>'codTipoCombustivel')::int  as cod_tipo_combustivel,
    (payload->>'capacidade')::int          as capacidade_litros,
    (payload->>'veederRootTankId')::int    as veeder_root_tank_id,
    (payload->>'redesoftTankId')::int      as redesoft_tank_id
from ({{ ultimo_snapshot('tanques') }}) s
