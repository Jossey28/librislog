# Plan 47: Profile Danger Zone (Reset Data & Delete Account)

## Overview

Add a "Danger zone" section to the profile page with two destructive user actions:
1. **Reset all personal data**: Delete all books, reading progress entries, tags, and other user-owned reading data while preserving the user account, profile, settings, API keys, and OIDC link.
2. **Delete own account**: Completely remove the user account including all data, API keys, OIDC link, settings, and the user row itself.

Both actions are protected with a confirmation phrase input to prevent accidental execution. Account deletion is blocked if the user is the last admin in the system.

---

## 1. Files to Create

None. All changes are to existing files.

---

## 2. Files to Modify

### 2.1 Backend: `backend/app/routers/profile.py`

**Purpose**: Add two new endpoints for the danger zone actions.

#### New Endpoint 1: Reset Personal Data

```python
POST /api/profile/reset-data
```

**Request Body**:
```json
{
  "confirmation": "DELETE ALL MY DATA"
}
```

**Response**:
- **200 OK**: Data successfully reset
  ```json
  {
    "message": "All personal data has been deleted",
    "deleted": {
      "books": 42,
      "tags": 15,
      "progress_entries": 128
    }
  }
  ```
- **400 Bad Request**: Invalid confirmation phrase
  ```json
  {
    "detail": "Confirmation phrase does not match"
  }
  ```
- **401 Unauthorized**: User not authenticated

**Implementation logic**:
1. Validate confirmation phrase exactly matches `"DELETE ALL MY DATA"` (case-sensitive)
2. Within a transaction:
   - Count books, tags, and progress entries for stats
   - Delete all `ReadingProgress` entries where `user_id = current_user.id`
   - Delete all `BookTag` links for books owned by user
   - Delete all `Tag` entries where `user_id = current_user.id`
   - Delete all `Book` entries where `user_id = current_user.id`
   - Clean up orphaned cover files (reuse logic from `delete_book`)
3. Return success message with deletion counts

#### New Endpoint 2: Delete Account

```python
DELETE /api/profile/account
```

**Request Body**:
```json
{
  "confirmation": "DELETE MY ACCOUNT"
}
```

**Response**:
- **204 No Content**: Account successfully deleted, session cleared
- **400 Bad Request**: Invalid confirmation phrase
  ```json
  {
    "detail": "Confirmation phrase does not match"
  }
  ```
- **403 Forbidden**: User is the last admin
  ```json
  {
    "detail": "Cannot delete account: you are the last administrator"
  }
  ```
- **401 Unauthorized**: User not authenticated

**Implementation logic**:
1. Validate confirmation phrase exactly matches `"DELETE MY ACCOUNT"` (case-sensitive)
2. Check if user is admin AND is the last admin:
   ```python
   if current_user.role == UserRole.admin:
       admin_count = session.exec(
           select(func.count()).select_from(User).where(User.role == UserRole.admin)
       ).one()
       if admin_count <= 1:
           raise HTTPException(status_code=403, detail="Cannot delete account: you are the last administrator")
   ```
3. Within a transaction (reuse and extend logic from `/api/users/{user_id}` admin delete):
   - Delete all books and related data (call reset-data logic internally)
   - Revoke all API keys (`ApiKey.revoked_at = now()`)
   - Delete OIDC link if exists (`OidcLink` where `user_id = current_user.id`)
   - Delete user settings (`UserSettings` where `user_id = current_user.id`)
   - Delete user row (`User`)
4. Clear browser session: `clear_browser_session(request)`
5. Return 204 No Content

**Security consideration**: After deleting the account via session auth, the session is cleared. If deleting via API key, the key is revoked before the user is deleted, so the key becomes invalid.

---

### 2.2 Backend: `backend/app/schemas.py`

**Purpose**: Add request schemas for confirmation payloads.

**New schemas**:

```python
class ConfirmationPhrase(SQLModel):
    confirmation: str

class DataResetResponse(SQLModel):
    message: str
    deleted: dict[str, int]  # { "books": 42, "tags": 15, "progress_entries": 128 }
```

