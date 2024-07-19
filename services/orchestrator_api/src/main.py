from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .conf import VERSION
from .deps import app_lifespan, get_mongo_client
from .routes.dt_service import router as dtservice_router
from .routes.files import router as files_router

app = FastAPI(
    title="Orchestrator API",
    root_path=f"/api/orchestrator/{VERSION}",
    openapi_url=f"/openapi.json",
    # include tags in the unique id function (default impl does not do this)
    generate_unique_id_function=lambda route: f"{route.tags[0] if len(route.tags) > 0 else 'root'}-{route.name}",
    swagger_ui_parameters={"tagsSorter": "alpha"},
    lifespan=app_lifespan,
)

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    return {'status': 'ok'}


app.include_router(dtservice_router)
app.include_router(files_router)
