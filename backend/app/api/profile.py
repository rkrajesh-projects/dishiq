from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.pantry import get_current_user
from app.schemas.profile import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["User Profile"])


@router.get("", response_model=ProfileRead, summary="Get Current User Profile")
def get_profile(db: Session = Depends(get_db)):
    """Retrieve the current user profile and preferences."""
    user = get_current_user(db)
    return user


@router.patch("", response_model=ProfileRead, summary="Update User Profile & Preferences")
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db)):
    """Update details of the current user profile and preferences."""
    user = get_current_user(db)
    
    # Update User model fields
    if body.full_name is not None:
        user.full_name = body.full_name
        
    # Update UserPreference model fields
    pref = user.preference
    if pref:
        if body.dietary_type is not None:
            pref.dietary_type = body.dietary_type
        if body.weekly_budget is not None:
            pref.weekly_budget = body.weekly_budget
        if body.household_size is not None:
            pref.household_size = body.household_size
            
    db.commit()
    db.refresh(user)
    return user
