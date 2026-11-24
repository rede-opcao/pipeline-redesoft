select
    (payload->>'codFormaPagto')::int  as cod_forma_pagto,
    payload->>'nome'                  as nome,
    (payload->>'tipo')::int           as tipo,
    (payload->>'ativo')::boolean      as ativo
from ({{ ultimo_snapshot('formas_pagamento') }}) s
