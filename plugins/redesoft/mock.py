"""API simulada no formato dos DTOs do guia da Cadastros API.

Serve para desenvolver e testar o pipeline sem credencial. Os dados são
fictícios e determinísticos (mesma data gera os mesmos números), e as
vendas por bico batem com as medições dos tanques, com uma perda anômala
proposital no posto 3, tanque T01, para aparecer nos dashboards.
"""
from __future__ import annotations

import random
import re
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

from .client import CadastrosApiError, CadastrosClient

EMPRESAS = [
    (1, "Posto Teste Centro", "João Pessoa"),
    (2, "Posto Teste Litoral", "João Pessoa"),
    (3, "Posto Teste Interior", "Campina Grande"),
]
TIPOS = {1: ("Gasolina Comum", "GC"), 2: ("Etanol", "ET"), 3: ("Diesel S10", "S10")}
PRECOS = {1: 6.29, 2: 4.39, 3: 6.09}
TANQUES = [("T01", 1, 30000), ("T02", 2, 15000), ("T03", 3, 30000)]  # codTanque, tipo, capacidade
BICOS_POR_TANQUE = 2
FORMAS = [(1, "Dinheiro"), (2, "Cartão Débito"), (3, "Cartão Crédito"), (4, "PIX")]
FMT = "%Y-%m-%dT%H:%M:%S"


def _tank_id(emp: int, i: int) -> int:
    return emp * 100 + i


def _dias(inicio: str, fim: str) -> list[date]:
    a, b = datetime.fromisoformat(inicio).date(), datetime.fromisoformat(fim).date()
    return [a + timedelta(days=n) for n in range((b - a).days + 1)]


def _empresa_dto(emp: int, nome: str, cidade: str) -> dict:
    return {"codEmpresa": emp, "codigo": emp, "nomeFantasia": nome, "razaoSocial": f"{nome} Ltda",
            "cnpj": f"{emp:08d}000100", "cidade": cidade, "uf": "PB", "ativa": True,
            "veederRootUrl": None, "veederRootLogin": None, "veederRootPassword": None}


def _tanque_dto(emp: int, i: int) -> dict:
    cod, tipo, cap = TANQUES[i - 1]
    return {"codTanque": cod, "codEmpresa": emp, "codTipoCombustivel": tipo, "capacidade": cap,
            "qrCode": f"00000000-0000-0000-0000-{_tank_id(emp, i):012d}",
            "veederRootTankId": i, "redesoftTankId": _tank_id(emp, i)}


