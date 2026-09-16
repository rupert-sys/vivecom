"""
Utilidad compartida para las secciones que dependen de with_for_update()
como candado entre procesos (Postgres). Ver la nota extensa en
reservation_service.py (F2-20) sobre la doble capa candado-en-memoria +
with_for_update(), y su limitación conocida: with_for_update() es un no-op
silencioso en SQLite. Extraída aquí (en vez de duplicarla en cada servicio
que la necesita) tras encontrarla repetida en reservation_service.py y
payment_reconciliation_service.py tras la revisión de F2-20/F3.
"""

import warnings

from sqlalchemy.ext.asyncio import AsyncSession

_contextos_advertidos: set[str] = set()


def advertir_si_with_for_update_es_no_op(db: AsyncSession, contexto: str) -> None:
    """Avisa una sola vez por contexto+dialecto por proceso, para no inundar los logs."""
    dialecto = db.bind.dialect.name if db.bind is not None else None
    if dialecto == "postgresql":
        return

    clave = f"{contexto}:{dialecto}"
    if clave in _contextos_advertidos:
        return
    _contextos_advertidos.add(clave)
    warnings.warn(
        f"{contexto}: with_for_update() no bloquea nada en el dialecto '{dialecto}' — "
        "la protección anti-carrera entre procesos NO está activa aquí. Esperado en "
        "pruebas (SQLite); si esto aparece en producción, algo está mal configurado.",
        stacklevel=2,
    )
