# Code Review Report — LightQuotes (轻语录) MVP

**Reviewer**: Principal Software Architect & Security Auditor  
**Review Type**: Scope Compliance & Red-Team Audit (Round 1)  
**Date**: 2025-01-01

---

## 1. Scope Alignment Audit

### 🚫 Media Processing Restrictions

| Feature | Status | Evidence |
|---------|--------|----------|
| Video upload/playback/transcoding | ✅ CLEAN | No video-related endpoints (`UploadVideo`, `VideoFile`), no video tables, no video UI elements. Image-only upload (`accept="image/jpeg,image/png"` in frontend, `ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}` in backend). |
| Multi-image upload (>1 image) | ✅ CLEAN | `create_post` accepts a single `image: UploadFile = File(None)` parameter. No multi-image arrays or fields. Database schema has a single `image_path` column (nullable). |
| Image cropping/filters/editing | ✅ CLEAN | Image is saved as-is. `from PIL import Image` is imported but never invoked for any editing/cropping/filter operation — it is dead code, not a functional feature. No `ImageEditor`, `ImageCropper`, `FileCompressor` implementations. |
| Cloud storage (OSS/S3/CDN) | ✅ CLEAN | All uploads saved to local filesystem path `/app/uploads/`. No `OSS`, `S3`, `CDN` imports, configs, or SDK calls. |

### 🚫 Social Interaction Restrictions

| Feature | Status | Evidence |
|---------|--------|----------|
| Likes (Like/LikeButton) | ✅ CLEAN | No `likes` database table, no `/api/like` endpoint, no like button or like counter in HTML/CSS/JS. The word "like" does not appear as a functional feature anywhere in the codebase. |
| Comments | ✅ CLEAN | No `comments` database table, no `/api/comment` endpoint, no comment input UI. |
| Shares | ✅ CLEAN | No share endpoint, no share button, no share tracking. |
| Friendship / Mutual Follow | ✅ CLEAN | Only one-way `Follow` model (follower_id → followed_id). No bidirectional acceptance logic, no `friends` table, no `MutualFollow` implementation. |
| DM / Chat / Message | ✅ CLEAN | No WebSocket connections, no `/api/message` or `/api/chat` endpoints, no messaging UI components. No `Notification` system. |

### 🚫 Recommendation Algorithm Restrictions

| Feature | Status | Evidence |
|---------|--------|----------|
| ML recommendation models | ✅ CLEAN | No `RecommendationModel`, `MLRecommender`, `CollaborativeFiltering` code. No user behavior tracking for model training. |
| Personalized ranking / trending | ✅ CLEAN | Timeline uses exact SQL: `Post.author_id.in_(followed_ids).order_by(desc(Post.created_at))` — pure chronological sort. Discover users sorted by `desc(User.created_at)` — simple registration date sort. No `UserScore`, `PersonalizedRanking`, `TrendingAlgorithm`. |
| User behavior tracking | ✅ CLEAN | No browsing time, click rate, or engagement metrics collected or stored. |

### 🚫 User & Registration Restrictions

| Feature | Status | Evidence |
|---------|--------|----------|
| Verification-free registration | ✅ CLEAN | Registration requires `code` field verified against `VerificationCode` table with expiry check. Email verification code is mandatory. |
| OAuth / Social Login | ✅ CLEAN | No `OAuthLogin`, `SocialLogin` endpoints or libraries (no `authlib`, `google-auth`, `python-social-auth` in requirements). Registration is email+code+password only. |
| Password reset | ✅ CLEAN | No `/api/auth/reset-password` endpoint, no `PasswordReset` functionality anywhere. |

### 📋 In-Scope Feature Verification

| ID | Feature | Implemented? | Location |
|----|---------|-------------|----------|
| FR-01 | Registration with email verification code | ✅ YES | `POST /api/auth/register`, `POST /api/auth/send-code`, `VerificationCode` model |
| FR-02 | Login/Logout with session cookies | ✅ YES | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| FR-03 | Publish text posts (max 280 chars) | ✅ YES | `POST /api/posts` with `max_length=280`, character counter in UI |
| FR-04 | Upload single image (JPEG/PNG, ≤5MB) | ✅ YES | Single `UploadFile`, validation, local filesystem storage |
| FR-05 | One-way follow users | ✅ YES | `POST /api/users/{id}/follow`, `Follow` model |
| FR-06 | Unfollow users | ✅ YES | `DELETE /api/users/{id}/follow` |
| FR-07 | Chronological timeline (followed users' posts) | ✅ YES | `GET /api/timeline` with `ORDER BY created_at DESC`, 20 per page |
| FR-08 | User discovery (non-algorithmic) | ✅ YES | `GET /api/users/discover` sorted by registration date |
| FR-09 | User profile page | ✅ YES | `GET /api/users/{id}`, `GET /api/users/{id}/posts` |

---

## 2. Actionable Feedback

**No violations detected.** The codebase is fully compliant with all scope boundaries defined in `boundary_manifest.md` and all functional requirements in `requirements.md`.

**Minor observation (non-blocking):**  
- `from PIL import Image` is imported in both `backend/main.py` and `backend/routes/posts.py` but never used for any image manipulation. This is dead code. While not a scope violation, it is recommended to remove these unused imports to keep the codebase clean.

---

Review Verdict: APPROVED
