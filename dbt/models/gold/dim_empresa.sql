select cod_empresa, nome_fantasia, razao_social, cnpj, cidade, uf,
       cast(null as {{ dbt.type_string() }}) as bandeira, ativa
from {{ ref('stg_b2c_empresas') }}
