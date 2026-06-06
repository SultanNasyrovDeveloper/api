import inspect
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request

from minager.core.api.permission_classes import (
    IsActive,
    IsAuthenticated,
    IsSelfOrSuperuser,
    IsSuperuser,
    IsVerified,
    ReadOnly,
)
from minager.core.api.permissions import AllOf, AnyOf, BasePermission, Not, permissions


class AlwaysAllow(BasePermission):
    """Permission that always passes."""

    async def has_permission(self, request: Request, **context) -> bool:
        return True


class AlwaysDeny(BasePermission):
    """Permission that always fails."""

    error_message = 'Access denied by AlwaysDeny'

    async def has_permission(self, request: Request, **context) -> bool:
        return False


class RequireHeaderPermission(BasePermission):
    """Permission that requires specific header."""

    error_message = 'X-Test-Header is required'

    async def has_permission(self, request: Request, **context) -> bool:
        return request.headers.get('X-Test-Header') == 'allowed'


@pytest.mark.asyncio
async def test_permissions_decorator_injects_parameter():
    """Test that @permissions() adds a parameter to function signature."""

    @permissions(AlwaysAllow)
    async def test_endpoint():
        return {'status': 'ok'}

    # Check that signature was modified
    sig = inspect.signature(test_endpoint)
    params = list(sig.parameters.keys())

    # Should have injected parameter
    assert '_minager_permission_check' in params


@pytest.mark.asyncio
async def test_permissions_decorator_preserves_original_params():
    """Test that @permissions() preserves original function parameters."""

    @permissions(AlwaysAllow)
    async def test_endpoint(user_id: int, name: str):
        return {'user_id': user_id, 'name': name}

    sig = inspect.signature(test_endpoint)
    params = list(sig.parameters.keys())

    # Original parameters should still be there
    assert 'user_id' in params
    assert 'name' in params
    # Plus injected parameter
    assert '_minager_permission_check' in params


@pytest.mark.asyncio
async def test_permissions_decorator_has_depends():
    """Test that injected parameter has Depends() default."""

    @permissions(AlwaysAllow)
    async def test_endpoint():
        return {'status': 'ok'}

    sig = inspect.signature(test_endpoint)
    perm_param = sig.parameters['_minager_permission_check']

    # Should have Depends() as default (check by type name since Depends is not a type)
    assert perm_param.default.__class__.__name__ == 'Depends'


@pytest.mark.asyncio
async def test_always_allow_permission_passes(mock_user):
    """Test that AlwaysAllow permission passes."""
    perm = AlwaysAllow()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_always_deny_permission_fails(mock_user):
    """Test that AlwaysDeny permission fails."""
    perm = AlwaysDeny()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is False


@pytest.mark.asyncio
async def test_permission_raises_http_exception():
    """Test that permission can raise HTTPException."""
    perm = AlwaysDeny()

    with pytest.raises(HTTPException) as exc_info:
        perm.raise_permission_denied()

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied by AlwaysDeny'


@pytest.mark.asyncio
async def test_permission_custom_error_message():
    """Test that permission can use custom error message."""
    perm = AlwaysDeny()

    with pytest.raises(HTTPException) as exc_info:
        perm.raise_permission_denied(detail='Custom error')

    assert exc_info.value.detail == 'Custom error'


@pytest.mark.asyncio
async def test_is_authenticated_passes_with_user(mock_user):
    """Test that IsAuthenticated passes when user is present."""
    perm = IsAuthenticated()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_is_authenticated_fails_without_user():
    """Test that IsAuthenticated fails when user is None."""
    perm = IsAuthenticated()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=None)
    assert result is False


@pytest.mark.asyncio
async def test_is_authenticated_has_401_status():
    """Test that IsAuthenticated uses 401 status code."""
    perm = IsAuthenticated()
    assert perm.status_code == 401


@pytest.mark.asyncio
async def test_is_superuser_passes_for_superuser(mock_superuser):
    """Test that IsSuperuser passes for superuser."""
    perm = IsSuperuser()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_superuser)
    assert result is True


@pytest.mark.asyncio
async def test_is_superuser_fails_for_regular_user(mock_user):
    """Test that IsSuperuser fails for regular user."""
    perm = IsSuperuser()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is False


@pytest.mark.asyncio
async def test_is_superuser_fails_without_user():
    """Test that IsSuperuser fails when user is None."""
    perm = IsSuperuser()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=None)
    assert result is False


@pytest.mark.asyncio
async def test_is_active_passes_for_active_user(mock_user):
    """Test that IsActive passes for active user."""
    perm = IsActive()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_is_active_fails_for_inactive_user(mock_inactive_user):
    """Test that IsActive fails for inactive user."""
    perm = IsActive()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_inactive_user)
    assert result is False


@pytest.mark.asyncio
async def test_is_verified_passes_for_verified_user(mock_user):
    """Test that IsVerified passes for verified user."""
    perm = IsVerified()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_is_verified_fails_for_unverified_user(mock_unverified_user):
    """Test that IsVerified fails for unverified user."""
    perm = IsVerified()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_unverified_user)
    assert result is False


@pytest.mark.asyncio
async def test_readonly_allows_get():
    """Test that ReadOnly allows GET requests."""
    perm = ReadOnly()
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request)
    assert result is True


@pytest.mark.asyncio
async def test_readonly_allows_head():
    """Test that ReadOnly allows HEAD requests."""
    perm = ReadOnly()
    request = Request(scope={'type': 'http', 'method': 'HEAD', 'headers': []})

    result = await perm.has_permission(request)
    assert result is True


