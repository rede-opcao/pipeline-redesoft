"""Gera o projeto Power BI (PBIP) lendo as tabelas gold do warehouse.

Uso (na pasta do projeto):  python powerbi/gerar_pbip.py ["Nome do Projeto"]
Depois abra powerbi/<Nome>.pbip no Power BI Desktop e clique em Atualizar.
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import sys
NOME = sys.argv[1] if len(sys.argv) > 1 else "Dashboard Redesoft"
SERVIDOR = "localhost:5433"
BANCO = "warehouse"
RAIZ = Path(__file__).resolve().parent
SM = RAIZ / f"{NOME}.SemanticModel"
RP = RAIZ / f"{NOME}.Report"
S = "https://developer.microsoft.com/json-schemas/fabric"

# Colunas das tabelas gold: nome -> (tipo TMDL, resumir por)
TABELAS: dict[str, list[tuple[str, str, str]]] = {
    "dim_empresa": [("cod_empresa", "int64", "none"), ("nome_fantasia", "string", "none"),
                    ("razao_social", "string", "none"), ("cnpj", "string", "none"),
                    ("cidade", "string", "none"), ("uf", "string", "none"),
                    ("bandeira", "string", "none"), ("ativa", "boolean", "none")],
    "dim_tanque": [("chave_tanque", "string", "none"), ("cod_empresa", "int64", "none"),
                   ("nome_fantasia", "string", "none"), ("cod_tanque", "string", "none"),
                   ("cod_tipo_combustivel", "int64", "none"), ("combustivel", "string", "none"),
                   ("combustivel_apelido", "string", "none"), ("capacidade_litros", "double", "sum"),
                   ("redesoft_tank_id", "int64", "none"), ("veeder_root_tank_id", "int64", "none"),
                   ("ativo", "boolean", "none")],
    "fct_conciliacao_tanque_diario": [
        ("chave", "string", "none"), ("chave_tanque", "string", "none"), ("data", "dateTime", "none"),
        ("cod_empresa", "int64", "none"), ("cod_tanque", "string", "none"),
        ("volume_inicio", "double", "sum"), ("volume_recebido", "double", "sum"),
        ("consumo_medido", "double", "sum"), ("litros_vendidos", "double", "sum"),
        ("volume_fim", "double", "sum"), ("n_retratos", "int64", "sum"),
        ("teve_sonda_ausente", "boolean", "none"), ("saida_encerrante", "double", "sum"),
        ("afericao_litros", "double", "sum"), ("diferenca_litros", "double", "sum"),
        ("diferenca_pct", "double", "average"), ("status", "string", "none")],
    "fct_afericao_bico_turno": [
        ("cod_lmc_bico", "int64", "none"), ("cod_empresa", "int64", "none"), ("data", "dateTime", "none"),
        ("cod_caixa_abertura_turno", "int64", "none"), ("ordem", "int64", "none"), ("bico", "int64", "none"),
        ("chave_tanque", "string", "none"), ("cod_produto", "int64", "none"),
        ("encerrante_inicial", "double", "none"), ("encerrante_final", "double", "none"),
        ("saida_encerrante", "double", "sum"), ("afericao_litros", "double", "sum"),
        ("saida_liquida", "double", "sum"), ("litros_vendidos", "double", "sum"),
        ("n_abastecimentos", "int64", "sum"), ("diferenca_litros", "double", "sum")],
    "fct_pagamentos_diario": [
        ("chave", "string", "none"), ("data", "dateTime", "none"), ("cod_empresa", "int64", "none"),
        ("cod_forma_pagto", "int64", "none"), ("forma_pagamento", "string", "none"),
        ("n_pagamentos", "int64", "sum"), ("valor", "double", "sum")],
    "fct_vendas_diario": [
        ("chave", "string", "none"), ("data", "dateTime", "none"), ("cod_empresa", "int64", "none"),
        ("cod_produto", "int64", "none"), ("produto", "string", "none"), ("especie", "string", "none"),
        ("n_vendas", "int64", "sum"), ("quantidade", "double", "sum"), ("valor_total", "double", "sum")],
    "fct_vendas_tanque_diario": [
        ("chave", "string", "none"), ("data", "dateTime", "none"), ("cod_empresa", "int64", "none"),
        ("cod_tanque", "string", "none"), ("n_abastecimentos", "int64", "sum"),
        ("litros_vendidos", "double", "sum"), ("valor_total", "double", "sum")],
}

# Medidas: tabela -> [(nome, DAX, formato)]
MEDIDAS = {
    "fct_vendas_diario": [
        ("Faturamento", "SUM(fct_vendas_diario[valor_total])", "#,0.00"),
        ("Litros Combustível",
         'CALCULATE(SUM(fct_vendas_diario[quantidade]), fct_vendas_diario[especie] = "COMBUSTIVEL")', "#,0"),
    ],
    "fct_pagamentos_diario": [
        ("Recebido", "SUM(fct_pagamentos_diario[valor])", "#,0.00"),
    ],
    "fct_conciliacao_tanque_diario": [
        ("Diferença (L)", "SUM(fct_conciliacao_tanque_diario[diferenca_litros])", "#,0.0"),
        ("Diferença %",
         "DIVIDE(SUM(fct_conciliacao_tanque_diario[consumo_medido]) - SUM(fct_conciliacao_tanque_diario[litros_vendidos]),"
         " SUM(fct_conciliacao_tanque_diario[litros_vendidos]))", "0.00%"),
        ("Aferição (L)", "SUM(fct_conciliacao_tanque_diario[afericao_litros])", "#,0"),
        ("Dias fora da tolerância",
         'CALCULATE(COUNTROWS(fct_conciliacao_tanque_diario), fct_conciliacao_tanque_diario[status] = "fora_tolerancia")',
         "0"),
    ],
}

# (lado muitos, lado um)
RELACOES = [(f"{t}.cod_empresa", "dim_empresa.cod_empresa") for t in TABELAS if t.startswith("fct_")]
RELACOES += [(f"{t}.data", "Calendario.Data") for t in TABELAS if t.startswith("fct_")]
RELACOES += [("fct_conciliacao_tanque_diario.chave_tanque", "dim_tanque.chave_tanque")]


def tag() -> str:
    return str(uuid.uuid4())


def q(nome: str) -> str:
    """Nome TMDL: aspas simples quando tem espaço ou caractere especial."""
    return nome if nome.replace("_", "").isalnum() and nome.isascii() else "'" + nome.replace("'", "''") + "'"


def escrever(caminho: Path, conteudo: str | dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, dict):
        conteudo = json.dumps(conteudo, ensure_ascii=False, indent=2)
    caminho.write_text(conteudo, encoding="utf-8", newline="\n")


def tmdl_tabela(nome: str, colunas) -> str:
    L = [f"table {nome}", f"\tlineageTag: {tag()}", ""]
    for m, dax, fmt in MEDIDAS.get(nome, []):
        L += [f"\tmeasure {q(m)} = {dax}", f"\t\tformatString: {fmt}", f"\t\tlineageTag: {tag()}", ""]
    for col, tipo, resumo in colunas:
        L += [f"\tcolumn {col}", f"\t\tdataType: {tipo}"]
        if tipo == "dateTime":
            L.append("\t\tformatString: Short Date")
        L += [f"\t\tlineageTag: {tag()}", f"\t\tsummarizeBy: {resumo}", f"\t\tsourceColumn: {col}", "",
              "\t\tannotation SummarizationSetBy = Automatic", ""]
    L += [f"\tpartition {nome} = m", "\t\tmode: import", "\t\tsource =", "\t\t\t\tlet",
          f'\t\t\t\t    Fonte = PostgreSQL.Database("{SERVIDOR}", "{BANCO}"),',
          f'\t\t\t\t    Tabela = Fonte{{[Schema="gold",Item="{nome}"]}}[Data]',
          "\t\t\t\tin", "\t\t\t\t    Tabela", ""]
    return "\n".join(L)


def gerar_modelo() -> None:
    d = SM / "definition"
    escrever(SM / "definition.pbism", {
        "$schema": f"{S}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})
    escrever(d / "database.tmdl", "database\n\tcompatibilityLevel: 1601\n")
    nomes = list(TABELAS) + ["Calendario"]
    escrever(d / "model.tmdl", "\n".join([
        "model Model", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
        *[f"ref table {n}" for n in nomes], ""]))
    for nome, cols in TABELAS.items():
        escrever(d / "tables" / f"{nome}.tmdl", tmdl_tabela(nome, cols))
    escrever(d / "tables" / "Calendario.tmdl", "\n".join([
        "table Calendario", f"\tlineageTag: {tag()}", "",
        "\tcolumn Data", "\t\tdataType: dateTime", "\t\tformatString: Short Date",
        f"\t\tlineageTag: {tag()}", "\t\tsummarizeBy: none", "\t\tsourceColumn: [Data]", "",
        "\tpartition Calendario = calculated", "\t\tmode: import",
        '\t\tsource = SELECTCOLUMNS(CALENDARAUTO(), "Data", [Date])', ""]))
    escrever(d / "relationships.tmdl", "\n".join(
        f"relationship {tag()}\n\tfromColumn: {a}\n\ttoColumn: {b}\n" for a, b in RELACOES))


def campo(tabela: str, prop: str, medida: bool = False) -> dict:
    tipo = "Measure" if medida else "Column"
    return {"field": {tipo: {"Expression": {"SourceRef": {"Entity": tabela}}, "Property": prop}},
            "queryRef": f"{tabela}.{prop}", "nativeQueryRef": prop}


def visual(nome: str, tipo: str, x, y, w, h, papeis: dict, titulo: str | None = None) -> dict:
    v = {"visualType": tipo, "query": {"queryState": {
        papel: {"projections": projs} for papel, projs in papeis.items()}}}
    if titulo:
        v["visualContainerObjects"] = {"title": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": "'" + titulo.replace("'", "''") + "'"}}}}}]}
    return {"$schema": f"{S}/item/report/definition/visualContainer/2.0.0/schema.json",
            "name": nome, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}, "visual": v}


def gerar_relatorio() -> None:
    d = RP / "definition"
    escrever(RP / "definition.pbir", {
        "$schema": f"{S}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}}})
    escrever(d / "version.json", {"$schema": f"{S}/item/report/definition/versionMetadata/1.0.0/schema.json",
                                  "version": "2.0.0"})
    escrever(d / "report.json", {
        "$schema": f"{S}/item/report/definition/report/3.0.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "type": "SharedResources",
                                          "reportVersionAtImport": {"visual": "2.0.0", "page": "2.0.0",
                                                                    "report": "3.0.0"}}}})
    pagina = "visaogeral"
    escrever(d / "pages" / "pages.json", {
        "$schema": f"{S}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [pagina, "afericoes"], "activePageName": pagina})
    escrever(d / "pages" / pagina / "page.json", {
        "$schema": f"{S}/item/report/definition/page/2.0.0/schema.json",
        "name": pagina, "displayName": "Visão Geral", "displayOption": "FitToPage",
        "height": 720, "width": 1280})
    C, V, P = "fct_conciliacao_tanque_diario", "fct_vendas_diario", "fct_pagamentos_diario"
    visuais = [
        visual("filtroPosto", "slicer", 20, 20, 240, 390,
               {"Values": [campo("dim_empresa", "nome_fantasia")]}, "Posto"),
        visual("cardFaturamento", "card", 280, 20, 235, 110, {"Values": [campo(V, "Faturamento", True)]}),
        visual("cardLitros", "card", 525, 20, 235, 110, {"Values": [campo(V, "Litros Combustível", True)]}),
        visual("cardDiferenca", "card", 770, 20, 235, 110, {"Values": [campo(C, "Diferença %", True)]}),
        visual("cardForaTolerancia", "card", 1015, 20, 245, 110,
               {"Values": [campo(C, "Dias fora da tolerância", True)]}),
        visual("linhaFaturamento", "lineChart", 280, 140, 600, 270,
               {"Category": [campo("Calendario", "Data")], "Y": [campo(V, "Faturamento", True)]},
               "Faturamento por dia"),
        visual("rosquinhaPagamentos", "donutChart", 890, 140, 370, 270,
               {"Category": [campo(P, "forma_pagamento")], "Y": [campo(P, "Recebido", True)]},
               "Recebido por forma de pagamento"),
        visual("matrizConciliacao", "pivotTable", 20, 420, 760, 280,
               {"Rows": [campo(C, "chave_tanque")], "Columns": [campo("Calendario", "Data")],
                "Values": [campo(C, "Diferença %", True)]},
               "Conciliação tanque x bicos: diferença % por dia"),
        visual("barrasPerda", "clusteredBarChart", 790, 420, 470, 280,
               {"Category": [campo(C, "chave_tanque")], "Y": [campo(C, "Diferença (L)", True)]},
               "Saída no encerrante sem venda (L) por tanque"),
    ]
    A = "fct_afericao_bico_turno"
    pag2 = "afericoes"
    visuais2 = [
        visual("filtroPosto2", "slicer", 20, 20, 240, 680,
               {"Values": [campo("dim_empresa", "nome_fantasia")]}, "Posto"),
        visual("cardAfericao", "card", 280, 20, 320, 110, {"Values": [campo(C, "Aferição (L)", True)]}),
        visual("cardDifBico", "card", 610, 20, 320, 110, {"Values": [campo(C, "Diferença (L)", True)]}),
        visual("tabelaBicos", "tableEx", 280, 140, 980, 560,
               {"Values": [campo(A, "data"), campo("dim_empresa", "nome_fantasia"), campo(A, "bico"),
                           campo(A, "cod_caixa_abertura_turno"), campo(A, "saida_encerrante"),
                           campo(A, "afericao_litros"), campo(A, "litros_vendidos"), campo(A, "diferenca_litros")]},
               "Encerrante x aferição x vendido, por bico e turno"),
    ]
    escrever(d / "pages" / pag2 / "page.json", {
        "$schema": f"{S}/item/report/definition/page/2.0.0/schema.json",
        "name": pag2, "displayName": "Aferições por bico", "displayOption": "FitToPage",
        "height": 720, "width": 1280})
    for pg, lista in ((pagina, visuais), (pag2, visuais2)):
        for vis in lista:
            escrever(d / "pages" / pg / "visuals" / vis["name"] / "visual.json", vis)


def main() -> None:
    for p in (SM, RP):
        if p.exists():
            shutil.rmtree(p)
    gerar_modelo()
    gerar_relatorio()
    escrever(RAIZ / f"{NOME}.pbip", {
        "$schema": f"{S}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
        "artifacts": [{"report": {"path": f"{NOME}.Report"}}], "settings": {"enableAutoRecovery": True}})
    escrever(RAIZ / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    print(f"Gerado: {RAIZ / (NOME + '.pbip')}")


if __name__ == "__main__":
    main()
