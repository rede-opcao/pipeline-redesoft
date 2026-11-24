select cod_empresa, nome_fantasia, razao_social, cnpj, cidade, uf, null::text as bandeira, ativa
from {{ ref('stg_b2c_empresas') }}
