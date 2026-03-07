from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import string
import uuid
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_GUESSES = 6
TOTAL_ROUNDS = 10

# In-memory store
rooms = {}

TOPICS = ["animals", "space", "nature", "technology", "sports", "food", "music", "movies"]

# --------------- Models ---------------

class JoinRequest(BaseModel):
    room_code: str
    player_name: str

class CreateRequest(BaseModel):
    player_name: str

class WordSubmitRequest(BaseModel):
    word: str
    hint: str

# --------------- Helpers ---------------

def generate_room_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=4))
        if code not in rooms:
            return code

def mask_word(word: str, guessed: set) -> str:
    return "".join([c if c in guessed or c == ' ' else "_" for c in word])

def get_room_view(room: dict) -> dict:
    game = room.get("current_game")
    masked = None
    if game:
        if room["phase"] == "result" or room["phase"] == "final":
            masked = game["word"]
        else:
            masked = mask_word(game["word"], game["guessed_letters"])

    return {
        "room_code": room["room_code"],
        "phase": room["phase"],  # waiting_for_player2, word_setting, guessing, result, final
        "round": room["round"],
        "total_rounds": TOTAL_ROUNDS,
        "players": {
            p_id: {"name": p["name"], "score": p["score"]}
            for p_id, p in room["players"].items()
        },
        "setter_id": room.get("setter_id"),
        "guesser_id": room.get("guesser_id"),
        "game": {
            "masked_word": masked,
            "hint": game["hint"] if game else None,
            "remaining_guesses": game["remaining_guesses"] if game else None,
            "guessed_letters": list(game["guessed_letters"]) if game else [],
            "status": game["status"] if game else None,
        } if game else None,
    }

# --------------- Endpoints ---------------

@app.post("/api/room/create")
def create_room(req: CreateRequest):
    room_code = generate_room_code()
    player_id = str(uuid.uuid4())

    rooms[room_code] = {
        "room_code": room_code,
        "phase": "waiting_for_player2",
        "round": 0,
        "players": {
            player_id: {"name": req.player_name, "score": 0}
        },
        "player_order": [player_id],
        "setter_id": player_id,   # Player 1 sets the word first
        "guesser_id": None,
        "current_game": None,
    }

    return {"room_code": room_code, "player_id": player_id}


@app.post("/api/room/join")
def join_room(req: JoinRequest):
    room = rooms.get(req.room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if len(room["players"]) >= 2:
        raise HTTPException(status_code=400, detail="Room is full")

    player_id = str(uuid.uuid4())
    room["players"][player_id] = {"name": req.player_name, "score": 0}
    room["player_order"].append(player_id)
    room["guesser_id"] = player_id
    room["phase"] = "word_setting"
    room["round"] = 1

    return {"room_code": req.room_code.upper(), "player_id": player_id}


@app.get("/api/room/{room_code}")
def get_room(room_code: str):
    room = rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return get_room_view(room)


@app.post("/api/room/{room_code}/submit-word")
def submit_word(room_code: str, req: WordSubmitRequest, player_id: str):
    room = rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["phase"] != "word_setting":
        raise HTTPException(status_code=400, detail="Not in word-setting phase")
    if room["setter_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the setter can submit the word")

    word = req.word.upper().strip()
    if not all(c.isalpha() or c == ' ' for c in word):
        raise HTTPException(status_code=400, detail="Word must contain only letters")

    room["current_game"] = {
        "word": word,
        "hint": req.hint.strip(),
        "guessed_letters": set(),
        "remaining_guesses": MAX_GUESSES,
        "status": "playing",
    }
    room["phase"] = "guessing"

    return get_room_view(room)


@app.post("/api/room/{room_code}/guess")
def guess_letter(room_code: str, player_id: str, letter: str):
    room = rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["phase"] != "guessing":
        raise HTTPException(status_code=400, detail="Not in guessing phase")
    if room["guesser_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the guesser can guess")

    letter = letter.upper()
    if not letter.isalpha() or len(letter) != 1:
        raise HTTPException(status_code=400, detail="Invalid guess")

    game = room["current_game"]
    if letter in game["guessed_letters"]:
        return get_room_view(room)

    game["guessed_letters"].add(letter)

    if letter not in game["word"]:
        game["remaining_guesses"] -= 1

    masked = mask_word(game["word"], game["guessed_letters"])

    if game["remaining_guesses"] <= 0:
        game["status"] = "lost"
        _end_round(room, won=False)
    elif "_" not in masked:
        game["status"] = "won"
        _end_round(room, won=True)

    return get_room_view(room)


@app.post("/api/room/{room_code}/next-round")
def next_round(room_code: str, player_id: str):
    room = rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["phase"] != "result":
        raise HTTPException(status_code=400, detail="Not in result phase")

    if room["round"] >= TOTAL_ROUNDS:
        room["phase"] = "final"
    else:
        room["round"] += 1
        # Swap roles
        old_setter = room["setter_id"]
        room["setter_id"] = room["guesser_id"]
        room["guesser_id"] = old_setter
        room["current_game"] = None
        room["phase"] = "word_setting"

    return get_room_view(room)


def _end_round(room: dict, won: bool):
    game = room["current_game"]
    guesser_id = room["guesser_id"]
    score = game["remaining_guesses"] if won else 0
    room["players"][guesser_id]["score"] += score
    room["phase"] = "result"
