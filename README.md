# Pipeline Redesoft

Carga diária dos dados do **Redesoft/B2Click** para um data lake, com transformação em dbt e
consumo no **Power BI**.

## Fonte ativa: API B2Click (retaguarda) — DAG `b2click_diario`

- Credenciais no `.env`: `B2CLICK_ENTIDADE`, `B2CLICK_USUARIO`, `B2CLICK_TOKEN` (nunca no código).
- Respostas em CSV (`;`, vírgula decimal, datas dd/mm/aaaa), gravadas como vieram no bronze
  (`data/bronze/b2click/...`) e no schema `raw_b2click` (uma linha por registro, texto).
- Tipos de rota: **cadastros** (completos), **diárias** (`itensVendidos`, `pagamentosDeVendas`,
  até 7 dias por chamada) e **mensais** (`aberturaBicos`, `tanqueLMC`, `medicaoTanques`, `Caixa`:
  a API só aceita mês fechado, do dia 1 ao último dia).
- **Limite da API: 10 requisições/hora por endpoint para a entidade inteira**, dividido com
  outros usos (relatórios do Power BI que chamam a API direto). A carga diária usa 1 chamada por
  endpoint; ao atingir o limite o extrator espera a próxima hora. Carga histórica: ~5 chamadas/mês.
- Chave do encerrante: empresa + `COD_PAF_BANCO` + `COD_LMC_BICO`. A venda liga ao encerrante por
  empresa + `COD_LMC_BICO` + dia (a venda pode estar em outro PDV).
- Gold novo: `fct_afericao_bico_turno` (encerrante × aferição × vendido por bico/turno). A
  conciliação por tanque usa **saída no encerrante − aferição** contra **litros vendidos**.
- Teste manual de todos os endpoints: `python scripts/testar_b2click.py --data 2026-11-01`
  (atenção: consome 1 requisição de cada endpoint).

A **Cadastros API** (DAG `redesoft_diario`, sem agendamento) fica como alternativa para quando a
chave dela chegar.

```
Cadastros API ─► Airflow (02:00) ─► bronze (JSON .jsonl.gz, local ou S3)
                       │
                       └─► raw (Postgres, JSON) ─► dbt: staging ─► gold ─► Power BI
```

| Camada | Onde | O que tem |
|---|---|---|
| bronze | `data/bronze/<fonte>/dt=<data>/` ou `s3://…` | resposta da API como veio, para reprocessar sem chamar a API |
| raw | schema `raw` do warehouse | o mesmo JSON, append-only, 1 tabela por fonte |
| staging | schema `staging` (views) | colunas tipadas, sem duplicatas |
| gold | schema `gold` (tabelas) | o que o Power BI consome |

## Tabelas gold

- `dim_empresa`, `dim_tanque`
- `fct_vendas_diario`: dia × posto × produto (quantidade, valor, nº de vendas)
- `fct_vendas_tanque_diario`: litros saídos pelos bicos, por tanque e dia
- `fct_pagamentos_diario`: dia × posto × forma de pagamento
- `fct_conciliacao_tanque_diario`: **consumo medido no Veeder-Root × litros vendidos nos bicos**,
  com `diferenca_litros`, `diferenca_pct` e `status` (`ok`, `fora_tolerancia`, `sem_medicao`,
  `sem_venda`, `sonda_ausente`). A tolerância fica em `dbt/dbt_project.yml` (`tolerancia_pct`).

## Rodar sem Docker (só a extração)

```powershell
python -m unittest discover tests
python scripts/run_local.py --inicio 2026-11-20 --fim 2026-11-22
```

Sem configuração, usa a **API simulada** (`CADASTROS_API_MODE=mock`): dados fictícios no formato
dos DTOs do guia, com uma perda proposital no posto 3, tanque T01, para testar a conciliação.

## Rodar completo (Docker Desktop)

1. Instale o Docker Desktop.
2. `copy .env.example .env` e troque `WAREHOUSE_PASSWORD` e `AIRFLOW__API_AUTH__JWT_SECRET`.
3. `docker compose up -d --build`
4. Abra http://localhost:8080, ative a DAG `redesoft_diario` e dispare uma execução.
5. Power BI / DBeaver: Postgres em `localhost:5433`, banco `warehouse`, usuário `warehouse`.

## Quando a chave da API chegar

No `.env`: `CADASTROS_API_MODE=real` e `CADASTROS_API_KEY=<chave>` (ou `CADASTROS_CLIENT_ID` +
`CADASTROS_CLIENT_SECRET`). Primeiro teste fora do Airflow, com um dia só e só cadastros:

```powershell
$env:CADASTROS_API_MODE="real"; $env:CADASTROS_API_KEY="<chave>"
python scripts/run_local.py --fontes empresas tanques bicos
```

**Carga histórica:** na interface, "Trigger DAG w/ config" com
`{"data_inicio": "2026-01-01", "data_fim": "2026-10-31"}`. A janela é fatiada em pedaços de até
31 dias automaticamente.

## A confirmar com dados reais

- [ ] `ItemVendido.bico` corresponde a `Bico.codigo`? (o teste `abastecimentos_sem_tanque` avisa se não)
- [ ] `granularidade=Dia` é aceito em `/api/medicoes/consumo` (o enum é publicado só como 0/1)
- [ ] Tamanho máximo de `pageSize` aceito pela API (hoje 200)
- [ ] Como aferições aparecem nos itens vendidos (afetam a conciliação)
- [ ] Datas da API sem fuso: assumidas como horário de Brasília

## Ida para a AWS (planejado)

- EC2 (`t3.medium`/`t3.large`, Linux) com este mesmo `docker compose`
- `BRONZE_URI=s3://<bucket>/bronze` (a EC2 precisa de IAM role com `s3:PutObject` no bucket)
- Warehouse em RDS PostgreSQL (troca `WAREHOUSE_DSN`/`WAREHOUSE_HOST`) e remoção do serviço `warehouse` do compose
- Remover `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS` e configurar login
- Power BI Service: verificar se o acesso ao RDS exige gateway

## Segurança

- Pipeline **só faz GET**. Nunca chamar as rotas `POST …/import` (disparam rotinas na produção).
- `.env` e `data/` estão no `.gitignore`. Chaves nunca vão para o código.
- A API devolve login e senha do Veeder-Root dentro do cadastro de empresas. O pipeline remove
  esses campos **antes** de gravar qualquer coisa (bronze e raw).
