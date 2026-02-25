"""
Permission system for FastAPI applications.

Provides a reusable, composable permission framework using signature injection
to add dependencies without modifying function signatures.

Usage:
    @router.get("/resource/{id}")
    @permissions(IsAuthenticated, IsOwner)
    async def get_resource(id: str):
        # Permissions checked automatically before this runs
        return {"resource": id}
"""

import inspect
from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, Type

from fastapi import Depends, HTTPException, Request, status

from minager.auth.dependencies import CurrentActiveUser


class BasePermission(ABC):
    """
    Base class for all permission checks.

    Subclasses must implement has_permission() which returns True if permission
    is granted, or raises HTTPException if denied.

    Attributes:
        error_message: Default error message for permission denial
        status_code: HTTP status code for permission denial (default: 403)
    """

    error_message: str = 'Permission denied'
    status_code: int = status.HTTP_403_FORBIDDEN

    @abstractmethod
    async def has_permission(self, request: Request, **context) -> bool:
        """
        Check if the request has permission.

        Args:
            request: FastAPI Request object
            **context: Additional context (user, resource, app state, etc.)

        Returns:
            True if permission granted

        Raises:
            HTTPException: If permission denied
        """

    def raise_permission_denied(self, detail: str | None = None) -> None:
        """
        Raise permission denied exception.

        Args:
            detail: Optional custom error message
        """
        raise HTTPException(
            status_code=self.status_code,
            detail=detail or self.error_message,
        )


def permissions(*permission_classes: Type[BasePermission]) -> Callable:
    """
    Decorator that injects permission dependency into function signature.

    This decorator modifies the function signature to add a hidden parameter
    with a Depends() that checks all permissions. FastAPI processes this
    dependency automatically before calling your endpoint function.

    Usage:
        @router.get("/data")
        @permissions(IsAuthenticated, IsAdmin)
        async def get_data():
            return {"data": "sensitive"}

    Args:
        *permission_classes: Permission classes to check (in order)

    Returns:
        Decorator function that injects permission checking
    """

    async def permission_checker(
        request: Request, current_user: CurrentActiveUser
    ) -> CurrentActiveUser:
        """
        Dependency that checks all permissions.

        Args:
            request: FastAPI Request object
            current_user: Authenticated user from CurrentActiveUser dependency

        Returns:
            current_user if all permissions pass

        Raises:
            HTTPException: If any permission check fails
        """
        context = {'user': current_user, 'request': request}

        for perm_class in permission_classes:
            perm = perm_class()

            if not await perm.has_permission(request, **context):
                perm.raise_permission_denied()

        return current_user

    def decorator(func: Callable) -> Callable:
        """
        Decorator that modifies function signature to inject permission dependency.

        Args:
            func: Original endpoint function

        Returns:
            Wrapped function with modified signature
        """
        # Get the original function signature
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        # Add our permission dependency as a parameter
        # Use a unique internal name to avoid conflicts
        perm_param = inspect.Parameter(
            '_minager_permission_check',
            inspect.Parameter.KEYWORD_ONLY,
            default=Depends(permission_checker),
            annotation=type(None),  # Hidden from OpenAPI docs
        )
        params.append(perm_param)

        # Create new signature with injected parameter
        new_sig = sig.replace(parameters=params)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            """Wrapper that removes injected parameter before calling original function."""
            # Remove the injected parameter before calling original function
            kwargs.pop('_minager_permission_check', None)
            return await func(*args, **kwargs)

        # Attach new signature so FastAPI sees the Depends()
        wrapper.__signature__ = new_sig

        return wrapper

    return decorator


# ─── Permission Combinators ──────────────────────────────────────────────────


class AnyOf(BasePermission):
    """
    Passes if ANY of the given permissions pass (OR logic).

    Usage:
        @permissions(IsAuthenticated, AnyOf(IsOwner, IsSuperuser))
        async def update_resource(...):
            # User must be authenticated AND (owner OR superuser)
            ...
    """

    def __init__(self, *permission_classes: Type[BasePermission] | BasePermission):
        self.permission_classes = permission_classes
        self.error_message = 'None of the required permissions are satisfied'

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if any permission passes."""
        for perm_class_or_instance in self.permission_classes:
            try:
                # Handle both classes and instances
                if isinstance(perm_class_or_instance, BasePermission):
                    perm = perm_class_or_instance
                else:
                    perm = perm_class_or_instance()

                if await perm.has_permission(request, **context):
                    return True
            except HTTPException:
                # Permission raised exception (failed), continue to next
                continue

        # None passed, return False (let caller handle exception)
        return False


class AllOf(BasePermission):
    """
    Passes only if ALL of the given permissions pass (AND logic).

    This is redundant when using @permissions() (which already uses AND),
    but useful for nested permission logic.

    Usage:
        @permissions(AnyOf(AllOf(IsOwner, IsActive), IsSuperuser))
        async def update_resource(...):
            # User must be (owner AND active) OR superuser
            ...
    """

    def __init__(self, *permission_classes: Type[BasePermission] | BasePermission):
        self.permission_classes = permission_classes
        self.error_message = 'All required permissions must be satisfied'

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if all permissions pass."""
        for perm_class_or_instance in self.permission_classes:
            # Handle both classes and instances
            if isinstance(perm_class_or_instance, BasePermission):
                perm = perm_class_or_instance
            else:
                perm = perm_class_or_instance()

            if not await perm.has_permission(request, **context):
                # One failed, so all failed
                return False

        return True


class Not(BasePermission):
    """
    Inverts a permission (NOT logic).

    Usage:
        @permissions(IsAuthenticated, Not(IsBanned))
        async def post_comment(...):
            # User must be authenticated and NOT banned
            ...
    """

    def __init__(self, permission_class: Type[BasePermission]):
        self.permission_class = permission_class
        self.error_message = f'Must not have {permission_class.__name__} permission'

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if permission does NOT pass."""
        perm = self.permission_class()

        try:
            result = await perm.has_permission(request, **context)
            # If permission passed, we fail (inverse)
            return not result
        except HTTPException:
            # Permission failed (raised exception), so we pass (inverse)
            return True
