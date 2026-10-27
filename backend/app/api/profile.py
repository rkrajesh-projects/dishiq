from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.profile import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["User Profile"])


@router.get("", response_model=ProfileRead, summary="Get Current User Profile")
def get_profile(db: Session = Depends(get_db), user = Depends(get_current_user)):
    """Retrieve the current user profile and preferences."""
    if not user.preference:
        from app.models.user import UserPreference
        pref = UserPreference(
            user_id=user.id,
            dietary_type="None",
            weekly_budget=2000.0,
            household_size=2,
            disliked_ingredients=[],
        )
        db.add(pref)
        db.commit()
        db.refresh(user)
    return user


@router.patch("", response_model=ProfileRead, summary="Update User Profile & Preferences")
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """Update details of the current user profile and preferences."""
    # Update User model fields
    if body.full_name is not None:
        user.full_name = body.full_name
        
    # Update UserPreference model fields
    pref = user.preference
    if not pref:
        from app.models.user import UserPreference
        pref = UserPreference(
            user_id=user.id,
            dietary_type="None",
            weekly_budget=2000.0,
            household_size=2,
            disliked_ingredients=[],
        )
        db.add(pref)
        db.flush()

    if body.dietary_type is not None:
        pref.dietary_type = body.dietary_type
    if body.weekly_budget is not None:
        pref.weekly_budget = body.weekly_budget
    if body.household_size is not None:
        pref.household_size = body.household_size
            
    db.commit()
    db.refresh(user)
    return user
