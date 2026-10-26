# Gastos mensuales → Google Sheets

Skill de [Claude Code](https://claude.com/claude-code) + scripts en Python
para procesar extractos bancarios de distintos bancos/billeteras (CSV, PDF,
Excel, capturas de pantalla), categorizar los movimientos y subirlos
organizados a un Google Sheets, con una pestaña por mes y resumen de
egresos/ingresos.

## Qué hace

1. **Extrae** los movimientos de cada archivo/captura que pasás (uno por
   banco/billetera) a un CSV con columnas estandarizadas. Santander tiene un
   parser dedicado (`scripts/parsers/santander.py`); el resto se procesa al
   vuelo, sin necesidad de escribir un parser nuevo.
2. **Categoriza** cada movimiento contra una lista fija de categorías/
   subcategorías (`categories.json`), distinguiendo ingresos reales de
   reintegros/descuentos y transferencias propias de transferencias a
   terceros.
3. **Sube** todo a una pestaña de Google Sheets nombrada con el mes
   correspondiente, agrupado por banco (con color propio por banco) y con un
   resumen de egresos/ingresos y un saldo del mes (ingresos − egresos) — sin tocar el histórico de meses anteriores.

## Estructura del repo

```
SKILL.md                    # instrucciones que sigue Claude para el flujo mensual
SETUP.md                    # guía de instalación paso a paso (Python, Google Cloud, etc.)
categories.json             # fuente de verdad de categorías/subcategorías (dropdown del Sheet)
references/
  patrones_santander.md     # patrones de texto típicos de Santander para categorizar
  patrones_otros_origenes.md  # idem para OCA, Prex y Mercado Pago
scripts/
  movs_csv.py                # formato/escritura del CSV intermedio de movimientos
  write_to_sheets.py          # sube uno o varios CSV categorizados a Google Sheets
  parsers/
    santander.py               # parser dedicado del extracto CSV de Santander
  requirements.txt            # dependencias Python (gspread, google-auth, openpyxl, ...)
```

## Uso

Este proyecto está pensado para usarse con Claude Code: le pasás los
extractos del mes (CSV/PDF/Excel/captura) como adjuntos en el chat y la
skill se encarga del resto. El flujo completo está documentado en
[SKILL.md](SKILL.md).

## Setup

Antes de usarlo por primera vez en una computadora hace falta instalar
Python, las dependencias del proyecto, y crear un service account de Google
Cloud para que Claude pueda escribir en tu Sheet sin pedirte login cada vez.
Guía completa paso a paso en [SETUP.md](SETUP.md).

## Personalización

`categories.json` define las categorías y subcategorías (son también las
opciones del dropdown del Sheet): editalo con las tuyas. Los colores por
banco están en `BANCO_COLORES`, dentro de `scripts/write_to_sheets.py`.

## Privacidad

`scripts/service_account.json` (credenciales de Google Cloud) y
`scripts/.sheet_id` (ID de tu planilla personal) son específicos de cada
usuario y están excluidos del repo vía `.gitignore` — nunca se versionan.
