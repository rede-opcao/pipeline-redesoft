select
    (payload->>'codTipoCombustivel')::int  as cod_tipo_combustivel,
    payload->>'nome'                       as nome,
    payload->>'apelido'                    as apelido,
    (payload->>'ativo')::boolean           as ativo
from ({{ ultimo_snapshot('tipos_combustivel') }}) s
