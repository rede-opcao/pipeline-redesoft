select
    (payload->>'codEmpresa')::int                  as cod_empresa,
    payload->>'codTanque'                          as cod_tanque,
    (payload->>'periodoInicio')::timestamp::date   as data,
    (payload->>'volumeInicio')::numeric            as volume_inicio,
    (payload->>'volumeFim')::numeric               as volume_fim,
    (payload->>'consumoLiquido')::numeric          as consumo_liquido,
    (payload->>'volumeRecebido')::numeric          as volume_recebido,
    (payload->>'nRetratos')::int                   as n_retratos,
    (payload->>'teveSondaAusente')::boolean        as teve_sonda_ausente,
    (payload->>'ehFeriado')::boolean               as eh_feriado,
    (payload->>'diaDaSemana')::int                 as dia_da_semana
from ({{ deduplicado('medicoes_consumo',
      "payload->>'codEmpresa', payload->>'codTanque', payload->>'periodoInicio'") }}) s
