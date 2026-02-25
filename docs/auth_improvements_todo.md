# Authentication Application - Improvement Todo List

## Status: Generated 2026-02-25

This document provides an actionable todo list for improving the authentication application based on the technical debt analysis and current code review.

## Recently Completed ✅

The following issues from the technical debt document have been resolved:

1. ✅ **Password validation implemented** - Min 8 chars, max 100 chars (schemas.py:41)
2. ✅ **Username validation implemented** - Pattern, min/max length (schemas.py:42)
3. ✅ **is_active field implemented** - Proper user activation (models.py:28)
4. ✅ **Better exception handling** - Using ValueError with proper messages
5. ✅ **Token type validation** - verify_token_type method (jwt.py:97)
6. ✅ **Minimal token payload** - Only sub, exp, iat, type fields
7. ✅ **is_verified field** - Email verification support (models.py:30)
8. ✅ **last_login tracking** - Updated on each login (models.py:24)
9. ✅ **Soft delete** - is_deleted field for data retention (models.py:31)
10. ✅ **Service layer** - UserSignupService for business logic

---

## Critical Priority (Fix Immediately) 🔴

### 1. Fix Transaction Safety in Signup

**File:** `minager/auth/services.py:13-35`

**Problem:**
- Signup creates records in 3 systems without proper rollback
- If knowledge tree creation fails, user is orphaned
- If profile creation fails, user + knowledge tree are orphaned
- No compensation mechanism

**Current Code:**
```python
async with managers.UserManager() as user_manager:
    user = await user_manager.create_user(user_data)
knowledge_tree_root_data = {...}
root = await knowledge_tree_client.create(knowledge_tree_root_data)
if not root:
    raise ValueError('Unable to create knowledge tree root.')
await profile_manager.create_profile(profile_data)
```

**Action Items:**
- [ ] Implement saga pattern with compensating transactions
- [ ] Add try/except blocks for each step
- [ ] Delete user if knowledge tree creation fails
- [ ] Delete user + knowledge tree if profile creation fails
- [ ] Add audit logging for failed registrations

**Priority:** CRITICAL
**Estimated effort:** 3-4 hours

---

### 2. Optimize Transaction in Login

**File:** `minager/auth/api.py:29`

**Problem:**
- TODO comment: "Can we retrieve and update in one transaction?"
- Currently opens manager twice (lines 21-22, 30-31)
- Authentication and last_login update in separate transactions

**Action Items:**
- [ ] Combine authenticate() and update_last_login() in single transaction
- [ ] Create new manager method: authenticate_and_update(email, password)
- [ ] Remove TODO comment
- [ ] Update endpoint to use single manager context

**Priority:** HIGH
**Estimated effort:** 1-2 hours

---

## High Priority (Fix Soon) 🟠

### 3. Implement Rate Limiting

**Files:** All auth endpoints

**Problem:**
- No protection against brute force attacks on login
- No limits on signup to prevent spam accounts
- Token refresh can be abused

**Action Items:**
- [ ] Install slowapi: `poetry add slowapi`
- [ ] Create rate limiting config in settings
- [ ] Add limiter to login endpoint: 5 attempts/minute per IP
- [ ] Add limiter to signup endpoint: 3 registrations/hour per IP
- [ ] Add limiter to refresh endpoint: 10 attempts/minute per user
- [ ] Add rate limit exceeded error handling
- [ ] Document rate limits in API docs

**Priority:** HIGH
**Estimated effort:** 3-4 hours

---

### 4. Implement Email Verification Workflow

**Files:** New endpoints + manager methods

**Problem:**
- is_verified field exists but never set to True
- No email verification workflow
- Users can use accounts without verifying emails

**Action Items:**
- [ ] Create verification token generation method in jwt_service
- [ ] Add send_verification_email endpoint (POST /users/verify-email/send)
- [ ] Add confirm_email endpoint (POST /users/verify-email/confirm)
- [ ] Integrate email sending (SMTP already configured in settings)
- [ ] Add email templates for verification
- [ ] Optionally block unverified users from certain actions
- [ ] Add resend verification email endpoint
- [ ] Add tests for verification flow

**Priority:** HIGH
**Estimated effort:** 6-8 hours

---

### 5. Add Comprehensive Test Coverage

**Files:** Create `tests/auth/` directory

**Problem:**
- No tests for auth module
- Cannot ensure correctness or catch regressions
- High risk of bugs in security-critical code

**Action Items:**
- [ ] Create `tests/auth/test_user_manager.py`
  - [ ] Test create_user with valid data
  - [ ] Test create_user with duplicate email
  - [ ] Test create_user with duplicate username
  - [ ] Test authenticate with valid credentials
  - [ ] Test authenticate with invalid email
  - [ ] Test authenticate with wrong password
  - [ ] Test authenticate with inactive user
  - [ ] Test authenticate with deleted user
  - [ ] Test update_user email change
  - [ ] Test update_user password change
  - [ ] Test password hashing and verification
