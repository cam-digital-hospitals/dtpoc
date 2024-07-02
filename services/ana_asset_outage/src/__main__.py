from .conf import HOST, PORT
from .main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host=HOST, port=PORT)
