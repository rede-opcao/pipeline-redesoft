"""Cliente HTTP da Cadastros API (somente leitura), sem dependências externas."""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

log = logging.getLogger(__name__)

STATUS_RETENTAVEIS = {429, 500, 502, 503, 504}


class CadastrosApiError(Exception):
    def __init__(self, status: int, url: str, corpo: str):
        super().__init__(f"HTTP {status} em {url}: {corpo[:300]}")
        self.status = status


class CadastrosClient:
    """Autentica por X-Api-Key (preferido, só leitura) ou OAuth2 client_credentials."""

    def __init__(self, base_url: str, api_key: str | None = None,
                 client_id: str | None = None, client_secret: str | None = None,
                 token_url: str | None = None, scope: str = "cadastros-api",
                 page_size: int = 200, timeout: int = 120, max_tentativas: int = 4):
        if not api_key and not (client_id and client_secret):
            raise ValueError("Informe CADASTROS_API_KEY ou CADASTROS_CLIENT_ID + CADASTROS_CLIENT_SECRET.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client_id, self.client_secret = client_id, client_secret
        self.token_url, self.scope = token_url, scope
        self.page_size, self.timeout, self.max_tentativas = page_size, timeout, max_tentativas
        self._token: str | None = None
        self._token_expira = 0.0

    # --- autenticação ---
    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.api_key:
            h["X-Api-Key"] = self.api_key
        else:
            h["Authorization"] = f"Bearer {self._obter_token()}"
        return h

    def _obter_token(self) -> str:
        if self._token and time.time() < self._token_expira - 60:
            return self._token
        corpo = urllib.parse.urlencode({
            "grant_type": "client_credentials", "client_id": self.client_id,
            "client_secret": self.client_secret, "scope": self.scope,
        }).encode()
        req = urllib.request.Request(self.token_url, data=corpo, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            dados = json.load(resp)
        self._token = dados["access_token"]
        self._token_expira = time.time() + int(dados.get("expires_in", 3600))
        return self._token

    # --- requisições ---
    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        for tentativa in range(1, self.max_tentativas + 1):
            req = urllib.request.Request(url, headers=self._headers(), method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                corpo = e.read().decode("utf-8", "replace")
                if e.code == 401 and not self.api_key:
                    self._token = None  # token expirado: renova e tenta de novo
                if e.code in STATUS_RETENTAVEIS | {401} and tentativa < self.max_tentativas:
                    log.warning("HTTP %s em %s (tentativa %s), repetindo", e.code, path, tentativa)
                    time.sleep(2 ** tentativa)
                    continue
                raise CadastrosApiError(e.code, url, corpo) from None
            except (urllib.error.URLError, TimeoutError) as e:
                if tentativa < self.max_tentativas:
                    log.warning("Falha de rede em %s: %s (tentativa %s)", path, e, tentativa)
                    time.sleep(2 ** tentativa)
                    continue
                raise
        raise RuntimeError("inalcançável")

    def iter_pages(self, path: str, params: dict[str, Any] | None = None) -> Iterator[list[dict]]:
        """Percorre todas as páginas de um PagedResultDto."""
        pagina = 1
        while True:
            dados = self.get_json(path, {**(params or {}), "page": pagina, "pageSize": self.page_size})
            itens = dados.get("items") or []
            if itens:
                yield itens
            total_paginas = dados.get("totalPages") or 0
            if not itens or pagina >= total_paginas:
                return
            pagina += 1
