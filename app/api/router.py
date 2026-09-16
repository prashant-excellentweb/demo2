from fastapi import APIRouter

from app.api.routes import attachments, auth, chats, projects, search, users

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(chats.router)
api_router.include_router(chats.ephemeral_router)
api_router.include_router(attachments.router)
api_router.include_router(search.router)
