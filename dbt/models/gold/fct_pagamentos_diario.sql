-- Recebimentos por dia, posto e forma de pagamento (cancelados excluídos).
with agregado as (
    select
        p.data_venda          as data,
        p.cod_empresa,
        p.cod_forma_pagto,
        f.nome                as forma_pagamento,
        count(*)              as n_pagamentos,
        sum(p.valor)          as valor
    from {{ ref('stg_b2c_pagamentos_vendas') }} p
    left join {{ ref('stg_b2c_formas_pagamento') }} f using (cod_forma_pagto)
    where not p.cancelado and p.data_venda is not null
    group by 1, 2, 3, 4
)
select {{ rs_chave(['data', 'cod_empresa', 'cod_forma_pagto']) }} as chave, agregado.*
from agregado
