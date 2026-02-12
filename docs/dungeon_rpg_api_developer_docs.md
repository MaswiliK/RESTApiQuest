# Dungeon Crawl RPG — Developer API Documentation

**Purpose:**
This document is a developer-focused, Swagger-style yet human-readable API reference for the Dungeon Crawl RPG Flask server. It lets another developer run the server locally, interact with endpoints, and understand request/response formats without asking you anything.

---

## Quick start (run locally)

Requirements:
- Python 3.10+ (or your env)
- Flask installed: `pip install flask`

Run:
```bash
python dungeon_rpg_api.py
```
The server listens on `http://127.0.0.1:5000` by default.

---

# Authentication / State

No auth tokens. The API is **stateful by player** using `player_id` (UUID) as the save slot. All stateful endpoints require `player_id` in the request body or query string.

Treat `player_id` like an account/session token — keep it private.

---

# Global Notes
- Dungeon coordinates are `x` and `y` with `0 <= x,y < dungeon_size`.
- `player.dungeon.grid[y][x]` represents the room at (x,y).
- `visited` is a boolean grid of explored rooms.
- `in_battle` and `monster` fields represent an active combat state.

---

# Endpoints (summary)

| Method | Path | Purpose |
|---|---|---|
| POST | `/start_game` | Create a new player (returns `player_id`) |
| POST | `/move` | Move N/S/E/W — returns event & available moves |
| POST | `/fight` | Fight current monster (`attack`, `run`) |
| POST | `/use_item` | Use an inventory item (e.g., `healing_potion`) |
| POST | `/equip` | Equip an item (e.g., `rusty_sword`) |
| POST | `/respawn` | Respawn after death (penalty applied) |
| GET  | `/status` | Get player status (health, inventory, position) |
| GET  | `/map` | ASCII-style visited map (P = player) |
| GET  | `/leaderboard` | Top players by level/exp |
| GET  | `/_debug/players` | Dev: list players in DB |

---

## POST /start_game

**Description:** Create a new player and generate a random dungeon. Returns `player_id` (UUID).

**Request body (JSON):**
```json
{
  "name": "MK",        // optional
  "dungeon_size": 5          // optional (default 4-6 if omitted)
}
```

**Success response (201):**
```json
{
  "ok": true,
  "player": {
    "player_id": "66a3f5cb-6b70-4580-8f07-a27ce9f06a97",
    "name": "MK",
    "level": 1,
    "health": 20,
    "position": {"x": 0, "y": 0},
    "dungeon_size": 5
  }
}
```

Errors: 400 for invalid input.

---

## POST /move

**Description:** Move the player one cell in the requested direction. Triggers random events: monster, treasure, trap, or ambience. Returns `available_moves` so clients can know possible directions.

**Request body (JSON):**
```json
{
  "player_id": "<uuid>",
  "direction": "north"  // north | south | east | west
}
```

**Success response (200):**
- On successful move into a normal room:
```json
{
  "ok": true,
  "moved": true,
  "event": "You hear dripping water...",
  "available_moves": ["north","east","west"]
}
```
- On blocked move (wall):
```json
{
  "ok": true,
  "moved": false,
  "event": "A cold stone wall blocks your path.",
  "available_moves": ["north","west"]
}
```
- On monster spawn (enter battle):
```json
{
  "ok": true,
  "moved": true,
  "event": "A Goblin jumps out!",
  "available_moves": ["east","south"]
}
```

**Notes:** If you move into the boss room `(size-1,size-1)` and your level >= 5, the boss will awaken and `in_battle` will be set.

Errors: 400 for bad direction, 404 for missing player.

---

## POST /fight

**Description:** Resolve combat while `in_battle` is active.

**Request body (JSON):**
```json
{
  "player_id": "<uuid>",
  "action": "attack"   // or "run"
}
```

**Success response examples:**
- Player attack & monster alive:
```json
{ "ok": true, "result": { "player_attack": 5, "monster_attack": 3, "monster_hp": 4, "player_health": 17 } }
```
- Monster defeated:
```json
{ "ok": true, "result": { "monster_defeated": true, "gained_exp": 8, "loot": "rusty_sword" } }
```
- Run success:
```json
{ "ok": true, "result": "escaped", "message": "You escaped the fight." }
```

Errors: 400 if no active battle, 404 if player not found.

---

## POST /use_item

**Description:** Use an inventory item. Currently implemented: `healing_potion`.

**Request body:**
```json
{
  "player_id": "<uuid>",
  "item": "healing_potion"
}
```

**Success response:**
```json
{ "ok": true, "healed": 6, "health": 22 }
```

Errors: 400 if item not found or not usable.

---

## POST /equip

**Description:** Equip an owned item to receive combat bonuses. Example: `rusty_sword` gives +2 damage.

