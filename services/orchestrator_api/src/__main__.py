import logging
from .conf import HOST, PORT
from .main import app

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app=app, host=HOST, port=PORT)
