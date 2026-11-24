"""Testes da extração com a API simulada. Rodar: python -m unittest discover tests"""
import gzip
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins"))

from redesoft.client import CadastrosApiError  # noqa: E402
from redesoft.config import FONTES_POR_NOME, Settings  # noqa: E402
from redesoft.mock import MockCadastrosClient  # noqa: E402
from redesoft.pipeline import executar_fonte, extrair, janelas  # noqa: E402


class TestJanelas(unittest.TestCase):
    def test_fatia_em_31_dias(self):
        j = janelas(date(2026, 1, 1), date(2026, 3, 15), 31)
        self.assertEqual(j[0], (date(2026, 1, 1), date(2026, 1, 31)))
        self.assertEqual(j[-1][1], date(2026, 3, 15))
        for a, b in j:
            self.assertLessEqual((b - a).days + 1, 31)
        # contínuo, sem buracos nem sobreposição
        for (_, b), (a2, _) in zip(j, j[1:]):
            self.assertEqual((a2 - b).days, 1)

    def test_sem_limite(self):
        self.assertEqual(janelas(date(2026, 1, 1), date(2026, 12, 31), None),
                         [(date(2026, 1, 1), date(2026, 12, 31))])

    def test_fim_antes_do_inicio(self):
        with self.assertRaises(ValueError):
            janelas(date(2026, 2, 1), date(2026, 1, 1), 31)


class TestExtracao(unittest.TestCase):
    def setUp(self):
        self.client = MockCadastrosClient(page_size=50)  # página pequena força paginação

    def test_mock_recusa_janela_maior_que_31_dias(self):
        with self.assertRaises(CadastrosApiError):
            self.client.get_json("/api/itens-vendidos", {"dataInicio": "2026-01-01T00:00:00",
                                                         "dataFim": "2026-03-01T23:59:59"})

    def test_incremental_longo_fatiado_e_paginado(self):
        f = FONTES_POR_NOME["itens_vendidos"]
        regs = extrair(self.client, f, date(2026, 1, 1), date(2026, 2, 10))
        chaves = {(r["codVendaItens"], r["codVenda"], r["codEmpresa"], r["codPafBanco"]) for r in regs}
        self.assertEqual(len(chaves), len(regs), "paginação duplicou ou perdeu registros")
        dias = {r["dataHoraVenda"][:10] for r in regs}
        self.assertEqual(len(dias), 41)

    def test_snapshot_por_empresa(self):
        regs = extrair(self.client, FONTES_POR_NOME["tanques"], empresas=[1, 2, 3])
        self.assertEqual(len(regs), 9)

    def test_consumo_bate_com_vendas_nos_bicos(self):
        """Na simulação, o consumo medido = vendido x (1 + perda); só o posto 3/T01 foge da tolerância."""
        dia = date(2026, 11, 10)
        bicos = {(b["codEmpresa"], b["codigo"]): b["redesoftTankId"]
                 for b in extrair(self.client, FONTES_POR_NOME["bicos"])}
        tanques = {(t["codEmpresa"], t["redesoftTankId"]): t["codTanque"]
                   for t in extrair(self.client, FONTES_POR_NOME["tanques"], empresas=[1, 2, 3])}
        vendido: dict = {}
        for i in extrair(self.client, FONTES_POR_NOME["itens_vendidos"], dia, dia):
            if i["bico"] is None or i["cancelado"]:
                continue
            chave = (i["codEmpresa"], tanques[(i["codEmpresa"], bicos[(i["codEmpresa"], i["bico"])])])
            vendido[chave] = vendido.get(chave, 0) + i["quantidade"]
        fora = []
        for c in extrair(self.client, FONTES_POR_NOME["medicoes_consumo"], dia, dia):
            chave = (c["codEmpresa"], c["codTanque"])
            pct = 100 * (c["consumoLiquido"] - vendido[chave]) / vendido[chave]
            if abs(pct) > 0.6:
                fora.append(chave)
        self.assertEqual(fora, [(3, "T01")])


class TestBronze(unittest.TestCase):
    def test_grava_jsonl_gz(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Settings(**{**Settings.from_env().__dict__, "modo_api": "mock",
                            "bronze_uri": tmp, "warehouse_dsn": None})
            r = executar_fonte("medicoes", "teste:1", date(2026, 11, 1), date(2026, 11, 2), settings=s)
            caminho = Path(r["bronze"])
            self.assertTrue(caminho.exists())
            self.assertIn("dt=2026-11-02", str(caminho))
            with gzip.open(caminho, "rt", encoding="utf-8") as fh:
                linhas = [json.loads(x) for x in fh]
            self.assertEqual(len(linhas), r["registros"])
            self.assertEqual(len(linhas), 2 * 3 * 3 * 24)  # dias x postos x tanques x horas


if __name__ == "__main__":
    unittest.main()