**Request:**
```json
{
  "player_id": "<uuid>",
  "item": "rusty_sword"
}
```

**Success:**
```json
{ "ok": true, "equipped": "rusty_sword" }
```

Errors: 400 if item not owned.

---

## POST /respawn

**Description:** Respawn after death. Applies a small XP penalty and sends the player back to entrance.

**Request:**
```json
{ "player_id": "<uuid>" }
```

**Success:**
```json
{ "ok": true, "message": "Respawned at entrance", "health": 25, "exp": 3 }
```

Errors: 400 if player not dead.

---

## GET /status

**Description:** Fetch current player state.

**Query params:** `?player_id=<uuid>`

**Success response:**
```json
{
  "ok": true,
  "status": {
    "id": "66a3f...",
    "name": "Maswili",
    "level": 2,
    "exp": 2,
    "health": 25,
    "max_health": 25,
    "inventory": [{"rusty_sword": 2}],
    "position": {"x":1,"y":3},
    "dungeon_size": 5,
    "visited": [[true,true,false,...], ...],
    "in_battle": false,
    "monster": null
  }
}
```

---

## GET /map

**Description:** Returns a tiny ASCII map of visited rooms.

**Request:** `GET /map?player_id=<uuid>`

**Response:**
```json
{
  "ok": true,
  "map": "P . # # #\n. . . # #\n# . # # #\n..."
}
```
Legend: `P` = player, `.` = visited, `#` = unexplored

---

## GET /leaderboard

**Description:** Top players by `level` then `exp`.

**Response:**
```json
{ "ok": true, "leaders": [ {"name":"Maswili","level":6,"exp":12}, ... ] }
```

---

## Developer / Debug endpoint

### GET /_debug/players
Lists players (dev-only). Use for testing.

---

# Database (SQLite) schema highlights

```
players (
  id TEXT PRIMARY KEY,
  name TEXT,
  health INTEGER,
  max_health INTEGER,
  level INTEGER,
  exp INTEGER,
  inventory TEXT,       -- JSON
  x INTEGER,
  y INTEGER,
  dungeon TEXT,         -- JSON (grid, size, visited)
  in_battle INTEGER,
  monster TEXT,
  created_at TEXT
)
```

Notes:
- `inventory` and `dungeon` are stored as JSON strings in SQLite.
- `monster` is a small JSON blob used only while `in_battle`.

---

# OpenAPI (Swagger) — minimal example

Below is a compact OpenAPI 3.0 YAML you can paste into a `openapi.yaml` and load in Swagger UI / ReDoc. This is intentionally minimal — adjust later with richer schema refs.

```yaml
openapi: 3.0.0
info:
  title: Dungeon Crawl RPG API
  version: 1.0.0
servers:
  - url: http://127.0.0.1:5000
paths:
  /start_game:
    post:
      summary: Create a new player
      requestBody:
        required: false
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                dungeon_size:
                  type: integer
      responses:
        '201':
          description: player created
  /move:
    post:
      summary: Move player
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                player_id:
                  type: string
                direction:
                  type: string
      responses:
        '200':
          description: movement result
  /status:
    get:
      summary: Player status
      parameters:
        - in: query
          name: player_id
          schema:
            type: string
      responses:
        '200':
          description: player state
```
```

---

# REST (.http) examples

Create a `dungeon.http` file in your repo with REST Client variables and example requests. The repo already contains one. 

Example snippet (REST Client):

```http
@base = http://127.0.0.1:5000

### Fight monster
POST {{base}}/fight
Content-Type: application/json

{
"player_id": "{{player_id}}",
"action": "attack"
}
```
---

# Error handling

Common errors and meanings:
- `400 Bad Request` — missing or invalid parameters (e.g., bad direction)
- `404 Not Found` — invalid `player_id` or player not in DB
- `500 Internal` — unexpected server error (check logs)

Errors are returned as JSON: `{ "ok": false, "error": "message" }`.

---

# Contribution / Extending the API

Suggested PRs:
- Move to SQLAlchemy for clearer schema & migrations
- Add `players` ownership/auth (API tokens)
- New endpoints: `/trade`, `/shop`, `/quests`
- Add unit tests with `pytest` and a `test_db.sqlite` fixture
- Dockerfile + docker-compose for running locally with env vars

---

# License & Attribution

Use this in your projects — MIT-friendly. Credit the original developer ( MaswiliK) 

---

# Appendix: Useful client flows

- **Quick play loop:** `POST /start_game` → `POST /move` → if `in_battle` → `POST /fight` → `GET /status` → `POST /use_item` → repeat.
- **Multiplayer experiment:** Start multiple players and use `/move` to bring them to the same coordinates. Detect collisions by checking DB for players with same `x` and `y` in the same dungeon size.

---


