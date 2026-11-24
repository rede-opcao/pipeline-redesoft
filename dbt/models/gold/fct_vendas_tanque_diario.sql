-- Litros vendidos por tanque e dia (dia do turno do encerrante).
select
    concat_ws('|', data, cod_empresa, split_part(chave_tanque, '-', 2)) as chave,
    data,
    cod_empresa,
    split_part(chave_tanque, '-', 2)  as cod_tanque,
    sum(n_abastecimentos)             as n_abastecimentos,
    sum(litros_vendidos)              as litros_vendidos,
    null::numeric                     as valor_total
from {{ ref('fct_afericao_bico_turno') }}
group by 2, 3, 4