---

### 2.3 Frontend: `frontend/src/lib/api.ts`

**Purpose**: Add API client methods for danger zone endpoints.

**New methods in `api.profile`**:

```typescript
async resetData(confirmation: string): Promise<{ message: string; deleted: { books: number; tags: number; progress_entries: number } }> {
  return request<{ message: string; deleted: { books: number; tags: number; progress_entries: number } }>('/profile/reset-data', {
    method: 'POST',
    body: JSON.stringify({ confirmation })
  });
}

async deleteAccount(confirmation: string): Promise<void> {
  return request<void>('/profile/account', {
    method: 'DELETE',
    body: JSON.stringify({ confirmation })
  });
}
```

---

### 2.4 Frontend: `frontend/src/lib/types.ts`

**Purpose**: Add TypeScript types for API responses (if not inferred).

**New types** (if needed):

```typescript
export interface DataResetResponse {
  message: string;
  deleted: {
    books: number;
    tags: number;
    progress_entries: number;
  };
}
```

---

### 2.5 Frontend: `frontend/src/routes/profile/+page.svelte`

**Purpose**: Add Danger Zone section UI with confirmation phrase inputs.

#### UI Structure

Add a new section after the OIDC section (or at the bottom if OIDC is disabled):

```svelte
<div id="section-danger-zone" class="scroll-mt-24 card bg-error/10 border border-error/30 shadow-sm">
  <div class="card-body gap-3">
    <h2 class="text-lg font-semibold text-error">{$_('profile.dangerZone.title')}</h2>
    <p class="text-sm text-base-content/70">{$_('profile.dangerZone.subtitle')}</p>
    
    <!-- Reset Data Section -->
    <div class="border border-error/20 rounded p-4 flex flex-col gap-3">
      <h3 class="font-medium">{$_('profile.dangerZone.resetData.title')}</h3>
      <p class="text-sm text-base-content/70">{$_('profile.dangerZone.resetData.description')}</p>
      <p class="text-xs text-warning font-semibold">{$_('profile.dangerZone.resetData.warning')}</p>
      
      <input
        class="input input-bordered max-w-md"
        bind:value={resetDataConfirmation}
        placeholder={$_('profile.dangerZone.resetData.placeholder')}
      />
      <p class="text-xs text-base-content/50">{$_('profile.dangerZone.resetData.hint')}</p>
      
      {#if resetDataMessage}
        <div class={`alert ${resetDataMessage.type === 'success' ? 'alert-success' : 'alert-error'} text-sm`}>
          <span>{resetDataMessage.text}</span>
        </div>
      {/if}
      
      <button
        class="btn btn-error btn-sm self-start"
        onclick={confirmResetData}
        disabled={resetDataConfirmation.trim() !== $_('profile.dangerZone.resetData.confirmationPhrase')}
      >
        {$_('profile.dangerZone.resetData.button')}
      </button>
    </div>
    
    <!-- Delete Account Section -->
    <div class="border border-error/20 rounded p-4 flex flex-col gap-3">
      <h3 class="font-medium">{$_('profile.dangerZone.deleteAccount.title')}</h3>
      <p class="text-sm text-base-content/70">{$_('profile.dangerZone.deleteAccount.description')}</p>
      <p class="text-xs text-error font-semibold">{$_('profile.dangerZone.deleteAccount.warning')}</p>
      
      <input
        class="input input-bordered max-w-md"
        bind:value={deleteAccountConfirmation}
        placeholder={$_('profile.dangerZone.deleteAccount.placeholder')}
      />
      <p class="text-xs text-base-content/50">{$_('profile.dangerZone.deleteAccount.hint')}</p>
      
      {#if deleteAccountMessage}
        <div class={`alert ${deleteAccountMessage.type === 'success' ? 'alert-success' : 'alert-error'} text-sm`}>
          <span>{deleteAccountMessage.text}</span>
        </div>
      {/if}
      
      <button
        class="btn btn-error btn-sm self-start"
        onclick={confirmDeleteAccount}
        disabled={deleteAccountConfirmation.trim() !== $_('profile.dangerZone.deleteAccount.confirmationPhrase')}
      >
        {$_('profile.dangerZone.deleteAccount.button')}
      </button>
    </div>
  </div>
</div>
```

