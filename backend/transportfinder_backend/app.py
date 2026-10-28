from suite_backend_core import create_app
from suite_backend_core.vista import MemoryPreferenceStore, make_vista_router
from suite_backend_core.vista_claims import make_claims_dependency

from .errors import install_error_handlers
from .routes import router
from .vista import load_vista_spec

def create_application():
    """Create an application instance; keeping this factory makes auth opt-ins testable."""
    application = create_app()
    install_error_handlers(application)
    application.include_router(router)
    application.include_router(
        make_vista_router(
            load_vista_spec(),
            MemoryPreferenceStore(),
            make_claims_dependency("transportfinder"),
            "transportfinder",
        )
    )
    return application


app = create_application()
