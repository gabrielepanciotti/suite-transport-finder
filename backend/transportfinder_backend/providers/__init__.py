"""Transport providers: one module per carrier, all speaking :mod:`.base`."""

from . import flixbus, itabus, trenitalia
from .base import Journey, Provider

PROVIDERS = {"train": trenitalia, "bus": flixbus, "itabus": itabus}

__all__ = ["Journey", "Provider", "PROVIDERS", "flixbus", "itabus", "trenitalia"]