@pytest.mark.asyncio
async def test_readonly_denies_post():
    """Test that ReadOnly denies POST requests."""
    perm = ReadOnly()
    request = Request(scope={'type': 'http', 'method': 'POST', 'headers': []})

    result = await perm.has_permission(request)
    assert result is False


@pytest.mark.asyncio
async def test_readonly_denies_delete():
    """Test that ReadOnly denies DELETE requests."""
    perm = ReadOnly()
    request = Request(scope={'type': 'http', 'method': 'DELETE', 'headers': []})

    result = await perm.has_permission(request)
    assert result is False


@pytest.mark.asyncio
async def test_is_self_or_superuser_allows_superuser(mock_superuser):
    """Test that IsSelfOrSuperuser allows superuser to access any resource."""
    perm = IsSelfOrSuperuser()
    other_user_id = uuid4()

    request = Request(
        scope={
            'type': 'http',
            'method': 'GET',
            'headers': [],
            'path_params': {'user_id': str(other_user_id)},
        }
    )

    result = await perm.has_permission(request, user=mock_superuser)
    assert result is True


@pytest.mark.asyncio
async def test_is_self_or_superuser_allows_self(mock_user):
    """Test that IsSelfOrSuperuser allows user to access their own resource."""
    perm = IsSelfOrSuperuser()

    request = Request(
        scope={
            'type': 'http',
            'method': 'GET',
            'headers': [],
            'path_params': {'user_id': str(mock_user.id)},
        }
    )

    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_is_self_or_superuser_denies_other(mock_user):
    """Test that IsSelfOrSuperuser denies access to other users' resources."""
    perm = IsSelfOrSuperuser()
    other_user_id = uuid4()

    request = Request(
        scope={
            'type': 'http',
            'method': 'GET',
            'headers': [],
            'path_params': {'user_id': str(other_user_id)},
        }
    )

    result = await perm.has_permission(request, user=mock_user)
    assert result is False


@pytest.mark.asyncio
async def test_anyof_passes_if_one_passes(mock_user):
    """Test that AnyOf passes if at least one permission passes."""
    perm = AnyOf(AlwaysDeny, AlwaysAllow, AlwaysDeny)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_anyof_fails_if_all_fail(mock_user):
    """Test that AnyOf fails if all permissions fail."""
    perm = AnyOf(AlwaysDeny, AlwaysDeny)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    # AnyOf should raise exception when all permissions fail
    result = await perm.has_permission(request, user=mock_user)
    assert result is False


@pytest.mark.asyncio
async def test_anyof_with_authenticated_or_superuser(mock_user, mock_superuser):
    """Test AnyOf with real permissions (authenticated OR superuser)."""
    # Regular user should pass (authenticated)
    perm = AnyOf(IsAuthenticated, IsSuperuser)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is True

    # Superuser should also pass
    result = await perm.has_permission(request, user=mock_superuser)
    assert result is True


@pytest.mark.asyncio
async def test_allof_passes_if_all_pass(mock_user):
    """Test that AllOf passes if all permissions pass."""
    perm = AllOf(AlwaysAllow, AlwaysAllow)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_allof_fails_if_one_fails(mock_user):
    """Test that AllOf fails if any permission fails."""
    perm = AllOf(AlwaysAllow, AlwaysDeny)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    result = await perm.has_permission(request, user=mock_user)
    assert result is False


@pytest.mark.asyncio
async def test_allof_with_authenticated_and_active(mock_user, mock_inactive_user):
    """Test AllOf with real permissions (authenticated AND active)."""
    perm = AllOf(IsAuthenticated, IsActive)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    # Active user should pass
    result = await perm.has_permission(request, user=mock_user)
    assert result is True

    # Inactive user should fail
    result = await perm.has_permission(request, user=mock_inactive_user)
    assert result is False


@pytest.mark.asyncio
async def test_not_inverts_permission(mock_user):
    """Test that Not inverts permission result."""
    perm = Not(AlwaysDeny)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    # AlwaysDeny fails, so Not(AlwaysDeny) should pass
    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_not_with_superuser(mock_user):
    """Test Not with real permission (NOT superuser)."""
    perm = Not(IsSuperuser)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    # Regular user is NOT superuser, should pass
    result = await perm.has_permission(request, user=mock_user)
    assert result is True


@pytest.mark.asyncio
async def test_not_with_superuser_fails(mock_superuser):
    """Test Not with superuser (should fail)."""
    perm = Not(IsSuperuser)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    # Superuser is superuser, so NOT superuser should fail
    result = await perm.has_permission(request, user=mock_superuser)
    assert result is False


@pytest.mark.asyncio
async def test_complex_permission_logic(mock_user, mock_superuser):
    """Test complex nested permission logic: (Authenticated AND Active) OR Superuser."""
    perm = AnyOf(AllOf(IsAuthenticated, IsActive), IsSuperuser)
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    # Active authenticated user should pass
    result = await perm.has_permission(request, user=mock_user)
    assert result is True

    # Superuser should pass (even if not active)
    result = await perm.has_permission(request, user=mock_superuser)
    assert result is True


@pytest.mark.asyncio
async def test_authenticated_and_not_banned(mock_user):
    """Test combining permissions: Authenticated AND NOT Superuser."""
    # Create a permission combo: must be authenticated but NOT superuser
    perm = AllOf(IsAuthenticated, Not(IsSuperuser))
    request = Request(scope={'type': 'http', 'method': 'GET', 'headers': []})

    # Regular user (authenticated, not superuser) should pass
    result = await perm.has_permission(request, user=mock_user)
    assert result is True
