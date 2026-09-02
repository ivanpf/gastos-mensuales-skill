#!/usr/bin/env python3
"""
Parsea un CSV de movimientos de Santander (export "Movimientos" de banca
digital) a un CSV normalizado, con las mismas columnas que usan todos los
parsers de este proyecto (ver scripts/movs_csv.py).

El formato de estos exports NO es un CSV plano: tiene ~6 líneas de metadata
de cuenta al principio, líneas en blanco, y recién después el header real
de la tabla (columna "Fecha"). Además vienen en encoding ISO-8859-1
(latin-1), no UTF-8.

Uso:
    python scripts/parsers/santander.py <archivo.csv> --out movimientos.csv
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from movs_csv import FIELDS, write_movs

ENCODING = "latin-1"
HEADER_MARKER = "Fecha"  # primera columna de la fila de header real
BANCO = "Santander"


def find_header_row(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        first_field = line.split(",", 1)[0].strip()
        if first_field == HEADER_MARKER:
            return i
    raise ValueError(
        f"No encontré la fila de header (columna '{HEADER_MARKER}'). "
        "El formato del export puede haber cambiado."
    )


def parse_amount(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    # Los montos vienen como "-147.54" / "157.50" (punto decimal, sin miles)
    return abs(float(raw))


def parse_santander_csv(path: str) -> list[dict]:
    with open(path, "r", encoding=ENCODING, newline="") as f:
        raw_lines = f.readlines()

    header_idx = find_header_row(raw_lines)
    reader = csv.DictReader(raw_lines[header_idx:])

    # Normalizamos nombres de columna (algunos vienen con acentos rotos
    # por el encoding, ej. "Descripci�n" en vez de "Descripción")
    fieldmap = {}
    for f in reader.fieldnames or []:
        key = f.strip().lower()
        if key.startswith("fecha"):
            fieldmap[f] = "fecha"
        elif key.startswith("referencia"):
            fieldmap[f] = "referencia"
        elif key.startswith("concepto"):
            fieldmap[f] = "concepto"
        elif key.startswith("descripci"):
            fieldmap[f] = "descripcion"
        elif key.startswith("débito") or key.startswith("d�bito") or key.startswith("debito"):
            fieldmap[f] = "debito"
        elif key.startswith("crédito") or key.startswith("cr�dito") or key.startswith("credito"):
            fieldmap[f] = "credito"
        elif key.startswith("saldo"):
            fieldmap[f] = "saldo"

    records = []
    for row in reader:
        fecha_raw = (row.get(next((k for k, v in fieldmap.items() if v == "fecha"), ""), "") or "").strip()
        if not fecha_raw:
            continue  # fila vacía / de cierre

        def get(field):
            col = next((k for k, v in fieldmap.items() if v == field), None)
            return (row.get(col, "") or "").strip() if col else ""

        try:
            d, m, y = fecha_raw.split("/")
            fecha_iso = f"{y}-{m}-{d}"
        except ValueError:
            continue  # fecha con formato inesperado, la salteamos

        debito = parse_amount(get("debito"))
        credito = parse_amount(get("credito"))

        if debito is not None:
            tipo, monto = "debito", debito
        elif credito is not None:
            tipo, monto = "credito", credito
        else:
            continue  # fila sin movimiento real

        concepto = get("concepto")
        saldo_raw = get("saldo")
        try:
            saldo = float(saldo_raw) if saldo_raw else ""
        except ValueError:
            saldo = ""

        records.append({
            "banco": BANCO,
            "fecha": fecha_iso,
            "referencia": get("referencia"),
            "concepto": concepto,
            "tipo": tipo,
            "monto": monto,
            "saldo": saldo,
            "categoria": "",
            "subcategoria": "",
        })

    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--out", default=None, help="Archivo de salida CSV (default: stdout)")
    args = ap.parse_args()

    records = parse_santander_csv(args.csv_path)

    if args.out:
        write_movs(records, args.out)
        print(f"{len(records)} movimientos -> {args.out}", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(records)


if __name__ == "__main__":
    main()
