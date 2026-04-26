from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401
from db import Base, engine, ensure_sqlite_schema
from routes.activity import router as activity_router
from routes.attendees import router as attendees_router
from routes.matching import router as matching_router
from routes.matches import router as matches_router
from routes.signup import router as signup_router
from routes.webhooks import router as webhooks_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()


@app.get("/health")
def health_check() -> dict[str, bool]:
    return {"ok": True}


app.include_router(signup_router)
app.include_router(attendees_router)
app.include_router(matching_router)
app.include_router(activity_router)
app.include_router(matches_router)
app.include_router(webhooks_router)
