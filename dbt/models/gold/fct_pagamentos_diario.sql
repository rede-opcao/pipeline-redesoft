-- Recebimentos por dia, posto e forma de pagamento (cancelados excluídos).
select
    concat_ws('|', p.data_venda::date, p.cod_empresa, p.cod_forma_pagto) as chave,
    p.data_venda::date          as data,
    p.cod_empresa,
    p.cod_forma_pagto,
    f.nome                      as forma_pagamento,
    count(*)                    as n_pagamentos,
    sum(p.valor)                as valor
from {{ ref('stg_pagamentos_vendas') }} p
left join {{ ref('stg_formas_pagamento') }} f using (cod_forma_pagto)
where not p.cancelado
group by 2, 3, 4, 5
