# [TECH_CONTRACT] SYSTEM ARCHITECTURE & TECHNICAL SPECIFICATIONS
## 1. System Context & Overview
(A high-level description mapping PRD features to technical components.)

## 2. Component Architecture (MANDATORY TWO-CONTAINER STRATEGY)
- **Container: backend**:
  - Role: API & Business Logic
  - Port: 8000 (Internal)
  - Runtime: (Agent's choice: e.g. Python, Node.js)
- **Container: frontend**:
  - Role: Static Asset Web Server (Nginx)
  - Port: 80 (Internal) -> 8080 (Host)
  - Assets: Vanilla HTML/CSS/JS

## 3. API Contract & Endpoints
| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| GET | /health | System health check (MANDATORY 200 OK) | No |
| POST | /api/... | ... | ... |

## 4. Data Model Schema
(Describe the database schema. e.g., Table Name, Columns, Types, Keys. MUST align with PRD restrictions.)

## 5. Technology Stack Validation
- **Frontend**: Vanilla HTML5/CSS3/JS (ES6) + Nginx
- **Backend**: (Language & Framework)
- **Data Store**: (DB Engine, e.g. SQLite)

## 6. Docker & Orchestration Blueprint (STRICT ENFORCEMENT)
### Dockerfile Requirements
- **Backend**: You MUST install `curl` in the Dockerfile (e.g. `apt-get install -y curl`) for healthchecks.
- **Frontend**: Use a lightweight Nginx image.

### docker-compose.yml Guardrails
MANDATORY PATTERN (DO NOT SIMPLIFY):
```yaml
services:
  backend:
    build: 
      context: .
      dockerfile: backend.Dockerfile # or multi-stage
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s
  frontend:
    build: 
      context: ./frontend
      dockerfile: frontend.Dockerfile
    ports:
      - "8080:80"
    depends_on:
      backend:
        condition: service_healthy
```

## 7. Security & Integration
- **CORS**: Backend MUST allow requests from frontend (if ports differ) or use Nginx proxy.
- **API Base URL**: Frontend JS MUST use relative paths `/api/...` or configured base.
