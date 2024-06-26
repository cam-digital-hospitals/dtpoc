from .conf import PORT
from .main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, port=PORT)
