# Tech Specs - 轻语录 (Light Quotes)

## 1. Architecture Overview

Two-container Docker deployment:
- **Backend Container**: Python FastAPI on port 8000
- **Frontend Container**: Nginx serving static HTML/CSS/JS on port 80

No reverse proxy between containers; frontend calls backend via browser-side fetch to `http://localhost:8000`.

## 2. Backend API Specification

### Base URL: `http://localhost:8000/api`

### 2.1 Auth Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/auth/register | No | Register with email + verification code |
| POST | /api/auth/send-code | No | Send verification code to email |
| POST | /api/auth/login | No | Login with email + password |
| POST | /api/auth/logout | Yes | Logout (clear session) |
| GET | /api/auth/me | Yes | Get current user info |

### 2.2 Post Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/posts | Yes | Create a new post (text + optional image) |
| GET | /api/posts/{id} | Yes | Get a single post by ID |
| DELETE | /api/posts/{id} | Yes | Delete own post |

### 2.3 User Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/users/{id} | Yes | Get user profile |
| GET | /api/users/{id}/posts | Yes | Get user's posts (paginated) |
| POST | /api/users/{id}/follow | Yes | Follow a user |
| DELETE | /api/users/{id}/follow | Yes | Unfollow a user |
| GET | /api/users/discover | Yes | Get suggested users to follow |

### 2.4 Timeline Endpoint

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/timeline | Yes | Get followed users' posts (paginated, 20 per page) |

## 3. Database Schema (SQLite)

### Table: users
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| username | TEXT | UNIQUE NOT NULL |
| email | TEXT | UNIQUE NOT NULL |
| password_hash | TEXT | NOT NULL |
| bio | TEXT | DEFAULT '' |
| created_at | TEXT | DEFAULT (datetime('now')) |

### Table: posts
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| author_id | INTEGER | NOT NULL REFERENCES users(id) |
| content | TEXT | NOT NULL, max 280 chars |
| image_path | TEXT | DEFAULT NULL |
| created_at | TEXT | DEFAULT (datetime('now')) |

### Table: follows
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| follower_id | INTEGER | NOT NULL REFERENCES users(id) |
| followed_id | INTEGER | NOT NULL REFERENCES users(id) |
| created_at | TEXT | DEFAULT (datetime('now')) |
| UNIQUE(follower_id, followed_id) |

### Table: verification_codes
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| email | TEXT | NOT NULL |
| code | TEXT | NOT NULL |
| expires_at | TEXT | NOT NULL |
| used | INTEGER | DEFAULT 0 |

## 4. Backend Container Spec

- **Image**: python:3.11-slim
- **Port**: 8000
- **Command**: uvicorn main:app --host 0.0.0.0 --port 8000
- **Healthcheck**: curl -f http://localhost:8000/health || exit 1
- **Volumes**: uploads/ for images, data/ for SQLite DB

## 5. Frontend Container Spec

- **Image**: nginx:alpine
- **Port**: 80
- **Healthcheck**: Not explicitly required, but depends_on backend with condition: service_healthy
- **Serves**: Static HTML/CSS/JS files

## 6. Security Measures

- Passwords hashed with bcrypt
- Verification codes expire after 5 minutes
- Rate limiting: 5 failed login attempts locks IP for 15 minutes (in-memory)
- CSRF protection via session-based tokens
- Image upload validation: only JPEG/PNG, max 5MB

## 7. Performance Targets

- Timeline query < 200ms (with SQLite indexing on created_at and author_id)
- Support ≤ 1000 CCU
- No pagination beyond simple OFFSET/LIMIT

## 8. File Upload Config

- Storage: local filesystem under `/app/uploads/`
- Allowed formats: image/jpeg, image/png
- Max file size: 5MB
- Single file per post only

## 9. Banned Features (Not Implemented)

No video upload, no multi-image, no cloud storage, no likes, no comments, no shares, no friendship, no DMs, no notifications, no recommendation algorithm, no OAuth, no password reset.
