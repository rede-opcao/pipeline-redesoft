select
    (payload->>'codProduto')::int       as cod_produto,
    (payload->>'codProdutoGrupo')::int  as cod_produto_grupo,
    payload->>'nome'                    as nome,
    payload->>'especie'                 as especie
from ({{ ultimo_snapshot('produtos') }}) s
