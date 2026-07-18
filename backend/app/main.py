from pathlib import Path

from fastapi import FastAPI


STATIC_DIR = Path(__file__).parent / "static"


def create_app(static_dir: Path = STATIC_DIR) -> FastAPI:
    app = FastAPI(title="Project Management MVP")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/hello")
    def hello() -> dict[str, str]:
        return {"message": "Hello from FastAPI"}

    app.frontend("/", directory=static_dir)
    return app


app = create_app()
