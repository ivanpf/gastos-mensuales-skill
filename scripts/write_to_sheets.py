#!/usr/bin/env python3
"""
Escribe movimientos ya categorizados a un Google Sheet, todo en una sola
pestaña por mes (ej. "Agosto"):
  - Tabla de movimientos arriba (Fecha, Concepto, Monto con signo,
    Categoría, Subcategoría, Referencia).
  - Tabla de resumen debajo, con un subtotal por categoría y el total
    general, con formato para distinguirlos a simple vista.

Requiere:
  pip install -r requirements.txt

Setup de las credenciales: ver SETUP.md en la raíz del proyecto.

Soporta combinar movimientos de más de un banco/tarjeta en la misma pestaña:
pasá varios CSV (uno por banco/cuenta, formato de scripts/movs_csv.py) y la
tabla de Movimientos los agrupa con una fila separadora por banco (usa la
columna "banco" de cada movimiento).

Uso:
    python write_to_sheets.py <movimientos_categorizados.csv> [otro.csv ...] \\
        --categories ../categories.json \\
        --sheet-id <ID_DEL_GOOGLE_SHEET> \\
        --credentials service_account.json
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from movs_csv import read_movs

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import ValidationConditionType
from gspread_formatting import (
    Border,
    Borders,
    CellFormat,
    Color,
    TextFormat,
    format_cell_range,
    set_column_widths,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MOVS_HEADER = ["Fecha", "Concepto", "Monto", "Categoría", "Subcategoría", "Referencia"]
RESUMEN_HEADER = ["Categoría", "Subcategoría", "Total"]

# Ancho de columnas en píxeles: A=Fecha, B=Concepto, C=Monto, D=Categoría,
# E=Subcategoría, F=Referencia. Concepto bien ancha para que el texto no
# quede muy alto al hacer wrap.
COLUMN_WIDTHS = [("A", 95), ("B", 420), ("C", 90), ("D", 190), ("E", 160), ("F", 130)]

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

HEADER_FORMAT = CellFormat(
    backgroundColor=Color(0.26, 0.26, 0.26),
    textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
)
SUBTOTAL_FORMAT = CellFormat(
    backgroundColor=Color(0.85, 0.85, 0.85),
    textFormat=TextFormat(bold=True),
)
TOTAL_FORMAT = CellFormat(
    backgroundColor=Color(0.71, 0.71, 0.71),
    textFormat=TextFormat(bold=True),
)
REFERENCIA_FORMAT = CellFormat(
    textFormat=TextFormat(foregroundColor=Color(0.75, 0.75, 0.75)),
)
REFERENCIA_HEADER_FORMAT = CellFormat(
    backgroundColor=Color(1, 1, 1),
    textFormat=TextFormat(bold=True, foregroundColor=Color(0.6, 0.6, 0.6)),
)
CONCEPTO_FORMAT = CellFormat(
    wrapStrategy="WRAP",
    verticalAlignment="MIDDLE",
)
VERTICAL_MIDDLE_FORMAT = CellFormat(
    verticalAlignment="MIDDLE",
)
BANCO_COLOR_DEFAULT = Color(0.87, 0.91, 0.98)  # celeste, para bancos sin color asignado
BANCO_COLORES = {
    "santander": Color(0.96, 0.70, 0.70),   # rojo
    "oca": Color(0.70, 0.82, 0.96),         # azul
    "prex": Color(0.85, 0.72, 0.94),        # violeta
    "mercado pago": Color(0.99, 0.92, 0.60),  # amarillo
}


def banco_format(banco):
    color = BANCO_COLORES.get(banco.strip().lower(), BANCO_COLOR_DEFAULT)
    return CellFormat(
        backgroundColor=color,
        textFormat=TextFormat(bold=True, italic=True),
        horizontalAlignment="CENTER",
    )
EGRESOS_TITLE_FORMAT = CellFormat(
    backgroundColor=Color(0.96, 0.80, 0.80),
    textFormat=TextFormat(bold=True),
    horizontalAlignment="CENTER",
)
INGRESOS_TITLE_FORMAT = CellFormat(
    backgroundColor=Color(0.80, 0.93, 0.80),
    textFormat=TextFormat(bold=True),
    horizontalAlignment="CENTER",
)
CATEGORIA_WRAP_FORMAT = CellFormat(
    wrapStrategy="WRAP",
)
TOTAL_AJUSTADO_FORMAT = CellFormat(
    backgroundColor=Color(0.80, 0.86, 0.98),
    textFormat=TextFormat(bold=True, italic=True),
)
_BLACK_BORDER = Border("SOLID", Color(0, 0, 0))
BORDER_FORMAT = CellFormat(
    borders=Borders(top=_BLACK_BORDER, bottom=_BLACK_BORDER, left=_BLACK_BORDER, right=_BLACK_BORDER),
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fecha_ddmmyyyy(fecha_iso):
    y, m, d = fecha_iso.split("-")
    return f"{d}/{m}/{y}"


def mes_de(fecha_iso):
    y, m, d = fecha_iso.split("-")
    return MESES[int(m) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("movimientos_csv", nargs="+",
                     help="Uno o más CSV de movimientos ya categorizados (formato de scripts/movs_csv.py, "
                          "con columnas 'categoria' y 'subcategoria' completas). "
                          "Pasar varios para combinar distintos bancos/tarjetas en la misma pestaña.")
    ap.add_argument("--categories", required=True, help="Path a categories.json")
    ap.add_argument("--sheet-id", required=True, help="ID del Google Sheet (de la URL)")
    ap.add_argument("--credentials", default="service_account.json")
    ap.add_argument("--worksheet-name", default=None,
                     help="Nombre de la pestaña. Default: nombre del mes del primer movimiento (ej. 'Agosto')")
    args = ap.parse_args()

    movimientos = []
    for path in args.movimientos_csv:
        movimientos.extend(read_movs(path))
    if not movimientos:
        raise ValueError("El CSV de movimientos está vacío.")

    cat_data = load_json(args.categories)
    categorias_dict = cat_data["categorias"]
    categorias = list(categorias_dict.keys())
    subcategorias = list(dict.fromkeys(
        sub for subs in categorias_dict.values() for sub in subs
    ))

    for m in movimientos:
        cat = m.get("categoria")
        sub = m.get("subcategoria")
        if cat not in categorias_dict:
            raise ValueError(
                f"Movimiento sin categoría válida: {m.get('concepto')!r} "
                f"(categoria={cat!r}). "
                "Todos los movimientos deben tener una categoría de la lista antes de subir."
            )
        if sub not in categorias_dict[cat]:
            raise ValueError(
                f"Movimiento sin subcategoría válida: {m.get('concepto')!r} "
                f"(categoria={cat!r}, subcategoria={sub!r}). "
                f"Subcategorías válidas para {cat!r}: {categorias_dict[cat]}."
            )

    creds = Credentials.from_service_account_file(args.credentials, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(args.sheet_id)

    ws_name = args.worksheet_name or mes_de(movimientos[0]["fecha"])
    n_cols = max(len(MOVS_HEADER), len(RESUMEN_HEADER))

    # --- Tabla de movimientos, agrupada por banco (respeta el orden de aparición) ---
    bancos_orden = list(dict.fromkeys(m["banco"] for m in movimientos))

    mov_rows = [MOVS_HEADER]
    banco_row_idxs = []  # [(índice 0-based, nombre del banco), ...] filas separadoras de banco
    for banco in bancos_orden:
        mov_rows.append([banco, "", "", "", "", ""])
        banco_row_idxs.append((len(mov_rows) - 1, banco))
        for m in movimientos:
            if m["banco"] != banco:
                continue
            signo = -1 if m["tipo"] == "debito" else 1
            mov_rows.append([
                fecha_ddmmyyyy(m["fecha"]),
                m["concepto"],
                round(signo * m["monto"], 2),
                m["categoria"],
                m["subcategoria"],
                m.get("referencia", ""),
            ])

    mov_start = 1  # fila 1 (1-indexed)
    mov_end = mov_start + len(mov_rows) - 1

    gap = 2  # una fila en blanco entre tablas

    # --- Tabla de resumen: Egresos (todas las categorías salvo Ingresos). Los créditos en estas
    # categorías son reintegros/descuentos de una compra (ej. "PROMOCIONES...DESC DECATHLON"),
    # no ingresos reales. Se muestran como una línea negativa aparte (no mezclada en un solo
    # número) para que el neteo se vea en la tabla, no quede escondido en el cálculo. ---
    debitos_por_cat_sub = defaultdict(float)
    creditos_por_cat_sub = defaultdict(float)
    for m in movimientos:
        if m["categoria"] == "Ingresos":
            continue
        key = (m["categoria"], m["subcategoria"])
        if m["tipo"] == "debito":
            debitos_por_cat_sub[key] += m["monto"]
        else:
            creditos_por_cat_sub[key] += m["monto"]

    # Para el cálculo de "Total sin transferencias propias" (neto).
    gastos_por_cat_sub = defaultdict(float)
    for key, val in debitos_por_cat_sub.items():
        gastos_por_cat_sub[key] += val
    for key, val in creditos_por_cat_sub.items():
        gastos_por_cat_sub[key] -= val

    resumen_rows = [["Egresos", "", ""], RESUMEN_HEADER]
    subtotal_row_idxs = []  # índices dentro de resumen_rows (0-based)
    total_general = 0.0
    for cat in categorias:
        if cat == "Ingresos":
            continue
        subtotal_cat = 0.0
        for sub in categorias_dict[cat]:
            debito = debitos_por_cat_sub.get((cat, sub), 0)
            credito = creditos_por_cat_sub.get((cat, sub), 0)
            if debito:
                resumen_rows.append([cat, sub, round(debito, 2)])
            if credito:
                resumen_rows.append([cat, sub, round(-credito, 2)])
            subtotal_cat += debito - credito
        if subtotal_cat:
            resumen_rows.append(["Subtotal", "", round(subtotal_cat, 2)])
            subtotal_row_idxs.append(len(resumen_rows) - 1)
            total_general += subtotal_cat
    resumen_rows.append(["TOTAL", "", round(total_general, 2)])
    total_row_idx = len(resumen_rows) - 1

    transferencias_propias = gastos_por_cat_sub.get(("Transferencias enviadas", "Propias"), 0)
    if transferencias_propias:
        resumen_rows.append([
            "Total sin transferencias propias", "", round(total_general - transferencias_propias, 2),
        ])
        total_sin_propias_row_idx = len(resumen_rows) - 1
    else:
        total_sin_propias_row_idx = None

    resumen_start = mov_end + gap
    resumen_end = resumen_start + len(resumen_rows) - 1

    # --- Tabla de resumen: Ingresos (categoría "Ingresos", desglosada por subcategoría) ---
    ingresos_por_sub = defaultdict(float)
    for m in movimientos:
        if m["categoria"] == "Ingresos" and m["tipo"] == "credito":
            ingresos_por_sub[m["subcategoria"]] += m["monto"]

    ingresos_rows = [["Ingresos", "", ""], RESUMEN_HEADER]
    total_ingresos = 0.0
    for sub in categorias_dict.get("Ingresos", []):
        total = ingresos_por_sub.get(sub, 0)
        if total:
            ingresos_rows.append(["Ingresos", sub, round(total, 2)])
            total_ingresos += total
    ingresos_rows.append(["TOTAL", "", round(total_ingresos, 2)])
    ingresos_total_row_idx = len(ingresos_rows) - 1

    ingresos_propios = ingresos_por_sub.get("Transferencia recibida propia", 0)
    if ingresos_propios:
        ingresos_rows.append([
            "Total sin transferencias propias", "", round(total_ingresos - ingresos_propios, 2),
        ])
        ingresos_total_sin_propias_row_idx = len(ingresos_rows) - 1
    else:
        ingresos_total_sin_propias_row_idx = None

    ingresos_start = resumen_end + gap
    ingresos_end = ingresos_start + len(ingresos_rows) - 1

    last_row = ingresos_end

    # Recrear la pestaña desde cero si ya existe: ws.clear() solo borra
    # valores, no formato, y eso dejaba colores de corridas anteriores
    # "pisando" filas que cambiaron de rol entre una corrida y otra.
    # Se crea la nueva antes de borrar la vieja porque un Sheet no puede
    # quedarse sin ninguna pestaña.
    old_ws = None
    try:
        old_ws = sh.worksheet(ws_name)
    except gspread.WorksheetNotFound:
        pass
    ws = sh.add_worksheet(title=f"{ws_name} (nuevo)" if old_ws else ws_name, rows=last_row, cols=n_cols)
    if old_ws:
        sh.del_worksheet(old_ws)
        ws.update_title(ws_name)

    ws.update(values=mov_rows, range_name=f"A{mov_start}")
    ws.update(values=resumen_rows, range_name=f"A{resumen_start}")
    ws.update(values=ingresos_rows, range_name=f"A{ingresos_start}")

    set_column_widths(ws, COLUMN_WIDTHS)

    # --- Dropdowns (data validation) ---
    mov_data_end = mov_end
    ws.add_validation(
        f"D{mov_start + 1}:D{mov_data_end}",
        ValidationConditionType.one_of_list,
        categorias,
        showCustomUi=True,
    )
    ws.add_validation(
        f"E{mov_start + 1}:E{mov_data_end}",
        ValidationConditionType.one_of_list,
        subcategorias,
        showCustomUi=True,
    )

    # --- Formato visual ---
    # Centrado vertical en toda la tabla primero (no pisa los demás atributos:
    # cada llamada a format_cell_range solo toca los campos que trae ese CellFormat).
    format_cell_range(ws, f"A{mov_start}:F{last_row}", VERTICAL_MIDDLE_FORMAT)

    format_cell_range(ws, f"A{mov_start}:F{mov_start}", HEADER_FORMAT)
    format_cell_range(ws, f"F{mov_start}", REFERENCIA_HEADER_FORMAT)
    format_cell_range(ws, f"F{mov_start + 1}:F{mov_data_end}", REFERENCIA_FORMAT)
    format_cell_range(ws, f"B{mov_start + 1}:B{mov_data_end}", CONCEPTO_FORMAT)
    for idx, banco in banco_row_idxs:
        row = mov_start + idx
        ws.merge_cells(f"A{row}:F{row}")
        format_cell_range(ws, f"A{row}:F{row}", banco_format(banco))

    # Bloque Egresos: título fusionado + header + subtotales + total
    egresos_header_row = resumen_start + 1
    ws.merge_cells(f"A{resumen_start}:C{resumen_start}")
    format_cell_range(ws, f"A{resumen_start}:C{resumen_start}", EGRESOS_TITLE_FORMAT)
    format_cell_range(ws, f"A{egresos_header_row}:C{egresos_header_row}", HEADER_FORMAT)
    for idx in subtotal_row_idxs:
        row = resumen_start + idx
        format_cell_range(ws, f"A{row}:C{row}", SUBTOTAL_FORMAT)
    total_row = resumen_start + total_row_idx
    format_cell_range(ws, f"A{total_row}:C{total_row}", TOTAL_FORMAT)
    if total_sin_propias_row_idx is not None:
        total_sin_propias_row = resumen_start + total_sin_propias_row_idx
        format_cell_range(ws, f"A{total_sin_propias_row}:C{total_sin_propias_row}", TOTAL_AJUSTADO_FORMAT)

    # Bloque Ingresos: título fusionado + header + total
    ingresos_header_row = ingresos_start + 1
    ws.merge_cells(f"A{ingresos_start}:C{ingresos_start}")
    format_cell_range(ws, f"A{ingresos_start}:C{ingresos_start}", INGRESOS_TITLE_FORMAT)
    format_cell_range(ws, f"A{ingresos_header_row}:C{ingresos_header_row}", HEADER_FORMAT)
    ingresos_total_row = ingresos_start + ingresos_total_row_idx
    format_cell_range(ws, f"A{ingresos_total_row}:C{ingresos_total_row}", TOTAL_FORMAT)
    if ingresos_total_sin_propias_row_idx is not None:
        ingresos_total_sin_propias_row = ingresos_start + ingresos_total_sin_propias_row_idx
        format_cell_range(ws, f"A{ingresos_total_sin_propias_row}:C{ingresos_total_sin_propias_row}", TOTAL_AJUSTADO_FORMAT)

    # Columna Categoría (A) de ambos bloques de resumen: mismo wrap que Concepto
    format_cell_range(ws, f"A{resumen_start}:A{ingresos_end}", CATEGORIA_WRAP_FORMAT)

    # Bordes negros en todas las celdas con contenido (solo eso, no en filas/columnas vacías)
    format_cell_range(ws, f"A{mov_start}:F{mov_end}", BORDER_FORMAT)
    format_cell_range(ws, f"A{resumen_start}:C{resumen_end}", BORDER_FORMAT)
    format_cell_range(ws, f"A{ingresos_start}:C{ingresos_end}", BORDER_FORMAT)

    print(f"Listo: {len(movimientos)} movimientos + resumen -> pestaña '{ws_name}'")
    print(f"https://docs.google.com/spreadsheets/d/{args.sheet_id}")


if __name__ == "__main__":
    main()
