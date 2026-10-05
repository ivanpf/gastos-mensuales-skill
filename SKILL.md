---
name: gastos-mensuales
description: Procesa movimientos de distintos bancos/billeteras (CSV, PDF, Excel, capturas de pantalla) y sube los gastos categorizados a un Google Sheets, todo en una pestaña por mes con resumen de egresos/ingresos. Usar esta skill cuando el usuario pida cargar/analizar/categorizar gastos, movimientos o resumen de cuenta de cualquier banco o billetera, o pase un archivo/captura de un extracto.
---

# Gastos mensuales -> Google Sheets

## Cuándo se usa
El usuario pasa uno o más archivos (CSV, PDF, Excel) o capturas de pantalla
con movimientos de un banco/billetera de un mes dado, y quiere que se
carguen categorizados a un Google Sheets, en la pestaña de ese mes.

## Setup (una sola vez por computadora)
Ver [SETUP.md](SETUP.md) para la guía completa paso a paso (Python, Google
Cloud Console, service account, etc.). Antes de procesar el primer mes en
una computadora nueva, confirmar que ese setup ya se hizo:
1. Existe `scripts/service_account.json` (credenciales del service account
   de Google Cloud). Si no existe, remitir al usuario a `SETUP.md` y
   detenerse hasta que lo tenga.
2. Existe `scripts/.sheet_id` con el ID del Google Sheet, y ese Sheet ya
   está compartido (permiso Editor) con el email del service account.
3. Dependencias instaladas: `pip install -r scripts/requirements.txt`
   (incluye `gspread`, `google-auth`, `gspread-formatting`, `openpyxl`).

## Flujo mensual: el usuario pasa varios archivos de distintos orígenes

El usuario junta en un mismo mensaje/conversación los extractos del mes de
cada banco/billeteta que use (ej. CSV de Santander + PDF de OCA + Excel de
Prex + captura de Mercado Pago) y los pega directo en el chat — **no hace
falta que los guarde en ninguna carpeta del proyecto**, alcanza con pasarlos
como adjuntos cada vez que corresponda cargar un mes nuevo.

Por cada archivo/captura:

1. **Extraer los movimientos**, uno por banco/origen, a un CSV con el
   formato de `scripts/movs_csv.py` (columnas: `banco, fecha, referencia,
   concepto, tipo, monto, saldo, categoria, subcategoria` — las dos
   últimas se completan en el paso de categorización).
   - Si existe un parser dedicado para ese banco en `scripts/parsers/`
     (por ahora solo `santander.py`), usarlo:
     `python scripts/parsers/santander.py <archivo.csv> --out <tmp>/movs_santander.csv`.
   - Si no hay parser dedicado para ese banco (PDF, Excel, captura de
     pantalla, o cualquier banco nuevo): no hace falta escribir uno — leer
     el archivo/imagen directamente (Read para PDF/captura, un script
     rápido con `openpyxl` para Excel) y armar a mano un CSV con las mismas
     columnas, agregando siempre el nombre del banco en la columna
     `banco`. Si en algún momento un origen empieza a repetirse seguido y
     vale la pena automatizarlo, se puede sumar un parser nuevo en
     `scripts/parsers/` siguiendo el mismo patrón que `santander.py`.
   - Si el archivo trae muchos movimientos repetidos del mismo tipo (ej.
     "Rendimiento" diario de una cuenta remunerada como Prex), preguntarle
     al usuario si los quiere **unificados en una sola fila** (suma total,
     un solo movimiento) antes de categorizar — no asumirlo.

2. **Categorizar.** Leer `categories.json` (objeto `{categoria:
   [subcategorias]}`) y completar las columnas `categoria`/`subcategoria`
   de cada fila del CSV con un valor de esa lista, con criterio, basándose
   en el `concepto`:
   - Cada banco tiene sus propios patrones de texto en el concepto — si
     existe una nota en `references/` para ese banco (ej.
     `references/patrones_santander.md`), usarla como ayuda. Si no existe,
     inferir del texto del concepto y, si hace falta, preguntarle al
     usuario.
   - **Transferencias**: distinguir "Propias" (a una cuenta del mismo
     usuario, mismo nombre en el concepto) de "A otros" (a otra persona).
     No asumir — si no es obvio de quién es la cuenta destino, preguntar.
   - **Créditos que no son ingresos reales** (reintegros, descuentos de una
     compra, ej. "PROMOCIONES TARJETAS...DESC <comercio>"): categorizarlos
     **igual que la compra que descuentan** (misma categoría/subcategoría),
     no como "Ingresos". El script neteará automáticamente ese crédito
     contra los débitos de la misma categoría en la tabla de Egresos, y lo
     va a mostrar como una línea negativa aparte (no oculto en un solo
     número) para que se vea el ajuste.
   - **Ingresos reales** (sueldo, transferencias recibidas de otra persona,
     rendimientos de cuentas remuneradas): sí van en categoría "Ingresos",
     con la subcategoría que corresponda.
   - Si un concepto o nombre de persona es ambiguo (¿a qué categoría
     corresponde una transferencia a "Fulano"? ¿es un reintegro o un
     ingreso real?), **preguntarle al usuario** en vez de asumir — estos
     casos se repiten mes a mes así que vale la pena confirmarlos.
   - Si hace falta una categoría o subcategoría que no existe todavía en
     `categories.json`, se puede agregar (ver más abajo), pero no inventar
     un valor que no esté en la lista al momento de escribir el CSV — la
     columna es un dropdown fijo en el Sheet.
   - Guardar cada banco en su propio archivo CSV categorizado (ej.
     `<tmp>/movs_santander.csv`, `<tmp>/movs_oca.csv`, etc.) — el script
     de subida acepta varios a la vez.
   - Antes de subir, mostrarle al usuario un resumen rápido (movimientos
     por categoría/subcategoría) para que pueda corregir algo si quedó mal
     categorizado.