#### State Variables

```svelte
<script lang="ts">
  let resetDataConfirmation = $state('');
  let resetDataMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);
  let deleteAccountConfirmation = $state('');
  let deleteAccountMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);
  
  async function confirmResetData() {
    resetDataMessage = null;
    try {
      const result = await api.profile.resetData(resetDataConfirmation);
      resetDataMessage = {
        type: 'success',
        text: $_('profile.dangerZone.resetData.success', {
          values: {
            books: result.deleted.books,
            tags: result.deleted.tags,
            entries: result.deleted.progress_entries
          }
        })
      };
      resetDataConfirmation = '';
      // Optionally reload book list or redirect to dashboard
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 2000);
    } catch (e: unknown) {
      resetDataMessage = {
        type: 'error',
        text: e instanceof Error ? e.message : $_('profile.dangerZone.resetData.failed')
      };
    }
  }
  
  async function confirmDeleteAccount() {
    deleteAccountMessage = null;
    try {
      await api.profile.deleteAccount(deleteAccountConfirmation);
      // Account deleted, session cleared by backend
      deleteAccountMessage = {
        type: 'success',
        text: $_('profile.dangerZone.deleteAccount.success')
      };
      // Redirect to login after short delay
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    } catch (e: unknown) {
      deleteAccountMessage = {
        type: 'error',
        text: e instanceof Error ? e.message : $_('profile.dangerZone.deleteAccount.failed')
      };
    }
  }
</script>
```

#### Section Navigation

Update the sticky nav to include the danger zone section:

```svelte
<li>
  <a
    href="#section-danger-zone"
    class="link link-hover text-sm"
    class:text-primary={activeSection === 'section-danger-zone'}
    data-section="section-danger-zone"
  >{$_('profile.dangerZone.title')}</a>
</li>
```

---

### 2.6 Frontend: `frontend/src/lib/i18n/locales/en.json`

**Purpose**: Add English i18n keys.

**New keys**:

```json
{
  "profile": {
    "dangerZone": {
      "title": "Danger Zone",
      "subtitle": "Irreversible actions that permanently delete your data or account.",
      "resetData": {
        "title": "Reset All Personal Data",
        "description": "Permanently delete all your books, tags, and reading progress. Your account, profile, settings, API keys, and OIDC link will be preserved.",
        "warning": "⚠️ This action cannot be undone. All your reading data will be lost.",
        "placeholder": "Type confirmation phrase",
        "hint": "Type exactly: DELETE ALL MY DATA",
        "confirmationPhrase": "DELETE ALL MY DATA",
        "button": "Reset All Data",
        "success": "Data reset complete. Deleted {books} books, {tags} tags, and {entries} progress entries.",
        "failed": "Failed to reset data"
      },
      "deleteAccount": {
        "title": "Delete Account",
        "description": "Permanently delete your entire account including all data, settings, API keys, OIDC link, and profile information.",
        "warning": "⚠️ THIS IS PERMANENT. Your account and all data will be completely removed.",
        "placeholder": "Type confirmation phrase",
        "hint": "Type exactly: DELETE MY ACCOUNT",
        "confirmationPhrase": "DELETE MY ACCOUNT",
        "button": "Delete My Account",
        "success": "Account deleted. Redirecting to login...",
        "failed": "Failed to delete account",
        "lastAdminError": "Cannot delete account: you are the last administrator"
      }
    }
  }
}
```

---

### 2.7 Frontend: `frontend/src/lib/i18n/locales/de.json`

**Purpose**: Add German i18n keys.

**New keys**:

