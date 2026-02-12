"""
Dungeon Crawl RPG - Flask + SQLite
Single-file Flask API that saves player progress and stats in SQLite.

Endpoints:
- POST /start_game    -> create new player
- POST /move          -> move north/south/east/west (triggers events)
- POST /fight         -> fight current monster (attack / run)
- GET  /status        -> get player status

Run: python dungeon_rpg_api.py
Requires: Flask (pip install flask)

This is a demo-level implementation intended for local testing and extension.
"""

from flask import Flask, request, jsonify, g
import sqlite3
import uuid
import json
import random
from datetime import datetime

DB_PATH = 'dungeon.db'

app = Flask(__name__)

# ---------------------- Database helpers ----------------------

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            name TEXT,
            health INTEGER,
            max_health INTEGER,
            level INTEGER,
            exp INTEGER,
            inventory TEXT,
            x INTEGER,
            y INTEGER,
            dungeon TEXT,
            in_battle INTEGER DEFAULT 0,
            monster TEXT,
            created_at TEXT
        )
    ''')
    db.commit()


# ---------------------- Game logic ----------------------

ROOM_TYPES = ['empty', 'monster', 'treasure', 'trap']
MONSTER_BASE = [
    {"name": "Goblin", "hp": 6, "atk": 2, "exp": 5},
    {"name": "Skeleton", "hp": 8, "atk": 3, "exp": 8},
    {"name": "Orc", "hp": 12, "atk": 4, "exp": 14},
]
TREASURE_ITEMS = ["gold_coin", "healing_potion", "rusty_sword", "gem"]


def generate_dungeon(size=5):
    # Create a size x size dungeon where each cell has a room type and seed
    grid = []
    for y in range(size):
        row = []
        for x in range(size):
            # Bias towards emptier rooms
            choice = random.choices(ROOM_TYPES, weights=[50, 30, 12, 8])[0]
            cell = {"type": choice, "visited": False}
            if choice == 'monster':
                # pick a monster template and attach a scaled variant
                template = random.choice(MONSTER_BASE)
                # scale by random factor so later rooms can be harder
                multiplier = random.choice([1, 1, 1, 2])
                cell['monster'] = {
                    "name": template['name'],
                    "hp": template['hp'] * multiplier,
                    "atk": template['atk'] * multiplier,
                    "exp": template['exp'] * multiplier
                }
            elif choice == 'treasure':
                cell['treasure'] = {
                    'item': random.choice(TREASURE_ITEMS),
                    'amount': random.randint(1, 5)
                }
            elif choice == 'trap':
                cell['trap'] = {
                    'damage': random.randint(1, 6)
                }
            row.append(cell)
        grid.append(row)
    # Guarantee start cell is empty
    grid[0][0] = {"type": "empty", "visited": True}
    return {
        "size": size,
        "grid": grid
    }


def save_player(player):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO players (id, name, health, max_health, level, exp, inventory, x, y, dungeon, in_battle, monster, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        player['id'], player.get('name'), player['health'], player['max_health'], player['level'],
        player.get('exp', 0), json.dumps(player.get('inventory', [])), player['x'], player['y'], json.dumps(player['dungeon']),
        1 if player.get('in_battle') else 0, json.dumps(player.get('monster')) if player.get('monster') else None, player.get('created_at')
    ))
    db.commit()


def load_player(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM players WHERE id = ?', (pid,))
    row = cur.fetchone()
    if not row:
        return None
    player = dict(row)
    player['inventory'] = json.loads(player['inventory']) if player['inventory'] else []
    player['dungeon'] = json.loads(player['dungeon']) if player['dungeon'] else None
    player['in_battle'] = bool(player['in_battle'])
    player['monster'] = json.loads(player['monster']) if player['monster'] else None
    return player


def apply_level_up(player):
    # simple levelling: every 20 exp -> +1 level
    while player.get('exp', 0) >= player.get('level', 1) * 20:
        player['exp'] -= player['level'] * 20
        player['level'] += 1
        player['max_health'] += 5
        player['health'] = player['max_health']


# ---------------------- Endpoints ----------------------

@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.get_json() or {}
    name = data.get('name') or f'Adventurer_{random.randint(1000,9999)}'
    size = data.get('dungeon_size', random.randint(4, 6))

    player = {
        'id': str(uuid.uuid4()),
        'name': name,
        'health': 20,
        'max_health': 20,
        'level': 1,
        'exp': 0,
        'inventory': [],
        'x': 0,
        'y': 0,
        'dungeon': generate_dungeon(size=size),
        'in_battle': False,
        'monster': None,
        'created_at': datetime.utcnow().isoformat()
    }

    save_player(player)
    # Hide dungeon grid in response but give size and player id
    resp = {
        'player_id': player['id'],
        'name': player['name'],
        'level': player['level'],
        'health': player['health'],
        'position': {'x': player['x'], 'y': player['y']},
        'dungeon_size': player['dungeon']['size']
    }
    return jsonify({'ok': True, 'player': resp}), 201

@app.route('/fight', methods=['POST'])
def fight():
    data = request.get_json() or {}
    pid = data.get('player_id')
    action = (data.get('action') or 'attack').lower()
    if not pid:
        return jsonify({'ok': False, 'error': 'player_id required'}), 400

    player = load_player(pid)
    if not player:
        return jsonify({'ok': False, 'error': 'player not found'}), 404

    if not player.get('in_battle') or not player.get('monster'):
        return jsonify({'ok': False, 'error': 'No monster to fight'}), 400

    monster = player['monster']

    if action == 'run':
        # small chance to escape
        if random.random() < 0.6:
            player['in_battle'] = False
            player['monster'] = None
            save_player(player)
            return jsonify({'ok': True, 'result': 'escaped', 'message': 'You escaped the fight.'})
        else:
            # failed escape -> monster hits once
            m_atk = max(1, random.randint(1, monster.get('atk', 1)))
            player['health'] -= m_atk
            if player['health'] <= 0:
                player['health'] = 0
            save_player(player)
            return jsonify({'ok': True, 'result': 'failed_escape', 'damage_taken': m_atk, 'health': player['health']})

    # Player attack
    p_atk = random.randint(1, 4) + (player.get('level', 1) - 1)
    monster['hp'] -= p_atk

    result = {'player_attack': p_atk}

    if monster['hp'] <= 0:
        # monster defeated
        gained_exp = monster.get('exp', 5)
        player['exp'] = player.get('exp', 0) + gained_exp
        # small loot chance
        loot = None
        if random.random() < 0.5:
            loot = random.choice(TREASURE_ITEMS)
            player['inventory'].append({loot: 1})

        player['in_battle'] = False
        player['monster'] = None
        apply_level_up(player)
        save_player(player)
        result.update({'monster_defeated': True, 'gained_exp': gained_exp, 'loot': loot, 'health': player['health'], 'level': player['level'], 'exp': player['exp']})
        return jsonify({'ok': True, 'result': result})

    # Monster attacks back
    m_atk = random.randint(1, monster.get('atk', 1))
    player['health'] -= m_atk
    if player['health'] <= 0:
        player['health'] = 0
    player['monster'] = monster
    save_player(player)

    result.update({'monster_attack': m_atk, 'monster_hp': monster['hp'], 'player_health': player['health']})
    return jsonify({'ok': True, 'result': result})


@app.route('/status', methods=['GET'])
def status():
    pid = request.args.get('player_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'player_id query param required'}), 400

    player = load_player(pid)
    if not player:
        return jsonify({'ok': False, 'error': 'player not found'}), 404

    # Hide full dungeon grid but provide visited map and size
    dungeon = player['dungeon']
    size = dungeon['size']
    visited = [[cell.get('visited', False) for cell in row] for row in dungeon['grid']]

    resp = {
        'id': player['id'],
        'name': player['name'],
        'level': player['level'],
        'exp': player.get('exp', 0),
        'health': player['health'],
        'max_health': player['max_health'],
        'inventory': player.get('inventory', []),
        'position': {'x': player['x'], 'y': player['y']},
        'dungeon_size': size,
        'visited': visited,
        'in_battle': player.get('in_battle', False),
        'monster': player.get('monster') if player.get('in_battle') else None
    }
    return jsonify({'ok': True, 'status': resp})


# ---------------------- Utility: dump all players (dev) ----------------------
@app.route('/_debug/players', methods=['GET'])
def debug_players():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id, name, level, health, x, y, in_battle, created_at FROM players')
    rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])


# ---------------------- Extra Gameplay Endpoints ----------------------

@app.route('/use_item', methods=['POST'])
def use_item():
    data = request.get_json() or {}
    pid = data.get('player_id')
    item = (data.get('item') or '').lower()
    if not pid or not item:
        return jsonify({'ok': False, 'error': 'player_id and item required'}), 400

    player = load_player(pid)
    if not player:
        return jsonify({'ok': False, 'error': 'player not found'}), 404

    # find item in inventory
    idx = None
    for i, it in enumerate(player.get('inventory', [])):
        if item in it and it[item] > 0:
            idx = i
            break
    if idx is None:
        return jsonify({'ok': False, 'error': 'item not in inventory'}), 400

    # healing potion logic
    if item == 'healing_potion':
        heal = random.randint(4, 8)
        player['health'] = min(player['max_health'], player['health'] + heal)
        player['inventory'][idx][item] -= 1
        if player['inventory'][idx][item] <= 0:
            player['inventory'].pop(idx)
        save_player(player)
        return jsonify({'ok': True, 'healed': heal, 'health': player['health']})

    return jsonify({'ok': False, 'error': 'item has no use yet'}), 400


@app.route('/respawn', methods=['POST'])
def respawn():
    data = request.get_json() or {}
    pid = data.get('player_id')
    player = load_player(pid)
    if not player:
        return jsonify({'ok': False, 'error': 'player not found'}), 404
    if player['health'] > 0:
        return jsonify({'ok': False, 'error': 'player is not dead'}), 400

    # respawn at start with penalty
    player['health'] = player['max_health']
    player['x'] = 0
    player['y'] = 0
    player['exp'] = max(0, player.get('exp', 0) - 5)
    player['in_battle'] = False
    player['monster'] = None
    save_player(player)
    return jsonify({'ok': True, 'message': 'Respawned at entrance', 'health': player['health'], 'exp': player['exp']})


@app.route('/map', methods=['GET'])
def ascii_map():
    pid = request.args.get('player_id')
    player = load_player(pid)
    if not player:
        return jsonify({'ok': False, 'error': 'player not found'}), 404

    dungeon = player['dungeon']
    size = dungeon['size']
    grid = dungeon['grid']
    lines = []
    for y in range(size):
        row = []
        for x in range(size):
            if player['x'] == x and player['y'] == y:
                row.append('P')
            else:
                cell = grid[y][x]
                row.append('.' if cell.get('visited') else '#')
        lines.append(' '.join(row))
    return jsonify({'ok': True, 'map': '\n'.join(lines)})

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT name, level, exp FROM players ORDER BY level DESC, exp DESC LIMIT 10')
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify({'ok': True, 'leaders': rows})

# ---------------------- Boss + Eventful Movement + Equipment ----------------------

DIRECTIONS = {
    'north': (0, -1),
    'south': (0, 1),
    'east': (1, 0),
    'west': (-1, 0),
}


def available_moves(player):
    size = player['dungeon']['size']
    x, y = player['x'], player['y']
    moves = []
    for name, (dx, dy) in DIRECTIONS.items():
        nx, ny = x + dx, y + dy
        if 0 <= nx < size and 0 <= ny < size:
            moves.append(name)
    return moves


@app.route('/move', methods=['POST'])
def move():
    data = request.get_json() or {}
    pid = data.get('player_id')
    direction = (data.get('direction') or '').lower()

    if direction not in DIRECTIONS:
        return jsonify({'ok': False, 'error': 'invalid direction'}), 400

    player = load_player(pid)
    if not player:
        return jsonify({'ok': False, 'error': 'player not found'}), 404

    dx, dy = DIRECTIONS[direction]
    nx, ny = player['x'] + dx, player['y'] + dy
    size = player['dungeon']['size']

    if not (0 <= nx < size and 0 <= ny < size):
        return jsonify({'ok': True, 'moved': False, 'event': 'A cold stone wall blocks your path.', 'available_moves': available_moves(player)})

    player['x'], player['y'] = nx, ny
    player['dungeon']['grid'][ny][nx]['visited'] = True

    # Boss room (bottom-right corner)
    if nx == size-1 and ny == size-1 and player['level'] >= 5:
        player['in_battle'] = True
        player['monster'] = {'name': 'Dungeon Warden', 'hp': 35, 'attack': 6}
        save_player(player)
        return jsonify({'ok': True, 'moved': True, 'event': 'The air trembles... The Dungeon Warden awakens!', 'available_moves': available_moves(player), 'boss': True})

    # Normal ambient flavor
    ambience = random.choice([
        'You hear dripping water...',
        'A distant growl echoes...',
        'Dust falls from the ceiling...',
        'You feel like you are being watched...'
    ])

    # Random encounters
    roll = random.random()
    if roll < 0.35:
        player['in_battle'] = True
        player['monster'] = {'name': 'Goblin', 'hp': random.randint(6, 10), 'attack': 3}
        event = 'A Goblin jumps out!'
    elif roll < 0.55:
        player.setdefault('inventory', []).append({'healing_potion': 1})
        event = 'You found a healing potion!'
    elif roll < 0.70:
        dmg = random.randint(2, 5)
        player['health'] -= dmg
        event = f'A trap triggers! You take {dmg} damage.'
    else:
        event = ambience

    save_player(player)
    return jsonify({'ok': True, 'moved': True, 'event': event, 'available_moves': available_moves(player)})


@app.route('/equip', methods=['POST'])
def equip():
    data = request.get_json() or {}
    pid = data.get('player_id')
    item = (data.get('item') or '').lower()

    player = load_player(pid)
    if not player:
        return jsonify({'ok': False, 'error': 'player not found'}), 404

    for it in player.get('inventory', []):
        if item in it and it[item] > 0:
            player['equipped'] = item
            save_player(player)
            return jsonify({'ok': True, 'equipped': item})

    return jsonify({'ok': False, 'error': 'item not owned'}), 400


# modify fight to use weapon bonus
old_fight = fight

def fight():
    data = request.get_json() or {}
    pid = data.get('player_id')
    action = (data.get('action') or 'attack').lower()

    player = load_player(pid)
    if not player or not player.get('in_battle'):
        return jsonify({'ok': False, 'error': 'no active battle'}), 400

    monster = player['monster']

    if action == 'run':
        player['in_battle'] = False
        player['monster'] = None
        save_player(player)
        return jsonify({'ok': True, 'escaped': True})

    # weapon bonus
    bonus = 0
    if player.get('equipped') == 'rusty_sword':
        bonus = 2

    player_dmg = random.randint(3, 6) + bonus
    monster['hp'] -= player_dmg

    if monster['hp'] <= 0:
        player['exp'] += 3
        player['in_battle'] = False
        player['monster'] = None
        save_player(player)
        return jsonify({'ok': True, 'victory': True, 'damage': player_dmg, 'exp': player['exp']})

    # monster attacks back
    m_dmg = monster['attack']
    player['health'] -= m_dmg
    save_player(player)
    return jsonify({'ok': True, 'damage': player_dmg, 'monster_damage': m_dmg, 'player_health': player['health']})

app.view_functions['fight'] = fight

@app.route("/delete_character", methods=["POST"])
def delete_character():
    data = request.get_json()

    if not data or "player_id" not in data:
        return jsonify({"ok": False, "error": "player_id required"}), 400

    player_id = data["player_id"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check player exists
    cursor.execute("SELECT id FROM players WHERE id = ?", (player_id,))
    player = cursor.fetchone()

    if not player:
        conn.close()
        return jsonify({"ok": False, "error": "Player not found"}), 404

    # Delete player
    cursor.execute("DELETE FROM players WHERE id = ?", (player_id,))
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "Character deleted. New adventure can begin."
    })

# ---------------------- Main ----------------------
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=5000)
