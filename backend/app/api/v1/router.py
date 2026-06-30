from fastapi import APIRouter

from backend.app.api.v1 import (
    art_style,
    assets,
    audit,
    billing,
    captions,
    health,
    identity,
    jobs,
    music,
    projects,
    provider,
    scenes,
    scripts,
    videos,
    voiceovers,
)

router = APIRouter()
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(assets.router, tags=["assets"])
router.include_router(billing.router, prefix="/projects", tags=["billing"])
router.include_router(health.router, tags=["health"])
router.include_router(identity.router, tags=["identity"])
router.include_router(provider.router, prefix="/provider", tags=["provider"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
router.include_router(voiceovers.router, prefix="/voiceovers", tags=["voiceovers"])
router.include_router(music.router, prefix="/background-music", tags=["music"])
router.include_router(art_style.router, prefix="/art-style", tags=["art-style"])
router.include_router(scenes.router, tags=["scenes"])
router.include_router(videos.router, prefix="/videos", tags=["videos"])
router.include_router(captions.router, prefix="/caption-style", tags=["captions"])