```json
{
  "profile": {
    "dangerZone": {
      "title": "Gefahrenbereich",
      "subtitle": "Unumkehrbare Aktionen, die Ihre Daten oder Ihr Konto dauerhaft löschen.",
      "resetData": {
        "title": "Alle persönlichen Daten zurücksetzen",
        "description": "Löschen Sie dauerhaft alle Ihre Bücher, Tags und Lesefortschritte. Ihr Konto, Profil, Einstellungen, API-Schlüssel und OIDC-Verknüpfung bleiben erhalten.",
        "warning": "⚠️ Diese Aktion kann nicht rückgängig gemacht werden. Alle Ihre Lesedaten gehen verloren.",
        "placeholder": "Bestätigungsphrase eingeben",
        "hint": "Geben Sie genau ein: DELETE ALL MY DATA",
        "confirmationPhrase": "DELETE ALL MY DATA",
        "button": "Alle Daten zurücksetzen",
        "success": "Daten zurückgesetzt. {books} Bücher, {tags} Tags und {entries} Fortschrittseinträge gelöscht.",
        "failed": "Fehler beim Zurücksetzen der Daten"
      },
      "deleteAccount": {
        "title": "Konto löschen",
        "description": "Löschen Sie dauerhaft Ihr gesamtes Konto einschließlich aller Daten, Einstellungen, API-Schlüssel, OIDC-Verknüpfung und Profilinformationen.",
        "warning": "⚠️ DIES IST DAUERHAFT. Ihr Konto und alle Daten werden vollständig entfernt.",
        "placeholder": "Bestätigungsphrase eingeben",
        "hint": "Geben Sie genau ein: DELETE MY ACCOUNT",
        "confirmationPhrase": "DELETE MY ACCOUNT",
        "button": "Mein Konto löschen",
        "success": "Konto gelöscht. Weiterleitung zur Anmeldung...",
        "failed": "Fehler beim Löschen des Kontos",
        "lastAdminError": "Konto kann nicht gelöscht werden: Sie sind der letzte Administrator"
      }
    }
  }
}
```

---

## 3. Data Deletion/Reset Scope

### 3.1 Reset Data (`POST /api/profile/reset-data`)

**Deleted**:
- All `Book` rows where `user_id = current_user.id`
- All `BookTag` links for books owned by the user
- All `Tag` rows where `user_id = current_user.id`
- All `ReadingProgress` rows where `user_id = current_user.id`
- Orphaned cover image files on disk (reuse existing cleanup logic)

**Preserved**:
- User account (`User` row)
- Profile information (firstname, lastname, email, role)
- User settings (`UserSettings`: language, timezone)
- API keys (`ApiKey` rows remain, not revoked)
- OIDC link (`OidcLink` remains active)

**Rationale**: User wants to start fresh with their reading library but keep their account and access credentials intact.

---

### 3.2 Delete Account (`DELETE /api/profile/account`)

**Deleted**:
- All reading data (via reset-data logic)
- All API keys (revoked via `revoked_at = now()`)
- OIDC link (`OidcLink` row deleted)
- User settings (`UserSettings` row deleted)
- User account (`User` row deleted)

**Preserved**:
- Nothing. The user is completely removed from the system.

**Rationale**: User wants to completely remove their presence from the application.

---

## 4. Transaction and Integrity Strategy

### 4.1 Reset Data Transaction Order

1. Start transaction
2. Count books, tags, progress entries (for response stats)
3. Delete `BookTag` links for user's books
4. Delete `ReadingProgress` entries for user
5. Delete `Tag` entries for user
6. For each book:
   - Check if cover is shared with other books
   - If not shared, delete cover file from disk
   - Delete book row
7. Commit transaction
8. Return success with counts

**Rollback**: If any step fails, entire transaction is rolled back. No partial data deletion occurs.

**Cover cleanup**: Performed within transaction by checking `Book.cover_url` references before deleting files. If a cover is referenced by other users' books, it is not deleted.

---

### 4.2 Delete Account Transaction Order

1. Start transaction
2. Check last-admin constraint (fail fast if violated)
3. Call reset-data logic (delete all reading data)
4. Revoke all API keys (`UPDATE ApiKey SET revoked_at = now() WHERE user_id = ?`)
5. Delete OIDC link (`DELETE FROM oidclink WHERE user_id = ?`)
6. Delete user settings (`DELETE FROM usersettings WHERE user_id = ?`)
7. Delete user row (`DELETE FROM user WHERE id = ?`)
8. Commit transaction
9. Clear browser session
10. Return 204 No Content

