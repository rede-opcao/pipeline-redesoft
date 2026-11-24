select
    (payload->>'codEmpresa')::int      as cod_empresa,
    (payload->>'codigo')::int          as cod_bico,
    (payload->>'redesoftTankId')::int  as redesoft_tank_id
from ({{ ultimo_snapshot('bicos') }}) s
