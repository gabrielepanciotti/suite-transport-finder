"""Load this node's view declaration without requiring ``node.config`` in Docker."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from suite_backend_core.vista import VistaSpec


DEFAULT_VISTA: dict[str, Any] = {
    "sezioni": [
        {"id": "cerca", "titolo": "Cerca", "min": "player"},
        {"id": "risultati", "titolo": "Risultati", "min": "player"},
        {"id": "salvati", "titolo": "Salvati", "min": "player"},
        {"id": "impostazioni", "titolo": "Impostazioni", "min": "admin"},
    ],
    "azioni": {
        "ricerca.crea": "creator",
        "ricerca.elimina": "admin",
        "salvato.crea": "creator",
        "salvato.modifica": "creator",
        "salvato.elimina": "creator",
        "impostazioni.modifica": "admin",
    },
}


def node_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "node.config"


def load_vista_spec() -> VistaSpec:
    """Return the configured view, falling back to the deployed default."""
    config_path = node_config_path()
    if not config_path.is_file():
        return VistaSpec.from_node_config({"vista": DEFAULT_VISTA})
    return VistaSpec.from_node_config(json.loads(config_path.read_text(encoding="utf-8")))
