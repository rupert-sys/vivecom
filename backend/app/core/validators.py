"""Validadores de Pydantic compartidos entre varios schemas."""


def validar_clabe(v: str) -> str:
    """CLABE mexicana: exactamente 18 dígitos numéricos (dato real de Banxico)."""
    if not v.isdigit() or len(v) != 18:
        raise ValueError("La CLABE debe tener exactamente 18 dígitos numéricos")
    return v
