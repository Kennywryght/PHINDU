"""
Shared FastAPI dependencies for authorization.

Usage in routes:

    from app.api.deps import require_role

    @router.post("/", dependencies=[Depends(require_role("owner", "manager"))])
    def create_something(...): ...

    # Or with the current user available:
    def create_something(
        current_user: User = Depends(require_role("owner")),
        ...
    ): ...
"""

from fastapi import Depends, HTTPException, status

from app.api.routes.auth import get_current_user
from app.db.models.user import User

ROLE_HIERARCHY = {
    "cashier": 0,
    "manager": 1,
    "owner": 2,
}


def require_role(*allowed_roles: str):
    """
    Dependency factory. Returns a dependency that:
      - Authenticates the user (via get_current_user)
      - Checks their role is one of allowed_roles
      - Returns the User object

    Use as `Depends(require_role("owner"))` or with multiple roles.
    """
    if not allowed_roles:
        raise ValueError("require_role needs at least one role")

    invalid = set(allowed_roles) - set(ROLE_HIERARCHY.keys())
    if invalid:
        raise ValueError(f"Unknown roles: {invalid}. Valid: {list(ROLE_HIERARCHY)}")

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires one of: {', '.join(allowed_roles)}. "
                    f"Your role: {current_user.role}."
                ),
            )
        return current_user

    return checker


def require_min_role(min_role: str):
    """
    Dependency factory requiring AT LEAST the given role in the hierarchy.
    Cashier < Manager < Owner.

    Example: require_min_role("manager") allows manager AND owner.
    """
    if min_role not in ROLE_HIERARCHY:
        raise ValueError(f"Unknown role: {min_role}")

    min_level = ROLE_HIERARCHY[min_role]

    def checker(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, -1)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires at least '{min_role}' role. "
                    f"Your role: {current_user.role}."
                ),
            )
        return current_user

    return checker
