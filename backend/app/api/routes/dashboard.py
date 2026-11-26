from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardData
from app.services.dashboard import build_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardData)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardData:
    return build_dashboard(db, current_user.id)
