from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.jwt_handler import hash_password
from app.auth.middleware import get_current_user, require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(dependencies=[Depends(get_current_user), Depends(require_admin)])


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.role is not None:
        if body.role not in ("admin", "operator"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role must be admin or operator")
        user.role = body.role

    if body.password is not None:
        user.password_hash = hash_password(body.password)

    db.commit()
    db.refresh(user)

    log_action(
        db, int(current_user["sub"]), "update_user", "user", user_id,
        f"username={user.username} role={user.role}",
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if int(current_user["sub"]) == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    admin_count = db.query(User).filter(User.role == "admin").count()
    if user.role == "admin" and admin_count <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the last admin user")

    username = user.username
    db.delete(user)
    db.commit()

    log_action(db, int(current_user["sub"]), "delete_user", "user", user_id, f"username={username}")
