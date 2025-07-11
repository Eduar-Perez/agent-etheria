from fastapi import FastAPI
from mangum import Mangum
from utilities.secrets_loader import load_aws_secrets
from api.routes import configure_routes

load_aws_secrets()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI()
    configure_routes(app)
    return app


app = create_app()
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
