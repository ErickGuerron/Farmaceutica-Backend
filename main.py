"""Punto de entrada de la API Farmacéutica.

Uso:
    python main.py                 # inicia el servidor HTTP en los puertos de PORTS (ej. 5000,5001)
    python main.py servir          # igual que lo anterior
    python main.py crear-admin --nombre "Ana" --email ana@x.com --password "clave-segura"

Las migraciones de base de datos se ejecutan con Alembic: `alembic upgrade head`.
"""
import argparse
import getpass
import multiprocessing
import sys

from app import create_app
from app.config import Config
from app.errors import ErrorAplicacion
from app.services import usuario_service


def _correr_en_puerto(settings: Config, puerto: int):
    app = create_app(settings)
    app.run(debug=False, host="0.0.0.0", port=puerto, threaded=True)


def _servir(settings: Config):
    """Un proceso por puerto de PORTS. Con un solo puerto corre en el proceso actual."""
    if len(settings.ports) == 1:
        _correr_en_puerto(settings, settings.ports[0])
        return

    procesos = []
    for puerto in settings.ports:
        proceso = multiprocessing.Process(target=_correr_en_puerto, args=(settings, puerto), name=f"api-{puerto}")
        proceso.start()
        procesos.append(proceso)
        print(f"API escuchando en http://0.0.0.0:{puerto}")

    try:
        for proceso in procesos:
            proceso.join()
    except KeyboardInterrupt:
        for proceso in procesos:
            proceso.terminate()
        for proceso in procesos:
            proceso.join()


def _crear_admin(settings: Config, args):
    password = args.password or getpass.getpass("Contraseña del administrador: ")
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.", file=sys.stderr)
        return 1

    create_app(settings)  # inicializa la conexión a la base de datos
    try:
        admin = usuario_service.crear_admin(args.nombre, args.email, password)
    except ErrorAplicacion as error:
        print(error.mensaje, file=sys.stderr)
        return 1

    print(f"Administrador creado: {admin['email']} (id {admin['id_usuario']})")
    return 0


def construir_parser():
    parser = argparse.ArgumentParser(description="API Farmacéutica")
    subcomandos = parser.add_subparsers(dest="comando")

    subcomandos.add_parser("servir", help="Inicia el servidor HTTP (valor por defecto)")

    admin = subcomandos.add_parser("crear-admin", help="Crea un usuario con rol admin")
    admin.add_argument("--nombre", required=True)
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", help="Si se omite se pedirá de forma interactiva")

    seed = subcomandos.add_parser("seed", help="Crea admin, empleado y datos de ejemplo (desarrollo)")
    seed.add_argument("--admin-email", default="admin@farmacia.local")
    seed.add_argument("--admin-password", help="Si se omite se genera y se muestra una vez")
    seed.add_argument("--empleado-email", default="empleado@farmacia.local")
    seed.add_argument("--empleado-password", help="Si se omite se genera y se muestra una vez")
    seed.add_argument("--cantidad", type=int, default=20, help="Empleados de ejemplo a crear")
    seed.add_argument("--forzar-empleados", action="store_true",
                      help="Crea empleados aunque la tabla no esté vacía")

    return parser


def _seed(settings: Config, args):
    from app.services import seed_service

    create_app(settings)  # inicializa la conexión
    resumen = seed_service.sembrar(
        admin_email=args.admin_email,
        admin_password=args.admin_password,
        empleado_email=args.empleado_email,
        empleado_password=args.empleado_password,
        cantidad_empleados=args.cantidad,
        forzar_empleados=args.forzar_empleados,
    )
    for usuario in resumen["usuarios"]:
        print(f"Usuario {usuario['rol']}: {usuario['email']} ({usuario['estado']})")
    print(f"Empleados de ejemplo creados: {resumen['empleados_creados']}")
    for rol, clave in resumen["contrasenas_generadas"].items():
        print(f"Contraseña generada para {rol}: {clave}  (guárdela; no se volverá a mostrar)")
    return 0


def main(argv=None):
    args = construir_parser().parse_args(argv)
    settings = Config()

    if args.comando == "crear-admin":
        return _crear_admin(settings, args)

    if args.comando == "seed":
        return _seed(settings, args)

    _servir(settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
