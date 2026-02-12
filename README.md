# 🐉 Dungeon Crawl RPG (Flask + SQLite)

A stateful, terminal‑style roguelike game served entirely over HTTP.

This project is a small but complete game engine built with **Flask** and **SQLite**. Players explore a dungeon, fight monsters, collect loot, and level up — all by sending API requests. Any HTTP client (VS Code REST Client, curl, Postman, etc.) becomes the game controller.

> Every request is a turn. The server is the world.

---

## ✨ Features

- Persistent characters (save anytime)
- Random dungeon events
- Turn‑based combat system
- Inventory & equipment
- Boss room encounter
- ASCII map exploration
- Leaderboard ranking
- Multiplayer‑ready architecture (multiple players on same server)

---

## 🎮 How the Game Works

You control a character using HTTP requests:

```
start_game → move → encounter → fight → loot → heal → level up → explore deeper
```

The server keeps track of:
- position `(x,y)` in the dungeon
- health & max health
- inventory items
- level & experience
- explored rooms

Your `player_id` is your **save file**.

You can shut down the server, restart it later, and continue exactly where you left off.

---

## 🚀 Quick Start

### 1) Clone repo

```bash
git clone <your-repo-url>
cd dungeon-rpg
```

### 2) Create environment (recommended)

```bash
python -m venv .venv
.venv\\Scripts\\activate   # Windows
# or
source .venv/bin/activate    # Linux/Mac
```

### 3) Install dependencies

```bash
pip install flask
```

### 4) Run server

```bash
python dungeon_rpg_api.py
```

Server runs at:

```
http://127.0.0.1:5000
```

---

## 🕹️ Play the Game (Recommended Method)

Use **VS Code + REST Client extension**.

1. Open `rpg.http`
2. Click **Send Request** above each request
3. Play from top to bottom
4. Copy paste "player_id" from json response into the constant "@player_id"


You are literally playing an RPG through HTTP.

---

## 📡 Core Endpoints

| Method | Endpoint | Description |
|------|------|------|
| POST | `/start_game` | Create a new character |
| POST | `/move` | Move north/south/east/west |
| POST | `/fight` | Attack or run from monster |
| POST | `/use_item` | Use a potion |
| POST | `/equip` | Equip a weapon |
| POST | `/respawn` | Respawn after death |
| GET | `/status` | Player stats & inventory |
| GET | `/map` | Explored dungeon map |
| GET | `/leaderboard` | Top players |

Full documentation available in **Dungeon RPG API — Developer Docs**.

---

## 🗺️ Dungeon System

The dungeon is a coordinate grid:

```
(0,0)  (1,0)  (2,0)  (3,0)  (4,0)
(0,1)  (1,1)  (2,1)  (3,1)  (4,1)
(0,2)  (1,2)  (2,2)  (3,2)  (4,2)
(0,3)  (1,3)  (2,3)  (3,3)  (4,3)
(0,4)  (1,4)  (2,4)  (3,4)  (4,4)
```

Movement is simple math:

```
north → y - 1
south → y + 1
east  → x + 1
west  → x - 1
```

Bounds checking prevents leaving the dungeon.

---

## ⚔️ Combat

When entering certain rooms, monsters spawn.

Combat is turn‑based:

- attack → deal damage
- monster retaliates
- defeat → gain XP & loot
- run → chance to escape

Boss appears at the far corner of the dungeon once you reach a higher level.

---

## 🧪 Example Requests (curl)

Start a character:

```bash
curl -X POST http://127.0.0.1:5000/start_game \
  -H "Content-Type: application/json" \
  -d '{"name":"MK","dungeon_size":5}'
```

Move:

```bash
curl -X POST http://127.0.0.1:5000/move \
  -H "Content-Type: application/json" \
  -d '{"player_id":"<uuid>","direction":"north"}'
```

Check status:

```bash
curl "http://127.0.0.1:5000/status?player_id=<uuid>"
```

---

## 🧠 Architecture

| Component | Role |
|------|------|
| Flask | Game engine / controller |
| SQLite | Persistent world memory |
| HTTP | Player input channel |
| JSON | Game state format |

Each API call updates the player row in SQLite, making the game state persistent.

---

## 📁 Project Structure

```
dungeon-rpg/
│
├── dungeon_rpg_api.py   # main server
├── dungeon.db           # SQLite database (auto created)
├── rpg.http         # playable client
├── README.md
└── docs/
```

---

## 🧩 Future Ideas

- shared multiplayer dungeon
- trading between players
- shops & currency
- quests & NPCs
- Telegram/Discord bot client
- web UI frontend
- WebSocket real‑time combat

---

## 🤝 Contributing

Pull requests are welcome.

Good starter contributions:
- add monsters
- new items
- more dungeon events
- balance combat
- better map rendering

---

## 📜 License

MIT License — free to use, modify, and learn from.

---

## ❤️ Why this project exists

This project demonstrates that backend APIs are not only for business software — they can power games and simulations. It’s a teaching project for learning:

- stateful API design
- persistence
- system architecture
- game mechanics

If you learned something from it, mission accomplished.