@lru_cache(maxsize=4096)
def _movimento(emp: int, dia: date) -> dict[str, Any]:
    """Vendas, pagamentos, caixas e estoque de um posto em um dia."""
    rng = random.Random(f"{emp}-{dia.isoformat()}")
    base_venda = (dia.toordinal() - 738000) * 10000
    itens, vendas, pagamentos = [], [], []
    vendido = {i: 0.0 for i in range(1, len(TANQUES) + 1)}
    seq = 0
    for i, (_, tipo, _) in enumerate(TANQUES, start=1):
        for _ in range(rng.randint(40, 90)):
            seq += 1
            cod_venda = base_venda + seq
            bico = (i - 1) * BICOS_POR_TANQUE + rng.randint(1, BICOS_POR_TANQUE)
            hora = datetime.combine(dia, datetime.min.time()) + timedelta(minutes=rng.randint(6 * 60, 22 * 60 - 1))
            litros = round(rng.uniform(10, 60), 3)
            cancelado = rng.random() < 0.02
            turno = 1 if hora.hour < 14 else 2
            item = {
                "codVendaItens": 1, "codEmpresa": emp, "codVenda": cod_venda, "codPafBanco": 1,
                "codProduto": 1000 + tipo, "quantidade": litros, "preco": PRECOS[tipo],
                "totalItem": round(litros * PRECOS[tipo], 2), "dataHoraVenda": hora.strftime(FMT),
                "cancelado": cancelado, "unidade": "L", "especie": "COMBUSTIVEL",
                "codCaixaAberturaTurno": dia.toordinal() * 10 + turno, "codAbastecimento": cod_venda,
                "dataHoraAbastecimento": hora.strftime(FMT), "precoVenda": PRECOS[tipo],
                "bico": bico, "codLmcBico": bico, "item": 1, "data": dia.strftime(FMT),
            }
            venda_itens = [item]
            if rng.random() < 0.1:  # conveniência junto
                venda_itens.append({**item, "codVendaItens": 2, "codProduto": 2001, "quantidade": 1,
                                    "preco": 3.5, "totalItem": 3.5, "unidade": "UN", "especie": "CONVENIENCIA",
                                    "codAbastecimento": None, "dataHoraAbastecimento": None,
                                    "bico": None, "codLmcBico": None, "item": 2})
            if not cancelado:
                vendido[i] += litros
            total = round(sum(x["totalItem"] for x in venda_itens), 2)
            itens.extend(venda_itens)
            vendas.append({"codVenda": cod_venda, "dataHoraVenda": hora.strftime(FMT), "codEmpresa": emp,
                           "codAgente": None, "cpfCnpj": None, "numeroNf": cod_venda, "serie": 1,
                           "cupom": cod_venda, "valorTotal": total, "itensVendidos": venda_itens})
            forma = rng.choice(FORMAS)[0]
            pagamentos.append({"codVenda": cod_venda, "codEmpresa": emp, "codPafBanco": 1,
                               "codVendaFechamento": 1, "cancelada": cancelado, "ordem": 1,
                               "codFormaPagto": forma, "valor": total, "valorForma": total, "troco": 0.0,
                               "dataVenda": hora.strftime(FMT), "codCaixaAberturaTurno": item["codCaixaAberturaTurno"],
                               "tipo": 0, "cancelado": cancelado, "codAgente": None,
                               "data": dia.strftime(FMT), "momento": hora.strftime(FMT)})
    caixas = [{"codEmpresa": emp, "codCaixaAberturaTurno": dia.toordinal() * 10 + t, "codPafBanco": 1,
               "processado": True, "editado": False,
               "abertura": (datetime.combine(dia, datetime.min.time()) + timedelta(hours=6 + 8 * (t - 1))).strftime(FMT),
               "fechamento": (datetime.combine(dia, datetime.min.time()) + timedelta(hours=14 + 8 * (t - 1))).strftime(FMT),
               "faltaDeCaixa": round(rng.uniform(-20, 5), 2), "turno": t, "deletado": False}
              for t in (1, 2)]

    estoque = {}
    for i, (cod, tipo, cap) in enumerate(TANQUES, start=1):
        perda_pct = 0.015 if (emp, cod) == (3, "T01") else rng.uniform(-0.002, 0.003)
        consumo = vendido[i] * (1 + perda_pct)
        recebido = (cap // 3) if (dia.toordinal() + emp + i) % 3 == 0 else 0
        inicio = cap * 0.35 + ((dia.toordinal() * 7 + emp * 3 + i) % 10) * cap * 0.03
        estoque[i] = {"inicio": inicio, "consumo": consumo, "recebido": float(recebido)}
    return {"itens": itens, "vendas": vendas, "pagamentos": pagamentos, "caixas": caixas, "estoque": estoque}


def _medicoes(emp: int, nome: str, dia: date) -> list[dict]:
    out = []
    for i, (cod, tipo, cap) in enumerate(TANQUES, start=1):
        e = _movimento(emp, dia)["estoque"][i]
        for h in range(24):
            frac = min(max((h - 6) / 16, 0), 1)
            receb = e["recebido"] * (1 if h >= 11 else 0.5 if h == 10 else 0)
            vol = e["inicio"] - e["consumo"] * frac + receb
            momento = datetime.combine(dia, datetime.min.time()) + timedelta(hours=h)
            out.append({
                "codigo": emp * 10**8 + (dia.toordinal() % 10000) * 10**4 + i * 100 + h,
                "codEmpresa": emp, "codTanque": cod, "veederRootTankId": i, "tankName": TIPOS[tipo][0],
                "totalVolume": round(vol, 2), "ullage": round(cap - vol, 2), "waterHeight": 0.0,
                "fuelHeight": None, "fuelTemperature": 27.5, "hasAlarms": False, "hasWarnings": False,
                "isProbeOut": False, "isDeliveryInProgress": h == 10 and e["recebido"] > 0,
                "momento": momento.strftime(FMT), "nomeFantasia": nome, "capacidade": cap,
                "codTipoCombustivel": tipo, "apelidoTipoCombustivel": TIPOS[tipo][1],
                "nomeTipoCombustivel": TIPOS[tipo][0],
            })
    return out


def _consumo(emp: int, nome: str, dia: date) -> list[dict]:
    out = []
    for i, (cod, tipo, cap) in enumerate(TANQUES, start=1):
        e = _movimento(emp, dia)["estoque"][i]
        out.append({
            "codEmpresa": emp, "nomeFantasia": nome, "codTanque": cod, "veederRootTankId": i,
            "tankName": TIPOS[tipo][0], "capacidade": cap, "codTipoCombustivel": tipo,
            "apelidoTipoCombustivel": TIPOS[tipo][1], "nomeTipoCombustivel": TIPOS[tipo][0],
            "periodoInicio": f"{dia}T00:00:00", "periodoFim": f"{dia + timedelta(days=1)}T00:00:00",
            "volumeInicio": round(e["inicio"], 2),
            "volumeFim": round(e["inicio"] - e["consumo"] + e["recebido"], 2),
            "consumoLiquido": round(e["consumo"], 2), "volumeRecebido": e["recebido"],
            "nRetratos": 24, "teveSondaAusente": False, "diaDaSemana": (dia.weekday() + 1) % 7,
            "ehFeriado": False, "nomeFeriado": None, "tipoDia": 0,
        })
    return out


class MockCadastrosClient(CadastrosClient):
    def __init__(self, page_size: int = 200, **_ignorado):
        self.page_size = page_size

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        p = dict(params or {})
        if m := re.fullmatch(r"/api/empresas/(\d+)/tanques", path):
            emp = int(m.group(1))
            return self._pagina([_tanque_dto(emp, i) for i in range(1, len(TANQUES) + 1)], p)
        if path == "/api/empresas":
            return self._pagina([_empresa_dto(*e) for e in EMPRESAS], p)
        if path == "/api/bicos":
            return self._pagina([{"codigo": (i - 1) * BICOS_POR_TANQUE + b, "codEmpresa": emp,
                                  "redesoftTankId": _tank_id(emp, i)}
                                 for emp, _, _ in EMPRESAS for i in range(1, len(TANQUES) + 1)
                                 for b in range(1, BICOS_POR_TANQUE + 1)], p)
        if path == "/api/produtos":
            prods = [{"codProduto": 1000 + t, "codProdutoGrupo": 10, "nome": n, "especie": "COMBUSTIVEL"}
                     for t, (n, _) in TIPOS.items()]
            prods.append({"codProduto": 2001, "codProdutoGrupo": 20, "nome": "Água mineral 500ml",
                          "especie": "CONVENIENCIA"})
            return self._pagina(prods, p)
        if path == "/api/tipos-combustivel":
            return self._pagina([{"codTipoCombustivel": t, "nome": n, "apelido": a, "descricao": None,
                                  "ativo": True} for t, (n, a) in TIPOS.items()], p)
        if path == "/api/formas-de-pagamento":
            return self._pagina([{"codFormaPagto": c, "codigo": c, "nome": n, "tipo": c, "ativo": True,
                                  "dias": 0, "quantClientes": 0} for c, n in FORMAS], p)

        janelas = {"/api/itens-vendidos": ("dataInicio", "dataFim", 31, "itens"),
                   "/api/vendas": ("dataInicio", "dataFim", 31, "vendas"),
                   "/api/pagamentos-de-vendas": ("dataInicio", "dataFim", 31, "pagamentos"),
                   "/api/caixas": ("dataInicio", "dataFim", 31, "caixas"),
                   "/api/medicoes": ("de", "ate", None, "medicoes"),
                   "/api/medicoes/consumo": ("de", "ate", 366, "consumo")}
        if path in janelas:
            pi, pf, limite, tipo = janelas[path]
            if pi not in p or pf not in p:
                raise CadastrosApiError(400, path, "período obrigatório (mock)")
            ini, fim = datetime.fromisoformat(p[pi]), datetime.fromisoformat(p[pf])
            if limite and (fim - ini) > timedelta(days=limite):
                raise CadastrosApiError(400, path, f"período superior a {limite} dias")
            regs: list[dict] = []
            for dia in _dias(p[pi], p[pf]):
                for emp, nome, _ in EMPRESAS:
                    if tipo == "medicoes":
                        regs += _medicoes(emp, nome, dia)
                    elif tipo == "consumo":
                        regs += _consumo(emp, nome, dia)
                    else:
                        regs += _movimento(emp, dia)[tipo]
            return regs if tipo == "consumo" else self._pagina(regs, p)
        raise CadastrosApiError(404, path, "rota não simulada")

    @staticmethod
    def _pagina(regs: list[dict], p: dict) -> dict:
        page, size = int(p.get("page", 1)), int(p.get("pageSize", 50))
        total_pages = max(1, -(-len(regs) // size))
        return {"items": regs[(page - 1) * size: page * size], "totalCount": len(regs),
                "page": page, "pageSize": size, "totalPages": total_pages}