**Rollback**: If any step fails, entire transaction is rolled back. User and all data remain intact.

**Foreign key integrity**: All deletions respect foreign key constraints. The deletion order ensures child rows are removed before parent rows.

---

## 5. Security Considerations

### 5.1 Authentication and Authorization

- Both endpoints require authentication via `require_user()`
- Users can only delete their own data (enforced by `current_user.id` filters)
- Admin users are NOT exempt from the last-admin check during self-deletion
- No special permissions needed (any authenticated user can delete their own data/account)

---

### 5.2 Confirmation Phrase

- **Exact match required**: Case-sensitive, no trimming beyond `.strip()`
- Phrases are in English for both locales (simplifies validation)
- Frontend provides placeholder and hint to guide user
- Button is disabled until exact phrase is entered (UX safeguard)
- Backend validates phrase before executing any deletion logic

**Reset data phrase**: `"DELETE ALL MY DATA"`
**Delete account phrase**: `"DELETE MY ACCOUNT"`

---

### 5.3 Last Admin Protection

**Logic**:
```python
if current_user.role == UserRole.admin:
    admin_count = session.exec(
        select(func.count()).select_from(User).where(User.role == UserRole.admin)
    ).one()
    if admin_count <= 1:
        raise HTTPException(status_code=403, detail="Cannot delete account: you are the last administrator")
```

**Alignment with existing admin protection**:
- Reuses same constraint logic as `/api/users/{user_id}` admin delete endpoint
- Prevents "orphaned" system without any admin user
- Error message is clear and actionable

**Edge case**: If user is not admin, no check is performed (regular users can always delete their accounts).

---

### 5.4 Session and API Key Behavior After Self-Delete

**Session-based auth**:
- After successful account deletion, `clear_browser_session(request)` is called
- User is immediately logged out
- Subsequent requests fail with 401 Unauthorized
- Frontend redirects to `/login` after showing success message

**API key-based auth**:
- API keys are revoked before user deletion (`revoked_at = now()`)
- After deletion, the key is invalid (user no longer exists)
- Subsequent requests with the revoked key fail with 401 Unauthorized

**CSRF**: Both endpoints validate CSRF token for session-based requests (inherited from `require_user()`).

---

## 6. UX Details

### 6.1 Danger Zone Section

- **Visual styling**: Red-tinted background (`bg-error/10`), red border (`border-error/30`)
- **Section title**: "Danger Zone" with error color (`text-error`)
- **Placement**: After OIDC section (or at bottom if OIDC disabled)
- **Section nav**: Added to sticky side nav for easy access

---

### 6.2 Confirmation Phrase Input

- **Input field**: Standard bordered input (`input input-bordered`)
- **Placeholder**: Localized hint (e.g., "Type confirmation phrase")
- **Helper text**: Shows exact phrase to type (e.g., "Type exactly: DELETE ALL MY DATA")
- **Button disabled state**: Button is disabled (visual cue: greyed out) until exact phrase is entered
- **Live validation**: Button enabled/disabled reactively via Svelte `$state` and `disabled` attribute

---

### 6.3 Feedback and Validation

**Success messages**:
- Reset data: Shows count of deleted items, then redirects to dashboard after 2 seconds
- Delete account: Shows "Account deleted. Redirecting to login...", then redirects to `/login` after 2 seconds

**Error messages**:
- Backend errors (e.g., "Confirmation phrase does not match", "Cannot delete account: you are the last administrator") are displayed in an alert box
- Frontend catches and displays errors returned by API
- User can retry after fixing the error (e.g., re-entering correct confirmation phrase)

**Toast notification**: Optional (can be added if toast system exists in project)

---

### 6.4 Post-Action Behavior

**Reset data**:
- Success message displayed
- After 2 seconds, redirect to `/dashboard` (now empty)
- User remains logged in
- Settings, API keys, OIDC link remain intact

