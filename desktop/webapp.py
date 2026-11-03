from pathlib import Path
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException


class Frontend(StaticFiles):
    async def get_response(self, path, scope):
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized == "api" or normalized.startswith("api/"):
            raise HTTPException(404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or normalized.startswith("assets/"):
                raise
            return FileResponse(Path(self.directory) / "index.html", media_type="text/html")


def create_desktop_app(settings, bundle):
    from app.main import create_app
    application = create_app(settings)
    application.mount("/", Frontend(directory=bundle / "frontend/dist", html=True), name="desktop-frontend")
    return application
