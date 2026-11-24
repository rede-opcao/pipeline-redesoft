select
    (payload->>'codEmpresa')::int             as cod_empresa,
    (payload->>'codCaixaAberturaTurno')::int  as cod_caixa_abertura_turno,
    (payload->>'codPafBanco')::int            as cod_paf_banco,
    (payload->>'turno')::int                  as turno,
    (payload->>'abertura')::timestamp         as abertura,
    (payload->>'fechamento')::timestamp       as fechamento,
    (payload->>'faltaDeCaixa')::numeric       as falta_de_caixa,
    (payload->>'processado')::boolean         as processado,
    (payload->>'deletado')::boolean           as deletado
from ({{ deduplicado('caixas',
      "payload->>'codEmpresa', payload->>'codCaixaAberturaTurno', payload->>'codPafBanco'") }}) s
