# Patrones de texto de otros orígenes (sin parser dedicado)

Estos orígenes no tienen parser en `scripts/parsers/`: se leen directo del
PDF / Excel / captura y se arma el CSV a mano (ver SKILL.md). Notas para
categorizar sus conceptos.

## OCA (PDF "Mi Cuenta")
- `TRANSF.TOLD <n>` -> transferencia **enviada** (débito).
- `TRANSF.TOLC <n>` -> transferencia **recibida** (crédito).
- El concepto no dice a quién ni para qué: **preguntar** al usuario qué
  categoría corresponde a cada monto (los pagos recurrentes suelen repetir
  el mismo importe).
- `COMPRA <plataforma de inversión>` -> "Inversiones".

## Prex (Excel "estado de cuenta")
- `Rendimiento` (uno por día) -> "Ingresos / Rendimientos"; **unificar todos
  en una sola fila** (suma del mes) previa confirmación del usuario.
- `Prex a Prex a Cuenta <n>` -> transferencia enviada: "A otros" si la
  cuenta es de otra persona, "Propias" si es del titular (preguntar la
  primera vez que aparece cada número de cuenta).
- `CARGA TRANSFERENCIA BANCARIA <n>` -> plata que entra desde un banco:
  normalmente es la contrapartida de una transferencia propia enviada
  desde otro banco ("Ingresos / Transferencia recibida propia").
- Revisar que las fechas cubran todo el mes: el export puede venir parcial.

## Mercado Pago (capturas de "Actividad")
- `Rendimientos` (uno por día) -> igual que Prex: "Ingresos / Rendimientos"
  unificados en una fila.
- `Transferencia enviada` / `Transferencia recibida` + nombre -> preguntar
  la categoría si el destinatario no es conocido; si el nombre es el del
  propio titular, es una transferencia propia.
- Compras "con tarjeta de crédito" (ej. Mercado Libre) -> **no cargar** si
  esa tarjeta ya se paga y carga como "Tarjeta de crédito" en otro banco
  (se contaría doble).
