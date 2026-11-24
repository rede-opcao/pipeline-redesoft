"""Catálogo das fontes extraídas da Cadastros API e configurações por ambiente.

Só rotas GET entram aqui. As rotas POST /import disparam rotinas no servidor
de produção e nunca devem ser chamadas pelo pipeline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fonte:
    nome: str                       # nome da tabela raw e da pasta no bronze
    path: str                       # rota da API ({codEmpresa} quando por_empresa)
    modo: str                       # "snapshot" (carga completa) ou "incremental" (por janela de datas)
    paginado: bool = True           # resposta PagedResultDto (items/totalPages) ou lista simples
    param_inicio: str | None = None
    param_fim: str | None = None
    janela_max_dias: int | None = None  # limite da API por chamada
    extra_params: dict = field(default_factory=dict)
    por_empresa: bool = False       # repete a chamada para cada empresa


FONTES: list[Fonte] = [
    # --- cadastros: pequenos, carga completa diária ---
    Fonte("empresas", "/api/empresas", "snapshot"),
    Fonte("tanques", "/api/empresas/{codEmpresa}/tanques", "snapshot", por_empresa=True),
    Fonte("bicos", "/api/bicos", "snapshot"),
    Fonte("produtos", "/api/produtos", "snapshot"),
    Fonte("tipos_combustivel", "/api/tipos-combustivel", "snapshot"),
    Fonte("formas_pagamento", "/api/formas-de-pagamento", "snapshot"),
    # --- movimento: incremental por janela de datas ---
    Fonte("itens_vendidos", "/api/itens-vendidos", "incremental",
          param_inicio="dataInicio", param_fim="dataFim", janela_max_dias=31),
    Fonte("vendas", "/api/vendas", "incremental",
          param_inicio="dataInicio", param_fim="dataFim", janela_max_dias=31),
    Fonte("pagamentos_vendas", "/api/pagamentos-de-vendas", "incremental",
          param_inicio="dataInicio", param_fim="dataFim", janela_max_dias=31),
    Fonte("caixas", "/api/caixas", "incremental",
          param_inicio="dataInicio", param_fim="dataFim", janela_max_dias=31,
          extra_params={"incluirDeletados": "true"}),
    Fonte("medicoes", "/api/medicoes", "incremental",
          param_inicio="de", param_fim="ate", janela_max_dias=31),
    # Consumo diário já calculado pela API (descarga separada do consumo líquido).
    # "Dia" é o nome do enum GranularidadeConsumoMedicao; confirmar com a equipe da API.
    Fonte("medicoes_consumo", "/api/medicoes/consumo", "incremental", paginado=False,
          param_inicio="de", param_fim="ate", janela_max_dias=366,
          extra_params={"granularidade": "Dia"}),
]

FONTES_POR_NOME = {f.nome: f for f in FONTES}


@dataclass(frozen=True)
class Settings:
    modo_api: str             # "mock" (dados simulados) ou "real"
    api_url: str
    api_key: str | None
    client_id: str | None
    client_secret: str | None
    token_url: str
    scope: str
    page_size: int
    bronze_uri: str           # pasta local ou s3://bucket/prefixo
    warehouse_dsn: str | None
    dias_reprocessamento: int

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        return cls(
            modo_api=env("CADASTROS_API_MODE", "mock").lower(),
            api_url=env("CADASTROS_API_URL", "https://cadastros.postosopcao.com.br"),
            api_key=env("CADASTROS_API_KEY") or None,
            client_id=env("CADASTROS_CLIENT_ID") or None,
            client_secret=env("CADASTROS_CLIENT_SECRET") or None,
            token_url=env("CADASTROS_TOKEN_URL", "https://auth.postosopcao.com.br/connect/token"),
            scope=env("CADASTROS_SCOPE", "cadastros-api"),
            page_size=int(env("CADASTROS_PAGE_SIZE", "200")),
            bronze_uri=env("BRONZE_URI", "data/bronze"),
            warehouse_dsn=env("WAREHOUSE_DSN") or None,
            dias_reprocessamento=int(env("DIAS_REPROCESSAMENTO", "3")),
        )
