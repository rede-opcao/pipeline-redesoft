select
    (payload->>'codEmpresa')::int               as cod_empresa,
    payload->>'codTanque'                       as cod_tanque,
    (payload->>'momento')::timestamp            as momento,
    (payload->>'totalVolume')::numeric          as volume_litros,
    (payload->>'ullage')::numeric               as espaco_livre_litros,
    (payload->>'waterHeight')::numeric          as altura_agua,
    (payload->>'waterVolume')::numeric          as volume_agua,
    (payload->>'fuelTemperature')::numeric      as temperatura,
    (payload->>'isDeliveryInProgress')::boolean as descarga_em_andamento,
    (payload->>'isProbeOut')::boolean           as sonda_fora,
    (payload->>'hasAlarms')::boolean            as tem_alarme
from ({{ deduplicado('medicoes', "payload->>'codEmpresa', payload->>'codTanque', payload->>'momento'") }}) s
