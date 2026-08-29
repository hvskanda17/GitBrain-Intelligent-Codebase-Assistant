from fastapi import APIRouter

from app.api.v1.routers import auth, chat, graph, projects, repositories, search, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(repositories.router)
api_router.include_router(graph.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
