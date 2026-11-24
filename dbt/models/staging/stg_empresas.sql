select
    (payload->>'codEmpresa')::int     as cod_empresa,
    payload->>'nomeFantasia'          as nome_fantasia,
    payload->>'razaoSocial'           as razao_social,
    payload->>'cnpj'                  as cnpj,
    payload->>'cidade'                as cidade,
    payload->>'uf'                    as uf,
    payload->>'bandeira'              as bandeira,
    (payload->>'ativa')::boolean      as ativa,
    (payload->>'coordenadorId')::int  as coordenador_id,
    (payload->>'gerenteId')::int      as gerente_id
from ({{ ultimo_snapshot('empresas') }}) s
