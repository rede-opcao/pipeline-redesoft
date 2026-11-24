select cod_empresa, nome_fantasia, razao_social, cnpj, cidade, uf, bandeira, ativa
from {{ ref('stg_empresas') }}
