"""
Formato CSV común para movimientos, usado por todos los parsers y por
write_to_sheets.py. Un CSV en vez de JSON: mismo dato, sin repetir el
nombre de cada campo en cada fila (más compacto para leer/inspeccionar).

Columnas:
    banco, fecha (ISO yyyy-mm-dd), referencia, concepto,
    tipo (debito|credito), monto (siempre positivo), saldo (opcional),
    categoria, subcategoria (vacías hasta el paso de categorización)
"""
import csv

FIELDS = [
    "banco", "fecha", "referencia", "concepto",
    "tipo", "monto", "saldo", "categoria", "subcategoria",
]


def write_movs(records, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def read_movs(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            row["monto"] = float(row["monto"])
            row["saldo"] = float(row["saldo"]) if row.get("saldo") else None
            records.append(row)
        return records