- [ ] Create `tests/auth/test_jwt_service.py`
  - [ ] Test create_access_token
  - [ ] Test create_refresh_token
  - [ ] Test decode_token valid
  - [ ] Test decode_token expired
  - [ ] Test decode_token invalid signature
  - [ ] Test verify_token_type
  - [ ] Test refresh_access_token
- [ ] Create `tests/auth/test_api.py`
  - [ ] Test signup success
  - [ ] Test signup duplicate email
  - [ ] Test signup invalid password
  - [ ] Test login success
  - [ ] Test login invalid credentials
  - [ ] Test refresh token success
  - [ ] Test refresh token with access token (should fail)
  - [ ] Test get /users/me
  - [ ] Test update user
  - [ ] Test update profile
- [ ] Create `tests/auth/test_services.py`
  - [ ] Test UserSignupService success flow
  - [ ] Test UserSignupService rollback scenarios

**Priority:** HIGH
**Estimated effort:** 12-16 hours

---

### 6. Complete Service Method Stubs

**File:** `minager/auth/services.py:37-44`

**Problem:**
- Three methods are empty stubs: create_user, create_user_profile, create_knowledge_tree_root
- Either implement or remove them
- Unclear architectural intent

**Action Items:**
- [ ] Review if these methods should exist
- [ ] If yes, implement them with proper logic
- [ ] If no, remove them
- [ ] Consider breaking signup() into smaller methods for testability
- [ ] Add docstrings explaining purpose

**Priority:** MEDIUM
**Estimated effort:** 2-3 hours

---

## Medium Priority (Plan to Fix) 🟡

### 7. Implement Audit Logging

**Files:** All auth operations

**Problem:**
- No logging of authentication events
- Failed login attempts not tracked
- Cannot detect suspicious activity
- No audit trail for investigations

**Action Items:**
- [ ] Create audit logger configuration
- [ ] Add logging to login endpoint (success/failure)
- [ ] Add logging to signup endpoint
- [ ] Add logging to token refresh
- [ ] Add logging to password changes
- [ ] Add logging to email changes
- [ ] Include IP address, user agent in logs
- [ ] Consider structured logging (JSON format)
- [ ] Add log rotation configuration

**Priority:** MEDIUM
**Estimated effort:** 4-6 hours

---

### 8. Implement Token Revocation/Blacklisting

**Files:** New infrastructure + jwt_service updates

**Problem:**
- Cannot invalidate tokens before expiration
- No way to implement proper logout
- Compromised tokens remain valid
- No session management

**Options:**
- **Option A:** Redis-based blacklist (faster, requires Redis)
- **Option B:** Database-backed sessions (slower, no new dependencies)

**Action Items (Option A - Recommended):**
- [ ] Add Redis dependency: `poetry add redis[hiredis]`
- [ ] Configure Redis connection in settings
- [ ] Create TokenBlacklistService
- [ ] Add check_if_revoked method to jwt_service
- [ ] Create logout endpoint (POST /auth/logout)
- [ ] Add revoke_all_user_tokens method
- [ ] Integrate blacklist check into auth dependencies
- [ ] Add tests for revocation
- [ ] Document token revocation in API docs

**Priority:** MEDIUM
**Estimated effort:** 6-8 hours

---

### 9. Add Password Strength Requirements

**File:** `minager/auth/schemas.py:41`

**Problem:**
- Only min length validation (8 chars)
- No complexity requirements
- Weak passwords like "12345678" are accepted

**Action Items:**
- [ ] Add field_validator to UserCreateDataSchema
- [ ] Require at least one uppercase letter
- [ ] Require at least one lowercase letter
- [ ] Require at least one digit
- [ ] Optionally require one special character
- [ ] Check against common passwords list
- [ ] Provide clear error messages
- [ ] Add same validation to password updates
- [ ] Update API documentation
- [ ] Add tests for password validation

**Priority:** MEDIUM
**Estimated effort:** 2-3 hours

---

### 10. Add API Documentation

**Files:** All endpoints

**Problem:**
- No docstrings on many endpoints
- Missing response_model on some endpoints
- No OpenAPI descriptions
- Makes API harder to use

**Action Items:**
- [ ] Add detailed docstrings to all endpoints
- [ ] Add `summary` parameter to all routes
- [ ] Add `description` parameter with usage details
- [ ] Add `responses` parameter with error codes
- [ ] Ensure all endpoints have response_model
- [ ] Add examples in schema definitions
- [ ] Document rate limits in descriptions
- [ ] Add security scheme documentation

**Priority:** MEDIUM
**Estimated effort:** 3-4 hours

---

## Low Priority (Technical Debt) 🟢

### 11. Add More User Timestamps

**File:** `minager/auth/models.py`

**Problem:**
- Missing useful timestamps for user management

**Action Items:**
- [ ] Consider adding password_changed_at field
- [ ] Consider adding email_verified_at field
- [ ] Consider adding deleted_at field (for soft delete audit)
- [ ] Add database migration
- [ ] Update schemas

**Priority:** LOW
**Estimated effort:** 2-3 hours

---

### 12. Improve Error Messages

**Files:** managers.py, api.py

**Problem:**
- Some error messages are generic
- Could provide better UX

