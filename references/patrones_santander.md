# Patrones de concepto típicos de Santander Uruguay

Notas específicas para categorizar movimientos que vienen de
`scripts/parsers/santander.py` (CSV de banca digital, sección
"Movimientos"). Esto es una ayuda para ese banco en particular — no aplica
a otros orígenes, cada uno tiene sus propios patrones de texto.

- `"COMPRA CON TARJETA DEBITO <comercio>"` -> categorizar por el comercio.
- `"PAGO DE SERVICIO POR BANRED ... <servicio>"` -> "Servicios" (UTE, OSE,
  Antel, Gas según el `<servicio>`).
- `"SERVICIO PAC DEBITO ...ZURICH SANTANDER"` u otro pago de tarjeta de
  crédito -> "Tarjeta de crédito".
- `"COMISION COMPRA INTERNACIONAL"` -> "Comisiones bancarias".
- `"TRANSFERENCIA ENVIADA"` / `"DEBITO OPERACION EN BANCA DIGITAL ... TRF"`
  -> "Transferencias enviadas" (revisar el nombre del destinatario para
  distinguir "Propias" de "A otros").
- `"PROMOCIONES TARJETAS DE DEBITO DESC <comercio>"` (crédito) -> es un
  reintegro/descuento de una compra, no un ingreso real — categorizar
  igual que la compra que descuenta (ver criterio general en SKILL.md).
- `"COMPRA CON TARJETA DEBITO DLO.PEDIDOSYA ..."` (incluye las líneas
  "ENVIO") -> "Comida / Delivery".
- `"COMPRA CON TARJETA DEBITO CORPORACION VIAL"` -> "Auto / Telepeaje".
- `"CREDITO OPERACION EN BANCA DIGITAL P--/<nombre>"` (crédito) -> si el
  nombre es el del propio titular, preguntar si es una transferencia propia
  o un ingreso real; no asumir.
- `"CR. PAGO SUELDOS ..."` -> "Ingresos / Sueldo".
- Una transferencia enviada genera **dos** líneas (`"TRANSFERENCIA ENVIADA"`
  con la comisión y `"DEBITO OPERACION EN BANCA DIGITAL ... TRF"` con el
  monto): ambas van en la misma categoría/subcategoría.
