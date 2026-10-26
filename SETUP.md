# Setup inicial (una sola vez por computadora)

Esta guía es para vos, humano. Si estás usando un agente de IA (Claude Code, Codex, Gemini CLI, etc.), también podés
simplemente decirle "hacé el setup de esta skill" y que te vaya guiando —
puede hacer casi todos los pasos por vos, salvo los que requieren que hagas
click en la web de Google (por seguridad, eso lo tenés que hacer vos a mano).

## 1. Instalar un agente de IA (si no tenés ninguno en esta computadora)

Necesitás un agente de IA con acceso a archivos y terminal, por ejemplo
Claude Code, Codex o Gemini CLI. Seguí las instrucciones de instalación de la
herramienta que elijas (y su cuenta correspondiente).

## 2. Conseguir esta carpeta en la computadora nueva

Si este proyecto está en un repositorio de Git (recomendado), simplemente:

```bash
git clone <URL-del-repo>
cd <carpeta-del-repo>
```

Si no tenés un repo todavía y solo lo estás copiando manualmente (pendrive,
otra nube, etc.), copiá toda la carpeta del proyecto tal cual, **salvo**
`scripts/service_account.json` si por algún motivo quedó ahí — ese archivo
es una credencial y no debería viajar suelto ni subirse a ningún repo
público (ver paso 5).

## 3. Instalar Python

Si `python --version` en una terminal no devuelve una versión (Windows a
veces solo tiene un acceso directo falso a la Microsoft Store), instalá
Python 3.11+ desde:
- Windows: Microsoft Store (buscar "Python") o https://python.org/downloads
- Mac: `brew install python3` o https://python.org/downloads
- Linux: normalmente ya viene instalado (`python3 --version`)

## 4. Instalar las dependencias del proyecto

Desde la carpeta del proyecto:

```bash
python -m pip install -r scripts/requirements.txt
```

## 5. Crear el service account de Google Cloud (una sola vez, se puede reusar en todas tus computadoras)

Esto le da al agente permiso para escribir en tu Google Sheet sin necesitar
tu contraseña de Google ni hacer login interactivo cada vez.

1. Andá a https://console.cloud.google.com/ y creá un proyecto nuevo (o
   usá uno existente) — arriba a la izquierda, "Seleccionar proyecto" ->
   "Proyecto nuevo".
2. Con el proyecto seleccionado, andá a **"APIs y servicios" -> "Biblioteca"**
   y habilitá estas dos APIs (buscalas por nombre y click en "Habilitar"):
   - **Google Sheets API**
   - **Google Drive API**
3. Andá a **"IAM y administración" -> "Cuentas de servicio"** ->
   **"Crear cuenta de servicio"**. Ponele cualquier nombre (ej.
   "gastos-bot") y creála (no hace falta darle ningún rol de proyecto).
4. Entrá a la cuenta de servicio recién creada -> pestaña **"Claves"** ->
   **"Agregar clave" -> "Crear clave nueva" -> tipo JSON**. Se descarga un
   archivo `.json`.
5. Guardá ese archivo como `scripts/service_account.json` dentro de la
   carpeta de este proyecto (el nombre tiene que ser exactamente ese).
   **Importante**: este archivo es una credencial — no lo compartas ni lo
   subas a un repositorio público. Si este proyecto es un repo de Git,
   asegurate de que `.gitignore` lo excluya (ya debería estar configurado).
6. Copiá el email de la cuenta de servicio (algo como
   `nombre@proyecto.iam.gserviceaccount.com` — está visible en la lista de
   cuentas de servicio, o dentro del JSON descargado en el campo
   `client_email`). Lo vas a necesitar en el paso siguiente.

## 6. Crear o elegir el Google Sheet de destino

- Si ya tenés un Google Sheet para esto (por ejemplo porque ya lo usaste en
  otra computadora), simplemente compartilo (botón "Compartir") con el
  email de la cuenta de servicio del paso 5, dándole permiso de **Editor**.
- Si no tenés uno todavía, creá un Google Sheet nuevo vacío desde
  sheets.google.com, y compartilo igual con el email de la cuenta de
  servicio (permiso Editor).
- Copiá el **ID del Sheet**: es la parte de la URL entre `/d/` y `/edit`,
  ej. en `https://docs.google.com/spreadsheets/d/1AbCdEf.../edit` el ID es
  `1AbCdEf...`.
- Guardá ese ID en un archivo `scripts/.sheet_id` (solo el ID, sin
  comillas ni espacios).

## 7. Listo — probar

Con todo lo anterior hecho, ya podés pedirle al agente que procese el
CSV/PDF/Excel/captura de un mes (ver [SKILL.md](SKILL.md) para el flujo
normal). Como prueba rápida de que todo está bien conectado, le podés pedir
que liste las pestañas del Sheet o que suba un movimiento de prueba.

## Notas
- Los pasos 1 a 4 y 7 se repiten en cada computadora nueva donde uses esto.
- El paso 5 (service account) solo hace falta hacerlo **una vez en total**
  — después simplemente copiás el archivo `service_account.json` a la
  computadora nueva (por un medio seguro, no por email ni chat público) en
  vez de crear una cuenta de servicio nueva cada vez.
- El paso 6 también es único por Sheet — si usás el mismo Google Sheet
  desde varias computadoras, copiá el mismo archivo `scripts/.sheet_id` a
  cada una (igual que `service_account.json`, por un medio seguro — no es
  una contraseña, pero identifica tu planilla de gastos personales, así
  que tampoco conviene subirlo a un repo público; por eso está en
  `.gitignore`)
  (ese archivo sí se puede versionar en Git, no es secreto).
