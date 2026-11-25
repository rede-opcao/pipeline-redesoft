-- Litros vendidos por tanque e dia (dia do turno do encerrante).
with agregado as (
    select
        data,
        cod_empresa,
        cast(cod_produto_tanque as {{ dbt.type_string() }}) as cod_tanque,
        sum(n_abastecimentos)             as n_abastecimentos,
        sum(litros_vendidos)              as litros_vendidos
    from {{ ref('fct_afericao_bico_turno') }}
    group by 1, 2, 3
)
select
    {{ rs_chave(['data', 'cod_empresa', 'cod_tanque']) }} as chave,
    data, cod_empresa, cod_tanque, n_abastecimentos, litros_vendidos,
    cast(null as numeric) as valor_total
from agregado
