select
    (payload->>'codEmpresa')::int           as cod_empresa,
    (payload->>'codVenda')::int             as cod_venda,
    (payload->>'dataHoraVenda')::timestamp  as data_hora_venda,
    (payload->>'codAgente')::int            as cod_agente,
    (payload->>'numeroNf')::bigint          as numero_nf,
    (payload->>'serie')::int                as serie,
    (payload->>'valorTotal')::numeric       as valor_total
from ({{ deduplicado('vendas', "payload->>'codVenda', payload->>'codEmpresa'") }}) s
