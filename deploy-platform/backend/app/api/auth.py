import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.jwt_handler import create_access_token, decode_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate

logger = logging.getLogger("deploy_platform")

router = APIRouter()

# ── Login rate limiting ─────────────────────────────────────────────

_login_attempts: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW = 5 * 60       # 5 minutes
_RATE_LIMIT_MAX = 5               # max failed attempts in window
_RATE_LIMIT_CLEANUP = 15 * 60     # keep records for 15 minutes


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_rate_limited(client_ip: str) -> bool:
    """Return True if the IP has exceeded the rate limit."""
    now = time.time()
    if client_ip in _login_attempts:
        _login_attempts[client_ip] = [
            t for t in _login_attempts[client_ip] if now - t < _RATE_LIMIT_CLEANUP
        ]
        recent = [t for t in _login_attempts[client_ip] if now - t < _RATE_LIMIT_WINDOW]
        if len(recent) >= _RATE_LIMIT_MAX:
            return True
    return False


def _record_failed_attempt(client_ip: str):
    if client_ip not in _login_attempts:
        _login_attempts[client_ip] = []
    _login_attempts[client_ip].append(time.time())


def _clear_attempts(client_ip: str):
    _login_attempts.pop(client_ip, None)


def require_admin_if_users_exist(request: Request, db: Session = Depends(get_db)) -> dict | None:
    """Require admin auth only when users already exist (skip for first-time setup)."""
    if db.query(User).count() == 0:
        return None
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(auth_header.split(" ", 1)[1])
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return payload


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = _get_client_ip(request)

    if _check_rate_limited(client_ip):
        logger.warning(f"Rate-limited login attempt from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过于频繁，请15分钟后再试",
        )

    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        _record_failed_attempt(client_ip)
        logger.warning(f"Failed login attempt for username: {req.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    _clear_attempts(client_ip)
    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    return TokenResponse(access_token=token, username=user.username, role=user.role)


@router.post("/register", response_model=TokenResponse)
def register(req: UserCreate, db: Session = Depends(get_db), _auth: dict | None = Depends(require_admin_if_users_exist)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    # First registered user becomes admin
    is_first = db.query(User).count() == 0
    role = "admin" if is_first else req.role
    user = User(username=req.username, password_hash=hash_password(req.password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, user.id, "user_register", "user", user.id, f"username={user.username} role={role}")
    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    return TokenResponse(access_token=token, username=user.username, role=user.role)
