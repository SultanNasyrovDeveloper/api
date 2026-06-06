"""
Concrete permission classes for common authorization scenarios.

This module provides ready-to-use permission classes for:
- Authentication checks
- Superuser checks
- Resource ownership checks
- Node-specific permissions
"""

from uuid import UUID

from fastapi import Request, status

from minager.auth.models import User
from minager.core.api.permissions import BasePermission


class IsAuthenticated(BasePermission):
    """
    Requires user to be authenticated (valid JWT token).

    This permission checks if a valid user exists in the context.
    Use this as the base permission for all protected endpoints.

    Usage:
        @permissions(IsAuthenticated)
        async def get_profile():
            return {"profile": "data"}
    """

    error_message = 'Authentication required'
    status_code = status.HTTP_401_UNAUTHORIZED

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if user is authenticated."""
        user = context.get('user')
        return bool(user)


class IsSuperuser(BasePermission):
    """
    Requires user to be a superuser.

    Use this for admin-only endpoints.

    Usage:
        @permissions(IsAuthenticated, IsSuperuser)
        async def admin_panel():
            return {"admin": "panel"}
    """

    error_message = 'Superuser privileges required'
    status_code = status.HTTP_403_FORBIDDEN

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if user is a superuser."""
        user: User | None = context.get('user')

        if not user:
            return False

        return user.is_superuser


class IsActive(BasePermission):
    """
    Requires user account to be active (not deactivated).

    Usage:
        @permissions(IsAuthenticated, IsActive)
        async def post_comment():
            return {"comment": "posted"}
    """

    error_message = 'Your account is not active'
    status_code = status.HTTP_403_FORBIDDEN

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if user account is active."""
        user: User | None = context.get('user')

        if not user:
            return False

        return user.is_active


class IsVerified(BasePermission):
    """
    Requires user email to be verified.

    Usage:
        @permissions(IsAuthenticated, IsVerified)
        async def create_post():
            return {"post": "created"}
    """

    error_message = 'Email verification required'
    status_code = status.HTTP_403_FORBIDDEN

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if user email is verified."""
        user: User | None = context.get('user')

        if not user:
            return False

        return user.is_verified


class IsOwnerOf(BasePermission):
    """
    Base class for resource ownership checks.

    Subclass this to check ownership of specific resources.
    Override get_resource_owner_id() to extract owner from the resource.

    Example:
        class IsNodeOwner(IsOwnerOf):
            async def get_resource_owner_id(self, request, **context) -> str | None:
                node = context.get('node')
                return node.owner_id if node else None
    """

    error_message = 'You must be the owner of this resource'
    status_code = status.HTTP_403_FORBIDDEN

    async def get_resource_owner_id(self, request: Request, **context) -> str | UUID | None:
        """
        Extract owner ID from resource.

        Override this method in subclasses to specify how to get the owner.

        Args:
            request: FastAPI Request
            **context: Context containing user, resource, etc.

        Returns:
            Owner ID as string or UUID, or None if not found
        """
        raise NotImplementedError('Subclasses must implement get_resource_owner_id()')

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if user owns the resource."""
        user: User | None = context.get('user')

        if not user:
            return False

        resource_owner_id = await self.get_resource_owner_id(request, **context)

        if not resource_owner_id:
            # Resource or owner not found
            return False

        # Compare user ID with resource owner ID
        return str(user.id) == str(resource_owner_id)


class IsNodeOwner(IsOwnerOf):
    """
    Requires user to own the node being accessed.

    This permission extracts the node from:
    1. Context (if node was already fetched)
    2. Request path parameters (node_id or uid)
    3. App state to fetch the node

    Usage:
        @permissions(IsAuthenticated, IsNodeOwner)
        async def update_node(node_id: str, app: App):
            return await app.state.nodes.update(node_id, data)
    """

    error_message = 'You must be the owner of this node'

    async def get_resource_owner_id(self, request: Request, **context) -> str | None:
        """Extract node owner ID."""
        # Try to get node from context first (if already fetched)
        node = context.get('node')

        if node:
            return node.owner_id

        # Try to get node from app state
        app = context.get('app')
        if not app:
            # App not in context, try to get from request
            app = getattr(request.app, 'state', None)

        if not app:
            return None

        # Extract node_id from path parameters
        node_id = request.path_params.get('node_id') or request.path_params.get('uid')

        if not node_id:
            return None

        # Fetch node from database
        try:
            node = await app.nodes.get(node_id)
            if node:
                # Store in context for reuse
                context['node'] = node
                return node.owner_id
        except Exception:
            # Node not found or error fetching
            return None

        return None


class IsProfileOwner(IsOwnerOf):
    """
    Requires user to own the profile being accessed.

    Usage:
        @permissions(IsAuthenticated, IsProfileOwner)
        async def update_profile(profile_id: int):
            return {"profile": "updated"}
    """

    error_message = 'You must be the owner of this profile'

    async def get_resource_owner_id(self, request: Request, **context) -> UUID | None:
        """Extract profile owner ID."""
        # Profile owner is the user_id field
        profile = context.get('profile')

        if profile:
            return profile.user_id

        # Could implement fetching profile from app state similar to IsNodeOwner
        return None


class IsSelfOrSuperuser(BasePermission):
    """
    Allows access if user is viewing their own resource OR is a superuser.

    Useful for user profile endpoints where users can view/edit their own
    data, but admins can view/edit anyone's data.

    Usage:
        @permissions(IsAuthenticated, IsSelfOrSuperuser)
        async def get_user(user_id: UUID):
            return {"user": "data"}
    """

    error_message = 'You can only access your own resources unless you are a superuser'

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if user is accessing their own resource or is superuser."""
        user: User | None = context.get('user')

        if not user:
            return False

        # Superusers can access anything
        if user.is_superuser:
            return True

        # Extract user_id from path parameters
        target_user_id = request.path_params.get('user_id') or request.path_params.get('id')

        if not target_user_id:
            # No target user specified, can't determine
            return False

        # Check if accessing own resource
        return str(user.id) == str(target_user_id)


class ReadOnly(BasePermission):
    """
    Allows only safe HTTP methods (GET, HEAD, OPTIONS).

    Use this to create read-only endpoints.

    Usage:
        @permissions(IsAuthenticated, ReadOnly)
        async def get_data():
            return {"data": "read-only"}
    """

    error_message = 'This endpoint is read-only'

    async def has_permission(self, request: Request, **context) -> bool:
        """Check if request method is safe."""
        return request.method in ('GET', 'HEAD', 'OPTIONS')
