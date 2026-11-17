# Variables de entorno

Copie estas variables en su entorno (o en un archivo que su herramienta cargue). No incluya secretos reales en el repositorio.

```
# Base de datos (SQL Server). Use DATABASE_URL para pruebas (p. ej. sqlite:///farmaceutica.db)
DB_ODBC_CONNECTION=DRIVER={ODBC Driver 18 for SQL Server};SERVER=HOST,1433;DATABASE=FARMACEUTICA;UID=usuario;PWD=secreto;TrustServerCertificate=yes;

# Tokens JWT
JWT_SECRET=un-secreto-largo-y-aleatorio
JWT_EXPIRA_HORAS=8

# Base pública de la API: los redirect_uri de OAuth son {OAUTH_REDIRECT_BASE}/auth/<proveedor>/callback
OAUTH_REDIRECT_BASE=http://localhost:5000

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_GRAPH_VERSION=v21.0

INSTAGRAM_APP_ID=
INSTAGRAM_APP_SECRET=

# Puertos donde se levanta la API (una instancia por puerto). Ej.: 5000,5001
PORTS=5000,5001
```

`PORT` (singular) sigue funcionando si `PORTS` no está definida.

Los redirect URI registrados en cada proveedor deben coincidir exactamente:

- Google: `{OAUTH_REDIRECT_BASE}/auth/google/callback`
- Facebook: `{OAUTH_REDIRECT_BASE}/auth/facebook/callback`
- Instagram: `{OAUTH_REDIRECT_BASE}/auth/instagram/callback`