3. **Subir a Sheets**, pasando **todos los CSV del mes en un solo comando**:
   ```
   python scripts/write_to_sheets.py \
       <tmp>/movs_santander.csv <tmp>/movs_oca.csv <tmp>/movs_prex.csv <tmp>/movs_mercadopago.csv \
       --categories categories.json \
       --sheet-id <ID> \
       --credentials scripts/service_account.json
   ```
   - El script escribe todo (movimientos agrupados por banco + resumen de
     Egresos + resumen de Ingresos + tabla "Saldo del mes" con Ingresos −
     Egresos, en verde si queda a favor y en rojo si da negativo) en **una
     sola pestaña por mes**, nombrada solo con el mes del primer movimiento
     (ej. "Agosto", sin año). La crea si no existe, o la **recrea de cero**
     en el mismo lugar si ya existe (útil para volver a subir el mismo mes
     corregido) — esto **no toca ninguna otra pestaña**, así que el
     histórico de meses anteriores queda intacto.
   - Si Google responde `429 Quota exceeded ... Write requests per
     minute`, es el límite de escrituras por minuto: esperar ~1 minuto y
     volver a correr el mismo comando (el script recrea la pestaña entera,
     así que no queda nada a medias). Conviene no subir el mismo mes varias
     veces seguidas.
   - Cada banco aparece agrupado con una fila separadora fusionada y de
     color propio (Santander=rojo, OCA=azul, Prex=violeta, Mercado
     Pago=amarillo; cualquier banco nuevo sin color asignado usa celeste
     por default — los colores están en `BANCO_COLORES` dentro de
     `write_to_sheets.py`, se le puede agregar uno nuevo ahí si el usuario
     lo pide).
   - El script valida que todas las categorías/subcategorías estén en la
     lista antes de escribir nada — si falla, corregir el CSV y
     reintentar, no editar el Sheet a mano para parchear.
   - Usar `--worksheet-name` solo si hay que forzar un nombre de pestaña
     distinto al mes detectado automáticamente.

4. Devolver el link del Sheet que imprime el script al final.

## Forma del CSV de movimientos (para orígenes sin parser dedicado)

Columnas (ver `scripts/movs_csv.py`, es la misma para todos los orígenes):

```
banco,fecha,referencia,concepto,tipo,monto,saldo,categoria,subcategoria
MiBanco,2026-01-31,123456789012,"COMPRA COMERCIO EJEMPLO",debito,1500.00,25000.00,Compras online,-
```

- `fecha`: ISO `yyyy-mm-dd`.
- `referencia`: número de operación si lo hay, si no vacío.
- `tipo`: `debito` o `credito`.
- `monto`: siempre positivo, el signo lo da `tipo`.
- `saldo`: opcional, vacío si no está disponible.
- `banco`: nombre del banco/billetera, se muestra en el Sheet.
- `categoria`/`subcategoria`: se completan en el paso de categorización,
  vacías está bien en el CSV "crudo" recién extraído.

Se puede armar con `scripts/movs_csv.py::write_movs(records, path)` desde
un script rápido, o escribiendo el CSV directamente si son pocas filas.

## Notas importantes
- El CSV de Santander viene en **encoding ISO-8859-1 (latin-1)**, no UTF-8,
  y con metadata antes del header real de la tabla. `scripts/parsers/santander.py`
  ya maneja esto — no reimplementar el parseo a mano. Ver también
  `references/patrones_santander.md` para los patrones de concepto típicos
  de ese banco.
- Los movimientos de tipo `credito` no son necesariamente "ingresos" en
  sentido estricto (pueden ser reintegros/descuentos). No asumir
  automáticamente — ver criterio de categorización arriba.
- Las transferencias a cuentas propias inflan el gasto total sin ser un
  gasto real — por eso el resumen de Egresos separa "Propias" de "A otros"
  y agrega una fila "Total sin transferencias propias".
- No modificar `categories.json` sin que el usuario lo pida explícitamente
  — es la fuente de verdad del dropdown del Sheet. Sí se puede (y conviene)
  agregar categorías/subcategorías nuevas cuando aparece un tipo de gasto
  que no encaja en las existentes, si el usuario lo confirma.
