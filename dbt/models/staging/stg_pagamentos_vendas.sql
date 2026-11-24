select
    (payload->>'codEmpresa')::int             as cod_empresa,
    (payload->>'codVenda')::int               as cod_venda,
    (payload->>'codPafBanco')::int            as cod_paf_banco,
    (payload->>'codVendaFechamento')::int     as cod_venda_fechamento,
    (payload->>'ordem')::int                  as ordem,
    (payload->>'codFormaPagto')::int          as cod_forma_pagto,
    (payload->>'valor')::numeric              as valor,
    (payload->>'troco')::numeric              as troco,
    coalesce((payload->>'cancelada')::boolean, false)
      or coalesce((payload->>'cancelado')::boolean, false) as cancelado,
    (payload->>'dataVenda')::timestamp        as data_venda,
    (payload->>'codCaixaAberturaTurno')::int  as cod_caixa_abertura_turno
from ({{ deduplicado('pagamentos_vendas',
      "payload->>'codVenda', payload->>'codEmpresa', payload->>'codPafBanco', payload->>'codVendaFechamento', payload->>'ordem'") }}) s
