# API Farmacéutica (Backend)

API REST en Flask para la gestión de empleados de la farmacia, con autenticación por correo y contraseña, inicio de sesión con Google, Facebook e Instagram, roles (`admin` y `empleado`) y base de datos SQL Server con migraciones Alembic.

## Estructura

```
main.py                 Punto de entrada (servidor y creación de administradores)
app/
  __init__.py           Fábrica de la aplicación (create_app)
  config.py             Lectura de variables de entorno y .env
  database.py           Conexión y sesiones de base de datos
  api/                  Rutas: sistema, empleados, auth
  models/               Modelos: Empleado, Rol, Usuario, IdentidadProveedor
  services/             Lógica de negocio y acceso a datos
  security/             Tokens JWT y decoradores de rol
migrations/             Migraciones Alembic (0001 Empleado, 0002 usuarios y roles)
tests/                  Pruebas automáticas (pytest)
docs/variables_entorno.md   Lista completa de variables de entorno
odd/tasks/              Documento de seguimiento de la funcionalidad
api-farmaceutica.py     Versión anterior, conservada sin cambios
```

## Requisitos

- Python 3.10 o superior
- ODBC Driver 18 for SQL Server
- Acceso a la instancia de SQL Server

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
```

## Configuración

Cree un archivo `.env` en la raíz del proyecto (no se sube a git). Las variables están en [docs/variables_entorno.md](docs/variables_entorno.md). Como mínimo:

```
DB_ODBC_CONNECTION=DRIVER={ODBC Driver 18 for SQL Server};SERVER=HOST,1433;DATABASE=FARMACEUTICA;UID=usuario;PWD=clave;TrustServerCertificate=yes;
JWT_SECRET=un-secreto-largo
PORTS=5000,5001
OAUTH_REDIRECT_BASE=http://localhost:5000
```

Genere `JWT_SECRET` con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Base de datos (Alembic)

```bash
alembic upgrade head
```

- `0001`: crea la tabla `Empleado` solo si no existe.
- `0002`: crea `rol` (con `admin` y `empleado`), `usuario` e `identidad_proveedor`.

Si la tabla `Empleado` ya existe en su base, márquela como migrada antes de aplicar:

```bash
alembic stamp 0001
alembic upgrade head
```

Para ver el SQL sin ejecutarlo: `alembic upgrade head --sql`.

## Ejecución

```bash
python main.py
```

Con `PORTS=5000,5001` se levantan dos instancias, una por puerto. Cada respuesta incluye los encabezados `X-Servidor` y `X-Puerto`, y el campo `atendido_por`, para comprobar qué instancia respondió.

Crear el primer administrador:

```bash
python main.py crear-admin --nombre "Ana" --email ana@farmacia.com --password "clave-segura"
```

## Pruebas

```bash
pytest
```

Las pruebas usan SQLite temporal; no se conectan a SQL Server.

## Endpoints

### Sistema

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Estado de la API |
| GET | `/instancia` | Servidor y puerto que atendieron |

### Empleados

Requieren encabezado `Authorization: Bearer <token>`. `GET` lo pueden usar `admin` y `empleado`; las escrituras solo `admin`.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/empleados` | Lista empleados |
| GET | `/empleados/{id}` | Detalle de un empleado |
| POST | `/empleados` | Registra un empleado |
| PUT | `/empleados/{id}` | Actualiza (requiere `version`) |
| DELETE | `/empleados/{id}` | Elimina (requiere `version`) |

El campo `version` es el control de concurrencia de la tabla: envíe la versión que recibió al leer el empleado.

### Autenticación

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/registro` | Registro con correo y contraseña (rol `empleado`) |
| POST | `/auth/login` | Inicio de sesión con correo y contraseña; devuelve `access_token` |
| GET | `/auth/me` | Usuario de la sesión actual |
| GET | `/auth/google/login` | URL de autorización de Google |
| GET | `/auth/facebook/login` | URL de autorización de Facebook |
| GET | `/auth/instagram/login` | URL de autorización de Instagram |
| GET | `/auth/{proveedor}/callback` | Callback de OAuth; devuelve el token de la API |
| GET | `/auth/usuarios` | Lista usuarios (solo `admin`) |
| PUT | `/auth/usuarios/{id}/rol` | Cambia el rol (solo `admin`) |

Ejemplo de login:

```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@farmacia.com","password":"clave-segura"}'
```

Los redirect URI registrados en Google, Facebook e Instagram deben ser `{OAUTH_REDIRECT_BASE}/auth/{proveedor}/callback`.

### Retorno a Flutter Web

Aplica la migración `0003` con `alembic upgrade head` y configura `OAUTH_FRONTEND_RETURNS` en las instancias de Flask con URLs completas y separadas por comas. Para Flutter Web local usa `OAUTH_FRONTEND_RETURNS=http://localhost:58819/`. El callback registrado en el proveedor sigue apuntando al dominio de Flask. Mantén `OAUTH_REDIRECT_BASE` en ese dominio y reinicia las instancias después de configurarlas.

Flutter solicita la autorización con `retorno` y `desafio`, y Flask redirige al cliente con un código de un solo uso. `POST /auth/intercambiar` recibe `state`, `code` y `verifier` y devuelve el JWT. Las instancias deben compartir el primario SQL y el `JWT_SECRET`. La ruta de inicio sin `retorno` usa el flujo anterior.

## Balanceo de carga con Nginx

Con `PORTS=5000,5001` la API queda escuchando en ambos puertos. Ejemplo de configuración:

```nginx
upstream farmaceutica_api {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
}

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://farmaceutica_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Si usa Nginx, `OAUTH_REDIRECT_BASE` debe ser la URL pública que ve el navegador (por ejemplo `https://api.su-dominio.com`), no los puertos internos.

Como la autenticación es un JWT firmado (no guarda sesión en memoria), cualquiera de las dos instancias valida el mismo token: no hace falta sesión pegajosa.

## Seguridad

- No suba el archivo `.env` ni credenciales al repositorio; `.gitignore` ya lo excluye.
- Si alguna contraseña de base de datos estuvo escrita en código anterior, cámbiela.
