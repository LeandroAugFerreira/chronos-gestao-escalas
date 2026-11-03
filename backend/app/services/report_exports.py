"""Server-side formats for authorized report projections; no external I/O."""
from datetime import UTC, datetime
import io
import json
import re
import zipfile
import xlsxwriter
from app.api.dependencies import fail
from app.services.analytics import COLUMNS, MAX_BYTES
from app.services.csv_export import csv_bytes, safe_text


def column_type(column):
    if column in {"version", "revision", "attempt", "population_count", "assignment_count"} or column.endswith(("_minutes", "_cents")):
        return "Int64.Type"
    if column == "valid":
        return "type logical"
    if column in {"reference_month", "start_date", "end_date_exclusive", "month"}:
        return "type date"
    if column in {"started_at", "finished_at", "start_at", "end_at"}:
        return "type datetimezone"
    return "type text"


def power_query(columns):
    queries = ["// Chronos 1.0. Crie o parâmetro de texto PastaChronos apontando para a pasta extraída.",
        "// Crie uma consulta por bloco let. Valores textuais iniciados por fórmula têm apóstrofo de proteção."]
    for name, fields in columns.items():
        types = ", ".join('{"' + c + '", ' + column_type(c) + '}' for c in fields)
        queries.append(f'// Consulta: {name}\nlet\n  Fonte = Csv.Document(File.Contents(PastaChronos & "\\{name}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n  Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),\n  Nulos = Table.ReplaceValue(Cabecalhos, "", null, Replacer.ReplaceValue, Table.ColumnNames(Cabecalhos)),\n  Tipos = Table.TransformColumnTypes(Nulos, {{{types}}}, "en-US")\nin\n  Tipos\n')
    return "\n\n".join(queries)


def relationships(tables):
    result = [{"one": "units.unit_id", "many": "scenario.unit_id", "filter": "single"}]
    for name in ["coverage", "proposals", "assignments", "finance"]:
        if name in tables:
            result.append({"one": "scenario.scenario_id", "many": name + ".scenario_id", "filter": "single"})
    if "executions" in tables:
        result.append({"one": "units.unit_id", "many": "executions.unit_id", "filter": "single"})
    return result


def dataset_zip(report):
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, rows in report["tables"].items():
            archive.writestr(name + ".csv", csv_bytes(COLUMNS[name], rows))
        manifest = report["manifest"] | {"relationships": relationships(report["tables"]), "csv_protection": "Dangerous text prefixed with apostrophe; text may differ from source. Numeric types are unchanged."}
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("power-query.m", power_query(manifest["columns"]))
        measures = []
        if "coverage" in report["tables"]:
            measures += ["Cobertura % = DIVIDE(SUM(coverage[covered_staff_minutes]), SUM(coverage[required_staff_minutes]))"]
        if "finance" in report["tables"]:
            measures += ["Projecao BRL = DIVIDE(SUM(finance[total_cents]), 100)"]
        if "executions" in report["tables"]:
            measures += ["Tentativas = COUNTROWS(executions)"]
        archive.writestr("measures.dax", "\n".join(measures))
        archive.writestr("LEIA-ME.txt", "Chronos 1.0\n" + "\n".join(manifest["methodology"]) + "\n\n" +
            "Use um pacote por modelo. Substitua os arquivos juntos ao atualizar. Não acrescente extrações sobrepostas. " +
            "Importe as consultas M e configure somente os relacionamentos do manifest. IDs são chaves de texto. " +
            "O pacote já contém apenas os dados autorizados na extração. Após sair do Chronos, o arquivo não mantém o RBAC; proteja o armazenamento e configure RLS antes de compartilhar. " +
            "Nenhum PBIX ou publicação foi criado. Não contém credenciais nem conexão de rede. CSV vazio representa tabela sem fatos, não resultado zero.\n")
    return target.getvalue()


