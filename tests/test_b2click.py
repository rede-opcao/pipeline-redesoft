"""Testes do extrator B2Click sem chamar a API. Rodar: python -m unittest discover tests"""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins"))

from redesoft.b2click import FONTES_B2C_POR_NOME, chamadas, ler_csv, separar_por_dia  # noqa: E402


class TestChamadas(unittest.TestCase):
    def test_dia_em_blocos_de_7(self):
        c = chamadas(FONTES_B2C_POR_NOME["itens_vendidos"], date(2026, 11, 1), date(2026, 11, 23))
        self.assertEqual(len(c), 4)  # 1-7, 8-14, 15-21, 22-23
        self.assertEqual(c[0][2], {"datainicial": "01112026", "datafinal": "07112026"})
        self.assertEqual(c[-1][:2], (date(2026, 11, 22), date(2026, 11, 23)))

    def test_carga_diaria_usa_uma_chamada(self):
        self.assertEqual(len(chamadas(FONTES_B2C_POR_NOME["itens_vendidos"], date(2026, 11, 21), date(2026, 11, 23))), 1)

    def test_mes_fechado_e_virada_de_mes(self):
        c = chamadas(FONTES_B2C_POR_NOME["abertura_bicos"], date(2026, 10, 30), date(2026, 11, 2))
        self.assertEqual([x[2] for x in c], [{"datainicial": "01102026", "datafinal": "31102026"},
                                              {"datainicial": "01112026", "datafinal": "30112026"}])
        self.assertEqual(c[0][0], date(2026, 10, 1))

    def test_cadastro(self):
        self.assertEqual(chamadas(FONTES_B2C_POR_NOME["bicos"], None, None), [(None, None, {})])


class TestSepararPorDia(unittest.TestCase):
    def test_todos_os_dias_presentes_mesmo_vazios(self):
        regs = [{"DATA": "21/11/2026"}, {"DATA": "21/11/2026"}, {"DATA": "23/11/2026"}]
        d = separar_por_dia(regs, "DATA", date(2026, 11, 21), date(2026, 11, 23))
        self.assertEqual({k: len(v) for k, v in d.items()},
                         {date(2026, 11, 21): 2, date(2026, 11, 22): 0, date(2026, 11, 23): 1})

    def test_data_invalida_vai_para_o_ultimo_dia(self):
        d = separar_por_dia([{"DATA": ""}], "DATA", date(2026, 11, 21), date(2026, 11, 22))
        self.assertEqual(len(d[date(2026, 11, 22)]), 1)


class TestCsv(unittest.TestCase):
    def test_bom_separador_e_descarte(self):
        corpo = "﻿A;B;SENHA\r\n1;2,5;x\r\n".encode("utf-8")
        self.assertEqual(ler_csv(corpo, frozenset({"SENHA"})), [{"A": "1", "B": "2,5"}])


if __name__ == "__main__":
    unittest.main()
