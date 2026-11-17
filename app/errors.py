class ErrorAplicacion(Exception):
    """Error de negocio con código HTTP y mensaje para el cliente."""

    def __init__(self, mensaje, status=400, detalle=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status = status
        self.detalle = detalle
