# Task Management API

A backend for a **task tracking and management** application with team
collaboration — users, teams/projects, tasks (CRUD + filtering/sorting/search),
task assignment, comments, file attachments, real-time notifications, and an
optional AI-assisted task-description generator.

Built with **Node.js + Express**. Storage is **SQLite** via Node's built-in
`node:sqlite` (no native build step, no database server to install). Auth is
**JWT** with **bcrypt** password hashing and real, revocable logout.

---

## Features → assignment mapping

| Requirement | Where |
|---|---|
| Secure auth (bcrypt), registration, login, JWT | `controllers/auth.controller.js`, `utils/password.js`, `utils/jwt.js` |
| Profile view / update | `controllers/user.controller.js` |
| Secure logout (JWT revocation via `jti` denylist) | `utils/jwt.js`, `middleware/auth.js` |
| Task data model (title, description, due date, status, priority) | `db/schema.sql` |
| Task CRUD | `controllers/task.controller.js` |
| Filtering, sorting, searching | `GET /api/tasks` query params |
| Teams/projects: create, join, invite | `controllers/team.controller.js` |
| Task assignment within teams | `POST /api/tasks/:id/assign` |
| Comments | `controllers/comment.controller.js` |
| Attachments (file upload/download) | `controllers/attachment.controller.js` (multer) |
| Validation & error handling | `middleware/validate.js`, `middleware/error.js` |
| **(Optional)** Real-time notifications | Server-Sent Events — `utils/sse.js`, `GET /api/notifications/stream` |
| **(Optional)** Generative AI task descriptions | `utils/ai.js` (Claude + offline template fallback) |

---

## Quick start

```bash
cd DB-and-System-Design/Assignment-1-Task-Management-API
npm install
cp .env.example .env        # optional — defaults work out of the box
npm start                   # http://localhost:3000

# health check
curl localhost:3000/api/health

# run the test suite (in-memory DB, 18 tests)
npm test
```

> Requires **Node ≥ 22.5** (for the built-in `node:sqlite` module). The
> experimental-module warning it prints is harmless; silence it with
> `NODE_NO_WARNINGS=1`.

### Try it end-to-end

```bash
# register (returns a JWT)
TOKEN=$(curl -s localhost:3000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alice","email":"alice@example.com","password":"password123"}' \
  | node -pe 'JSON.parse(require("fs").readFileSync(0)).token')

# create a task
curl -s localhost:3000/api/tasks -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Design schema","description":"ERD","due_date":"2026-09-01","priority":"high"}'

# list my open tasks, searched + sorted
curl -s "localhost:3000/api/tasks?status=open&q=schema&sort=due_date&order=asc" \
  -H "Authorization: Bearer $TOKEN"
```

---

## API reference

Base URL: `/api`. All routes except register/login/health require
`Authorization: Bearer <token>`.

### Auth
| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/register` | `{name,email,password}` | returns `{user, token}` (201) |
| POST | `/auth/login` | `{email,password}` | returns `{user, token}` |
| POST | `/auth/logout` | — | revokes the current token |

### Users
| Method | Path | Notes |
|---|---|---|
| GET | `/users/me` | current profile |
| PATCH | `/users/me` | `{name?, bio?}` |
| GET | `/users?q=` | search users (for assignment/invites) |

### Teams
| Method | Path | Notes |
|---|---|---|
| POST | `/teams` | `{name, description?}` |
| GET | `/teams` | teams I belong to |
| GET | `/teams/:id` | team + members (must be a member) |
| POST | `/teams/:id/members` | `{email}` or `{userId}` (owner only) |
| POST | `/teams/:id/join` | self-join |

### Tasks
| Method | Path | Notes |
|---|---|---|
| POST | `/tasks` | `{title, description?, due_date?, priority?, status?, team_id?, assignee_id?}` — pass `generate_description:true` (with `notes`) for AI text |
| GET | `/tasks` | filters: `status`, `priority`, `team_id`, `assignee=me|<id>`, `q` (search); `sort` (`created_at`/`due_date`/`priority`/`title`), `order` (`asc`/`desc`), `limit`, `offset` |
| GET | `/tasks/:id` | single task |
| PATCH | `/tasks/:id` | update any field incl. `status`, `assignee_id` |
| POST | `/tasks/:id/complete` | mark completed |
| POST | `/tasks/:id/assign` | `{assignee_id}` (must be a team member if the task has a team) |
| DELETE | `/tasks/:id` | creator or team owner only |

### Comments & attachments
| Method | Path | Notes |
|---|---|---|
| GET | `/tasks/:id/comments` | list |
| POST | `/tasks/:id/comments` | `{body}` |
| GET | `/tasks/:id/attachments` | list |
| POST | `/tasks/:id/attachments` | multipart form, field `file` |
| GET | `/attachments/:attId/download` | stream the file |

### Notifications (optional, real-time)
| Method | Path | Notes |
|---|---|---|
| GET | `/notifications` | recent notifications |
| POST | `/notifications/:id/read` | mark read |
| GET | `/notifications/stream?token=<jwt>` | **SSE** live stream |

### AI (optional)
| Method | Path | Notes |
|---|---|---|
| POST | `/ai/task-description` | `{title, notes?}` → `{description, source}` (`claude` if `ANTHROPIC_API_KEY` set, else `template`) |

---

## Data model

```
users ──< team_members >── teams
  │                          │
  │ creator/assignee         │ team_id
  └─────────< tasks >────────┘
                │
        ┌───────┼─────────┐
     comments  attachments  notifications
```

See [`src/db/schema.sql`](./src/db/schema.sql) for full DDL, constraints, and
indexes (`tasks.assignee_id`, `tasks.team_id`, `tasks.status`).

## Project structure

```
src/
├── server.js            # HTTP entry point
├── app.js               # Express app factory
├── config.js            # env-driven config
├── db/                  # node:sqlite connection + schema.sql
├── middleware/          # auth, validation, central error handling
├── utils/               # password, jwt, sse, notify, ai
├── controllers/         # auth, user, team, task, comment, attachment, misc
└── routes/index.js      # all routes + validation wiring
tests/api.test.js        # 18 integration tests (user stories)
```

## Design notes

- **Security**: passwords hashed with bcrypt (10 rounds); JWTs carry a unique
  `jti` so logout can revoke a specific token via a denylist table — a real
  logout for otherwise-stateless JWTs. Password hashes are never serialized.
- **Authorization**: task visibility is scoped to creator, assignee, or team
  members; team-member add is owner-only; task delete is creator/owner-only.
- **Validation**: a small declarative validator returns field-level 400 errors;
  the central error handler maps unique-constraint → 409, JWT errors → 401,
  oversized uploads → 413.
- **No native dependencies**: SQLite via `node:sqlite` means `npm install` never
  compiles C — it just works.

## Tests

`npm test` runs 18 `node:test` integration cases against an in-memory database,
covering every user story: registration, duplicate/validation rejection, login,
auth enforcement, profile update, team create/invite/authorization, task
create/assign/complete, filter/search, comments, access control, the AI
endpoint, and logout revocation.

---

## Deliverables checklist
- [x] Node.js + Express backend with a database (SQLite)
- [x] Secure auth (bcrypt + JWT), register/login/logout/profile
- [x] Task model + CRUD + filter/sort/search
- [x] Teams/projects, assignment, comments, attachments
- [x] RESTful endpoints with validation & error handling
- [x] Clear README
- [x] Optional: real-time notifications (SSE) + generative-AI descriptions
- [x] 18 passing integration tests
- [ ] Demo video
