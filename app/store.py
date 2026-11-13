"""Generación en memoria de los identificadores de respuesta."""


class MatchStore:
    def __init__(self) -> None:
        self._por_clave: dict[tuple[int, int, int], int] = {}
        self._ultimo_id = 100

    def obtener_o_crear(self, usuario_id: int, usuario_match_id: int,
                        habilidad_id: int) -> int:
        """Reutiliza el identificador de una misma pareja y habilidad durante el proceso."""
        clave = (usuario_id, usuario_match_id, habilidad_id)
        if clave not in self._por_clave:
            self._ultimo_id += 1
            self._por_clave[clave] = self._ultimo_id
        return self._por_clave[clave]
