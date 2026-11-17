from flask import Flask, request, jsonify
import pyodbc
import base64
import socket
from flask_cors import CORS

app = Flask(__name__)
CORS(app, expose_headers=["X-Servidor", "X-Puerto"])

HOSTNAME = socket.gethostname()


def instancia():
    return {"servidor": HOSTNAME, "puerto": request.environ.get("SERVER_PORT")}


@app.after_request
def marcar_instancia(response):
    info = instancia()
    response.headers["X-Servidor"] = info["servidor"]
    response.headers["X-Puerto"] = str(info["puerto"])
    if response.is_json:
        body = response.get_json(silent=True)
        if isinstance(body, dict) and "atendido_por" not in body and "servidor" not in body:
            body["atendido_por"] = info
            response.set_data(jsonify(body).get_data())
    return response


@app.route('/', methods=['GET'])
def raiz():
    return jsonify({"mensaje": "API Farmaceutica activa"}), 200


@app.route('/instancia', methods=['GET'])
def ver_instancia():
    return jsonify(instancia()), 200


# ==========================================
# CONEXION SQL SERVER
# ==========================================

def conectar():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=10.79.7.185,1433;"
        "DATABASE=FARMACEUTICA;"
        "UID=sa;"
        "PWD=sa;"
        "TrustServerCertificate=yes;"
    )


# ==========================================
# CONTROL DE VERSIONES
# ==========================================

def codificar_version(version):
    return base64.b64encode(version).decode("utf-8")


def decodificar_version(version):
    try:
        return base64.b64decode(version, validate=True)
    except Exception:
        return None


def empleado_json(row):
    return {
        "id_empleado": row[0],
        "cedula": row[1],
        "nombres": row[2],
        "apellidos": row[3],
        "telefono": row[4],
        "direccion": row[5],
        "correo": row[6],
        "cargo": row[7],
        "fecha_contratacion": str(row[8]),
        "salario": float(row[9]),
        "estado": bool(row[10]),
        "version": codificar_version(row[11])
    }


# ==========================================
# CREATE - REGISTRAR EMPLEADO
# ==========================================

@app.route('/empleados', methods=['POST'])
def crear():
    data = request.get_json()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Empleado
            (cedula, nombres, apellidos, telefono, direccion,
             correo, cargo, fecha_contratacion, salario, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['cedula'],
            data['nombres'],
            data['apellidos'],
            data.get('telefono'),
            data.get('direccion'),
            data.get('correo'),
            data['cargo'],
            data['fecha_contratacion'],
            data['salario'],
            data.get('estado', True)
        ))

        conn.commit()

        return jsonify({
            "mensaje": "Empleado registrado correctamente"
        }), 201

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ==========================================
# READ - LISTAR EMPLEADOS
# ==========================================

@app.route('/empleados', methods=['GET'])
def listar():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id_empleado, cedula, nombres, apellidos,
                   telefono, direccion, correo, cargo,
                   fecha_contratacion, salario, estado, row_version
            FROM Empleado
        """)

        empleados = [
            empleado_json(row)
            for row in cursor.fetchall()
        ]

        return jsonify(empleados)

    finally:
        conn.close()


# ==========================================
# READ - BUSCAR EMPLEADO POR ID
# ==========================================

@app.route('/empleados/<int:id>', methods=['GET'])
def buscar(id):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id_empleado, cedula, nombres, apellidos,
                   telefono, direccion, correo, cargo,
                   fecha_contratacion, salario, estado, row_version
            FROM Empleado
            WHERE id_empleado = ?
        """, (id,))

        row = cursor.fetchone()

        if row is None:
            return jsonify({
                "mensaje": "Empleado no encontrado"
            }), 404

        return jsonify(empleado_json(row))

    finally:
        conn.close()


# ==========================================
# UPDATE - ACTUALIZAR CON CONCURRENCIA
# ==========================================

@app.route('/empleados/<int:id>', methods=['PUT'])
def actualizar(id):
    data = request.get_json()

    if not data or not data.get('version'):
        return jsonify({
            "mensaje": "Debe enviar la version del empleado"
        }), 400

    version = decodificar_version(data['version'])

    if version is None or len(version) != 8:
        return jsonify({
            "mensaje": "Version invalida"
        }), 400

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE Empleado SET
                cedula = ?,
                nombres = ?,
                apellidos = ?,
                telefono = ?,
                direccion = ?,
                correo = ?,
                cargo = ?,
                fecha_contratacion = ?,
                salario = ?,
                estado = ?
            WHERE id_empleado = ?
            AND row_version = ?
        """, (
            data['cedula'],
            data['nombres'],
            data['apellidos'],
            data.get('telefono'),
            data.get('direccion'),
            data.get('correo'),
            data['cargo'],
            data['fecha_contratacion'],
            data['salario'],
            data.get('estado', True),
            id,
            version
        ))

        actualizado = cursor.rowcount

        if actualizado == 0:
            conn.rollback()

            cursor.execute("""
                SELECT 1 FROM Empleado
                WHERE id_empleado = ?
            """, (id,))

            existe = cursor.fetchone()

            if existe is None:
                return jsonify({
                    "mensaje": "Empleado no encontrado"
                }), 404

            return jsonify({
                "mensaje": "Conflicto de concurrencia",
                "detalle": "Otro usuario modifico este empleado. Consulte nuevamente los datos antes de actualizar."
            }), 409

        conn.commit()

        # Recuperar la nueva version
        cursor.execute("""
            SELECT row_version FROM Empleado
            WHERE id_empleado = ?
        """, (id,))

        nueva_version = cursor.fetchone()[0]

        return jsonify({
            "mensaje": "Empleado actualizado correctamente",
            "version": codificar_version(nueva_version)
        }), 200

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ==========================================
# DELETE - ELIMINAR CON CONCURRENCIA
# ==========================================

@app.route('/empleados/<int:id>', methods=['DELETE'])
def eliminar(id):
    data = request.get_json(silent=True) or {}

    if not data.get('version'):
        return jsonify({
            "mensaje": "Debe enviar la version del empleado"
        }), 400

    version = decodificar_version(data['version'])

    if version is None or len(version) != 8:
        return jsonify({
            "mensaje": "Version invalida"
        }), 400

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM Empleado
            WHERE id_empleado = ?
            AND row_version = ?
        """, (id, version))

        eliminado = cursor.rowcount

        if eliminado == 0:
            conn.rollback()

            cursor.execute("""
                SELECT 1 FROM Empleado
                WHERE id_empleado = ?
            """, (id,))

            existe = cursor.fetchone()

            if existe is None:
                return jsonify({
                    "mensaje": "Empleado no encontrado"
                }), 404

            return jsonify({
                "mensaje": "Conflicto de concurrencia",
                "detalle": "El empleado fue modificado por otro usuario. No se puede eliminar con una version antigua."
            }), 409

        conn.commit()

        return jsonify({
            "mensaje": "Empleado eliminado correctamente"
        }), 200

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ==========================================
# INICIAR SERVIDOR
# ==========================================

if __name__ == '__main__':
    app.run(
        debug=False,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