**Delete account**:
- Success message displayed
- After 2 seconds, redirect to `/login`
- Session cleared by backend
- User must create a new account or log in with a different account

---

## 7. Test Plan

### 7.1 Backend Unit Tests

**File**: `backend/tests/test_profile.py` (create if doesn't exist, or add to existing test file)

#### Test: Reset Data Success
```python
def test_reset_data_success(client, db_session, admin_user):
    # Setup: Create books, tags, progress for admin_user
    # Action: POST /api/profile/reset-data with correct confirmation
    # Assert: 200 OK, deleted counts match, user still exists, settings intact
```

#### Test: Reset Data Wrong Confirmation
```python
def test_reset_data_wrong_confirmation(client, admin_user):
    # Action: POST /api/profile/reset-data with wrong phrase
    # Assert: 400 Bad Request, data not deleted
```

#### Test: Delete Account Success (Regular User)
```python
def test_delete_account_success(client, db_session, regular_user):
    # Action: DELETE /api/profile/account with correct confirmation
    # Assert: 204 No Content, user row deleted, session cleared
```

#### Test: Delete Account Last Admin
```python
def test_delete_account_last_admin(client, db_session, admin_user):
    # Setup: Ensure admin_user is the only admin
    # Action: DELETE /api/profile/account with correct confirmation
    # Assert: 403 Forbidden, user still exists
```

#### Test: Delete Account Second Admin Success
```python
def test_delete_account_second_admin(client, db_session, admin_user, admin_user_2):
    # Setup: Two admins exist
    # Action: DELETE /api/profile/account (admin_user) with correct confirmation
    # Assert: 204 No Content, admin_user deleted, admin_user_2 remains
```

#### Test: Delete Account Wrong Confirmation
```python
def test_delete_account_wrong_confirmation(client, admin_user):
    # Action: DELETE /api/profile/account with wrong phrase
    # Assert: 400 Bad Request, user not deleted
```

---

### 7.2 Backend Integration Tests

**File**: `backend/tests/test_danger_zone_integration.py`

#### Test: Reset Data Cascade
```python
def test_reset_data_deletes_all_related_data(client, db_session, admin_user):
    # Setup: Create books, tags, book_tag links, progress entries, covers
    # Action: POST /api/profile/reset-data
    # Assert: All related data deleted, covers cleaned up if orphaned
```

#### Test: Delete Account Cascade
```python
def test_delete_account_deletes_all_related_data(client, db_session, regular_user):
    # Setup: Create books, tags, API keys, OIDC link, settings
    # Action: DELETE /api/profile/account
    # Assert: All data deleted, API keys revoked, user row removed
```

#### Test: Delete Account Cover Cleanup
```python
def test_delete_account_preserves_shared_covers(client, db_session, user1, user2):
    # Setup: user1 and user2 share a cover
    # Action: DELETE /api/profile/account (user1)
    # Assert: user2's book still references cover, cover file not deleted
```

---

### 7.3 Frontend Component Tests

**Manual or automated** (e.g., Playwright or Vitest component tests):

#### Test: Confirmation Phrase Button Disabled
- Navigate to profile page, scroll to danger zone
- Verify reset data button is disabled when input is empty
- Type incorrect phrase, verify button still disabled
- Type correct phrase, verify button becomes enabled

#### Test: Reset Data Success Flow
- Type correct phrase, click "Reset All Data"
- Verify success message displays with counts
- Verify redirect to dashboard after 2 seconds

#### Test: Delete Account Success Flow
- Type correct phrase, click "Delete My Account"
- Verify success message displays
- Verify redirect to login after 2 seconds

#### Test: Delete Account Last Admin Error
- As last admin, type correct phrase, click delete
- Verify error message displays: "Cannot delete account: you are the last administrator"
- Verify no redirect, user still logged in

---

### 7.4 End-to-End Smoke Tests

**Tool**: Manual or Playwright E2E tests

#### Scenario 1: Regular User Resets Data
1. Create test user with 10 books, 5 tags, 20 progress entries
2. Log in, navigate to profile
3. Scroll to danger zone, enter reset confirmation phrase
4. Click "Reset All Data"
5. Verify success message shows correct counts
6. Verify redirect to dashboard
7. Verify dashboard shows 0 books
8. Verify user profile, settings, API keys still accessible

#### Scenario 2: Regular User Deletes Account
1. Create test user with data
2. Log in, navigate to profile
3. Scroll to danger zone, enter delete confirmation phrase
4. Click "Delete My Account"
5. Verify success message
6. Verify redirect to login
7. Attempt to log in with deleted account credentials
8. Verify login fails (account no longer exists)

#### Scenario 3: Last Admin Blocked from Deleting Account
1. Create single admin user
2. Log in as admin, navigate to profile
3. Scroll to danger zone, enter delete confirmation phrase
4. Click "Delete My Account"
5. Verify error message: "Cannot delete account: you are the last administrator"
6. Verify admin still logged in, account intact

#### Scenario 4: Second Admin Can Delete Account
1. Create two admin users
2. Log in as admin1, navigate to profile
3. Scroll to danger zone, enter delete confirmation phrase
4. Click "Delete My Account"
5. Verify success, redirect to login
6. Log in as admin2, verify admin2 still exists and can access admin panel

---

## 8. Step-by-Step Execution Order

### Phase 1: Backend Implementation

1. **Add schemas** (`backend/app/schemas.py`):
   - Add `ConfirmationPhrase` schema
   - Add `DataResetResponse` schema

2. **Implement reset-data endpoint** (`backend/app/routers/profile.py`):
   - Add `POST /api/profile/reset-data` handler
   - Validate confirmation phrase
   - Delete books, tags, book_tag links, progress entries
   - Clean up orphaned covers
   - Return success with counts

3. **Implement delete-account endpoint** (`backend/app/routers/profile.py`):
   - Add `DELETE /api/profile/account` handler
   - Validate confirmation phrase
   - Check last-admin constraint
   - Reuse reset-data logic for reading data deletion
   - Revoke API keys
   - Delete OIDC link, settings, user row
   - Clear session
   - Return 204 No Content

4. **Write backend tests** (`backend/tests/test_profile.py`, `backend/tests/test_danger_zone_integration.py`):
   - Write unit tests for both endpoints
   - Write integration tests for cascade deletions
   - Test last-admin protection
   - Test confirmation phrase validation

5. **Run backend tests**:
   ```bash
   cd backend
   pytest tests/test_profile.py tests/test_danger_zone_integration.py -v
   ```

---

### Phase 2: Frontend Implementation

6. **Add i18n keys**:
   - Update `frontend/src/lib/i18n/locales/en.json`
   - Update `frontend/src/lib/i18n/locales/de.json`

7. **Add API client methods** (`frontend/src/lib/api.ts`):
   - Add `api.profile.resetData()`
   - Add `api.profile.deleteAccount()`

8. **Update types** (`frontend/src/lib/types.ts`):
   - Add `DataResetResponse` type (if needed)

9. **Add Danger Zone UI** (`frontend/src/routes/profile/+page.svelte`):
   - Add state variables for confirmation inputs and messages
   - Add `confirmResetData()` handler
   - Add `confirmDeleteAccount()` handler
   - Add Danger Zone section HTML (reset data + delete account cards)
   - Update section nav to include danger zone link

10. **Test frontend manually**:
    - Start dev server: `cd frontend && npm run dev`
    - Log in as regular user, navigate to profile
    - Verify danger zone section renders
    - Test confirmation phrase input and button disabled state
    - Test reset data flow
    - Test delete account flow
    - Test last-admin error (log in as last admin)

---

### Phase 3: Integration Testing

11. **Run full stack locally**:
    ```bash
    # Terminal 1: Backend
    cd backend && uvicorn app.main:app --reload
    
    # Terminal 2: Frontend
    cd frontend && npm run dev
    ```

12. **Execute E2E smoke tests** (manually or via Playwright):
    - Test all 4 scenarios from section 7.4
    - Verify data persistence and deletion in database
    - Verify session behavior and redirects

---

### Phase 4: Code Review and Deployment

13. **Code review**:
    - Review backend logic (transaction safety, last-admin check, confirmation validation)
    - Review frontend UX (confirmation phrase clarity, disabled states, error handling)
    - Review i18n completeness (EN and DE)

14. **Deploy**:
    - Merge to main branch
    - Deploy backend and frontend
    - Monitor logs for errors
    - Test in production with test accounts

---

## 9. Assumptions and Open Questions

### Assumptions

1. **Confirmation phrases are in English only**: To simplify validation, phrases are not localized. Users in all locales must type the English phrase. This is a common pattern for destructive actions (e.g., GitHub uses English phrases).

2. **No soft delete**: Users and data are permanently deleted from the database. There is no "soft delete" or recovery mechanism. This matches the requirement for "completely remove" functionality.

3. **Cover cleanup logic exists**: The plan assumes the existing `delete_book` logic includes cover cleanup. If not, cover cleanup must be implemented or skipped for reset-data.

4. **Single-admin scenario is rare but critical**: The last-admin check is essential to prevent system lockout. The plan assumes this is an edge case but must be handled correctly.

5. **Session invalidation is sufficient**: After account deletion, clearing the session is enough to log the user out. No additional token revocation or cache clearing is needed (since session state is server-side).

6. **API key revocation is logged**: Revoking API keys via `revoked_at` preserves the audit trail. Keys are not hard-deleted from the database.

7. **Redirect timing (2 seconds) is acceptable**: A 2-second delay after success messages provides enough time for users to read feedback before redirect. This can be adjusted if too fast/slow.

---

### Open Questions

1. **Should reset-data also revoke API keys?**
   - Current plan: API keys are preserved during reset-data.
   - Alternative: Revoke API keys since they grant access to user data (which is now empty).
   - **Recommendation**: Preserve API keys. User may want to keep API access even after resetting reading data.

2. **Should there be a "Download my data" option before deletion?**
   - Current plan: No data export feature.
   - Alternative: Add a "Download my data" button that exports books/tags/progress as JSON before deletion.
   - **Recommendation**: Out of scope for this feature. Can be added in a future plan if requested.

3. **Should admins be able to delete other users' data from the admin panel?**
   - Current plan: Only self-service deletion via profile page.
   - Alternative: Extend admin user management to include "Reset user data" and "Delete user" actions.
   - **Recommendation**: Out of scope. Admin deletion already exists (`DELETE /api/users/{user_id}`). This plan focuses on self-service profile actions.

4. **Should there be a "grace period" or "undo" option after deletion?**
   - Current plan: Deletion is immediate and irreversible.
   - Alternative: Mark account as "pending deletion" for 7 days, allow user to cancel.
   - **Recommendation**: Out of scope. Requirement specifies "completely remove," implying immediate deletion. Grace period can be added later if requested.

5. **Should OIDC unlink happen automatically during reset-data?**
   - Current plan: OIDC link is preserved during reset-data, deleted during account deletion.
   - Alternative: Also unlink OIDC during reset-data.
   - **Recommendation**: Preserve OIDC link during reset-data. User may want to keep SSO login even after resetting reading data.

---

## 10. Summary

This plan implements a comprehensive "Danger Zone" feature in the profile page with two destructive actions:

1. **Reset All Personal Data**: Deletes books, tags, and progress while preserving account and settings.
2. **Delete Account**: Completely removes user and all associated data.

Both actions are protected by exact confirmation phrase validation. Account deletion is blocked if the user is the last admin. The implementation includes:

- Backend endpoints with transactional safety
- Frontend UI with confirmation inputs and disabled buttons
- i18n support (EN and DE)
- Comprehensive test coverage (unit, integration, E2E)
- Clear error messages and success feedback

The feature aligns with existing patterns in the codebase (e.g., admin user deletion, book deletion cascade) and provides a safe, user-friendly way to manage destructive actions.

---

**Suggested filename**: `.plan/47-profile-danger-zone.md`