**Action Items:**
- [ ] Review all error messages for clarity
- [ ] Use consistent error message format
- [ ] Provide actionable error details
- [ ] Avoid exposing internal details
- [ ] Add error codes for client parsing

**Priority:** LOW
**Estimated effort:** 2-3 hours

---

### 13. Add User Search/Admin Endpoints

**Files:** New admin endpoints

**Problem:**
- No way to list users (admin function)
- No way to manage users programmatically
- No soft delete recovery

**Action Items:**
- [ ] Create admin middleware/decorator
- [ ] Add list users endpoint (GET /admin/users)
- [ ] Add get user by ID endpoint (GET /admin/users/{id})
- [ ] Add delete user endpoint (DELETE /admin/users/{id})
- [ ] Add restore deleted user endpoint (POST /admin/users/{id}/restore)
- [ ] Add deactivate user endpoint (POST /admin/users/{id}/deactivate)
- [ ] Add promote to superuser endpoint
- [ ] Protect with is_superuser check
- [ ] Add pagination
- [ ] Add filtering options

**Priority:** LOW
**Estimated effort:** 6-8 hours

---

## Future Enhancements (Low Priority) 🔵

### 14. Password Reset Workflow

**Action Items:**
- [ ] Create password reset token generation
- [ ] Add request password reset endpoint
- [ ] Add reset password endpoint
- [ ] Send password reset emails
- [ ] Add token expiration (15-30 minutes)
- [ ] Add rate limiting
- [ ] Add tests

**Estimated effort:** 6-8 hours

---

### 15. Two-Factor Authentication (2FA)

**Action Items:**
- [ ] Install TOTP library: `poetry add pyotp`
- [ ] Add 2FA secret field to User model
- [ ] Add enable 2FA endpoint
- [ ] Add verify 2FA code endpoint
- [ ] Add backup codes generation
- [ ] Update login flow for 2FA
- [ ] Add tests

**Estimated effort:** 10-12 hours

---

### 16. OAuth2 Social Login

**Action Items:**
- [ ] Install authlib: `poetry add authlib`
- [ ] Add OAuth config for providers (Google, GitHub)
- [ ] Create OAuth callback endpoints
- [ ] Link OAuth accounts to users
- [ ] Handle account creation via OAuth
- [ ] Add tests

**Estimated effort:** 12-16 hours

---

### 17. Account Lockout After Failed Attempts

**Action Items:**
- [ ] Track failed login attempts (Redis or DB)
- [ ] Lock account after N failures (5-10)
- [ ] Add lockout duration (15-30 minutes)
- [ ] Add unlock account endpoint
- [ ] Send email notification on lockout
- [ ] Add tests

**Estimated effort:** 4-6 hours

---

### 18. Session Management UI/API

**Action Items:**
- [ ] Store active sessions in Redis/DB
- [ ] Add list active sessions endpoint
- [ ] Add revoke session endpoint
- [ ] Add revoke all other sessions endpoint
- [ ] Track device/location info
- [ ] Add tests

**Estimated effort:** 8-10 hours

---

## Implementation Roadmap

### Sprint 1: Critical Fixes (Week 1)
- [ ] Task #1: Fix transaction safety in signup
- [ ] Task #2: Optimize transaction in login
- [ ] Task #3: Implement rate limiting

**Total effort:** 7-10 hours

---

### Sprint 2: Core Features (Week 2-3)
- [ ] Task #4: Implement email verification
- [ ] Task #5: Add comprehensive test coverage
- [ ] Task #6: Complete service method stubs

**Total effort:** 20-27 hours

---

### Sprint 3: Security Hardening (Week 4-5)
- [ ] Task #7: Implement audit logging
- [ ] Task #8: Implement token revocation
- [ ] Task #9: Add password strength requirements

**Total effort:** 12-17 hours

---

### Sprint 4: Polish & Documentation (Week 6)
- [ ] Task #10: Add API documentation
- [ ] Task #11: Add more timestamps
- [ ] Task #12: Improve error messages

**Total effort:** 7-10 hours

---

### Sprint 5: Admin Features (Future)
- [ ] Task #13: Add user search/admin endpoints
- [ ] Task #14: Password reset workflow
- [ ] Task #17: Account lockout

**Total effort:** 16-22 hours

---

### Sprint 6: Advanced Features (Future)
- [ ] Task #15: Two-factor authentication
- [ ] Task #16: OAuth2 social login
- [ ] Task #18: Session management

**Total effort:** 30-38 hours

---

## Progress Tracking

**Total Tasks:** 18
**Completed:** 0
**In Progress:** 0
**Not Started:** 18

**Total Estimated Effort:** 92-132 hours

---

## Notes

- Prioritize tasks based on security impact and user needs
- Each task should include unit and integration tests
- Update documentation as features are implemented
- Consider breaking larger tasks into sub-tasks
- Review and update this document periodically

---

## Quick Wins (Can be done in < 2 hours each)

1. Task #2: Optimize login transaction
2. Task #6: Complete service stubs
3. Task #9: Add password strength
4. Task #11: Add timestamps
5. Task #12: Improve error messages

Start with these for immediate impact!
