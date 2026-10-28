from fastapi import APIRouter

from app.api import auth, emails, leads, misc, properties, tasks

api_router = APIRouter()
for m in (auth, leads, properties, tasks, emails, misc):
    api_router.include_router(m.router)
