from fastapi import APIRouter

from backend.app.api.v1 import (
    art_style,
    captions,
    health,
    music,
    scenes,
    scripts,
    videos,
    voiceovers,
)

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
router.include_router(voiceovers.router, prefix="/voiceovers", tags=["voiceovers"])
router.include_router(music.router, prefix="/background-music", tags=["music"])
router.include_router(art_style.router, prefix="/art-style", tags=["art-style"])
router.include_router(scenes.router, tags=["scenes"])
router.include_router(videos.router, prefix="/videos", tags=["videos"])
router.include_router(captions.router, prefix="/caption-style", tags=["captions"])
