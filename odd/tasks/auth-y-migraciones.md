Objetivo: reorganizar api-farmaceutica.py en paquetes iniciados desde main.py, agregar login (email/contraseña, Google, Facebook, Instagram), roles admin/empleado y migraciones Alembic sobre SQL Server.
Rama: main (repositorio sin commits; no se hacen commits automáticos). Estrategia de entrega: ask-on-risk. Runner: pytest.

## Specs
S1. "reorganizar lo que ya esta en api-farmaceutica.py y tener una mejor distribucion y organizacion para que se inicie desde main"
S2. "usar alembic para las migraciones, (la base de datos es sql server)"
S3. "login con email y contraseña"
S4. "implementes un login por medio de google, fb e instagram"
S5. "la parte de roles rol admin y rol empleado"
S6. "manten la misma estructura que se optimene de empleado para no cambiar los endpoints"
S6a. Supuesto: solo GET de empleados exige sesión (admin o empleado); POST/PUT/DELETE exigen rol admin.
S6b. Supuesto: Instagram Business Login no entrega email; sus cuentas se identifican por user_id.

## Tasks
T1 | S1, S6 | inline | reorganizar en paquetes, misma respuesta de Empleado
T2 | S2 | inline | Alembic + migraciones 0001 (Empleado, guarded) y 0002 (roles/usuarios)
T3 | S3, S5 | inline | usuarios, roles, contraseñas hash, JWT, decoradores
T4 | S4 | inline | OAuth Google/Facebook/Instagram
T5 | S1-S6 | inline | pruebas pytest y verificación

## Log
L1 (original, verbatim): "necesito que implementes un login por medio de google, fb e instagram , ademas de ello login con email y contraseña y la parte de roles rol admin y rol empleado, puedes reorganizar lo que ya esta en api-farmaceutica.py y tener una mejor distribucion y organizacion para que se inicie desde main,a demas de usar alembic para las migraciones, (la base de datos es sql server)  y ademas de ello manten la misma estructura que se optimene de empleado para no cambiar los endpoints"
L2 Evidencia: pytest 21/21 OK (SQLite para la lógica; ROWVERSION de SQL Server no probado en vivo). `alembic upgrade head --sql` con dialecto mssql genera DDL válido. `python main.py --help` OK. pyflakes sin errores (salvo import intencional en migrations/env.py).
L3 Pendiente: validar 0001/0002 contra la base real de SQL Server (la tabla Empleado ya existe: usar `alembic stamp 0001` antes de `upgrade head`); credenciales OAuth reales; api-farmaceutica.py conservado sin cambios (no se eliminó).
