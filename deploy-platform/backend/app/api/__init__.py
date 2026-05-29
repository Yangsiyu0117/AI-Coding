from fastapi import APIRouter

from app.api import auth, config, services, packages, upgrades, patrol, environments, audit, users

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(config.router, prefix="/config", tags=["config"])
router.include_router(services.router, prefix="/services", tags=["services"])
router.include_router(packages.router, prefix="/packages", tags=["packages"])
router.include_router(upgrades.router, prefix="/upgrades", tags=["upgrades"])
router.include_router(upgrades.ws_router, prefix="/upgrades", tags=["upgrades"])
router.include_router(patrol.router, prefix="/patrol", tags=["patrol"])
router.include_router(environments.router, prefix="/environments", tags=["environments"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(users.router, prefix="/users", tags=["users"])