def workbook_bytes(report):
    target = io.BytesIO()
    book = xlsxwriter.Workbook(target, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    book.set_properties({"title": "Chronos 1.0 — Relatório", "company": "Chronos", "comments": report["manifest"]["data_sha256"]})
    title = book.add_format({"font_size": 18, "bold": True, "font_color": "#FFFFFF", "bg_color": "#102B35"})
    header = book.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#17685F", "text_wrap": True, "valign": "vcenter"})
    text = book.add_format({"font_name": "Calibri", "font_size": 11, "valign": "top", "text_wrap": True})
    note = book.add_format({"font_color": "#435A64", "text_wrap": True, "valign": "top", "font_size": 11})
    number = book.add_format({"num_format": "#,##0", "valign": "top"})
    percent = book.add_format({"num_format": "0.0%", "valign": "top"})
    date_format = book.add_format({"num_format": "yyyy-mm-dd", "valign": "top"})
    instant_format = book.add_format({"num_format": 'yyyy-mm-dd hh:mm "UTC"', "valign": "top"})
    summary = book.add_worksheet("Resumo")
    summary.hide_gridlines(2)
    summary.set_column("A:A", 43)
    summary.set_column("B:B", 24)
    summary.set_column("C:D", 22)
    summary.merge_range("A1:D2", "Chronos 1.0 — Analytics", title)
    scenario = report["tables"]["scenario"][0]
    summary.merge_range("A4:D4", f"Cenário v{scenario['version']} · {scenario['reference_month'][:7]} · {scenario['timezone']}", note)
    summary.merge_range("A5:D6", "Relatório da seleção. Capacidade e cobertura são calculadas; custos são projetados. Os dados de origem estão nas abas seguintes.", note)
    summary.write("A8", "Indicador", header); summary.write("B8", "Valor", header)
    row = 8
    formulas = [("Pessoas no cenário", "='scenario'!I5", scenario["population_count"], number),
        ("Orçamento de capacidade (min)", "='scenario'!L5", scenario["effective_budget_minutes"], number)]
    if report["tables"].get("coverage"):
        coverage = report["tables"]["coverage"][0]
        if coverage["required_staff_minutes"] is not None:
            ratio = coverage["covered_staff_minutes"] / coverage["required_staff_minutes"] if coverage["required_staff_minutes"] else "n.a."
            formulas.append(("Cobertura no horizonte (%)", '=IF(\'coverage\'!J5=0,"n.a.",\'coverage\'!K5/\'coverage\'!J5)', ratio, percent))
    if "finance" in report["tables"]:
        n = len(report["tables"]["finance"])
        formulas.append(("Projeção selecionada (centavos BRL)", f"=SUM('finance'!I5:I{4+n})", sum(r["total_cents"] for r in report["tables"]["finance"]), number))
    if "executions" in report["tables"]:
        n = len(report["tables"]["executions"])
        formulas.append(("Tentativas observadas de automação", f"=COUNTA('executions'!A5:A{4+n})" if n else "=0", n, number))
    for label, formula, value, fmt in formulas:
        if isinstance(value, int) and abs(value) >= 10**15:
            fail(422, "EXPORT_PRECISION", "Total excede a precisão segura do Excel. Use o pacote CSV.")
        summary.write_string(row, 0, label, text)
        summary.write_formula(row, 1, formula, fmt, value)
        row += 1
    row += 2
    summary.merge_range(row, 0, row, 3, "Método e fontes", header)
    for paragraph in report["manifest"]["methodology"]:
        row += 1
        summary.merge_range(row, 0, row + 1, 3, paragraph, note)
        summary.set_row(row, 24)
        row += 1
    row += 2
    summary.merge_range(row, 0, row + 1, 3, "Extraído em " + report["manifest"]["extracted_at"] + "\nSHA-256 dos dados: " + report["manifest"]["data_sha256"], note)
    summary.freeze_panes(8, 0)
    for name, rows in report["tables"].items():
        sheet = book.add_worksheet(name)
        columns = COLUMNS[name]
        sheet.hide_gridlines(2)
        sheet.merge_range(0, 0, 0, max(1, len(columns) - 1), "Chronos 1.0 — " + name, title)
        sheet.merge_range(1, 0, 1, max(1, len(columns) - 1), report["manifest"]["grains"][name], note)
        sheet.set_row(0, 30); sheet.set_row(1, 46); sheet.set_row(3, 52)
        sheet.freeze_panes(4, 0)
        for col, field in enumerate(columns):
            sheet.set_column(col, col, 68 if field.endswith("digest") else 40 if field.endswith("_id") or field in {"name", "name_at_extraction"} else max(25, len(field) + 3))
            sheet.write_string(3, col, field, header)
        for i, record in enumerate(rows, 4):
            long_name = max((len(str(record.get(field, ""))) for field in ["name", "name_at_extraction"] if field in columns), default=0)
            sheet.set_row(i, max(18, ((long_name + 35) // 36) * 16))
            for j, field in enumerate(columns):
                value = record.get(field)
                if isinstance(value, str):
                    if len(value) > 32767 or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value):
                        fail(422, "EXPORT_TEXT", "Texto incompatível com XLSX. Use o pacote CSV.")
                    if column_type(field) == "type date":
                        sheet.write_datetime(i, j, datetime.fromisoformat(value), date_format)
                    elif column_type(field) == "type datetimezone":
                        sheet.write_datetime(i, j, datetime.fromisoformat(value).astimezone(UTC).replace(tzinfo=None), instant_format)
                    else:
                        sheet.write_string(i, j, value, text)
                elif value is None:
                    sheet.write_blank(i, j, None, text)
                elif isinstance(value, bool):
                    sheet.write_boolean(i, j, value, text)
                else:
                    if abs(value) >= 10**15:
                        fail(422, "EXPORT_PRECISION", "Número excede a precisão segura do Excel. Use o pacote CSV.")
                    sheet.write_number(i, j, value, number)
        sheet.autofilter(3, 0, max(3, 3 + len(rows)), len(columns) - 1)
    book.close()
    return target.getvalue()


def export_bytes(report, format):
    content = workbook_bytes(report) if format == "xlsx" else dataset_zip(report)
    if len(content) > MAX_BYTES:
        fail(422, "REPORT_LIMIT", "Arquivo excede 8 MiB. Reduza a seleção.")
    return content
