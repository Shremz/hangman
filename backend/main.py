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
    total_rounds: int = 5

class WordSubmitRequest(BaseModel):
    word: str
    hint: str

class ChatRequest(BaseModel):
    player_id: str
    message: str

# --------------- Helpers ---------------

def generate_room_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=4))
        if code not in rooms:
            return code

def mask_word(word: str, guessed: set) -> str:
    return "".join([c if c in guessed or c == ' ' else "_" for c in word])

def get_room_view(room: dict, requesting_player_id: str = None) -> dict:
    game = room.get("current_game")
    masked = None
    is_setter = requesting_player_id == room.get("setter_id")

    if game:
        if room["phase"] in ["result", "final"] or is_setter:
            masked = game["word"]
        else:
            masked = mask_word(game["word"], game["guessed_letters"])

    return {
        "room_code": room["room_code"],
        "phase": room["phase"],  # waiting_for_player2, word_setting, guessing, result, final
        "round": room["round"],
        "total_rounds": room["total_rounds"],
        "current_turn": room["current_turn"],
        "players": {
            p_id: {"name": p["name"], "score": p["score"]}
            for p_id, p in room["players"].items()
        },
        "setter_id": room.get("setter_id"),
        "guesser_id": room.get("guesser_id"),
        "messages": room.get("messages", []),
        "game": {
            "masked_word": masked,
            "is_reveal": is_setter and room["phase"] == "guessing",
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
        "total_rounds": req.total_rounds,
        "current_turn": 0, # Total turns taken
        "players": {
            player_id: {"name": req.player_name, "score": 0}
        },
        "player_order": [player_id],
        "setter_id": player_id,
        "guesser_id": None,
        "current_game": None,
        "messages": [],
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
def get_room(room_code: str, player_id: str = None):
    room = rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return get_room_view(room, player_id)


@app.post("/api/room/{room_code}/chat")
def send_chat(room_code: str, req: ChatRequest):
    room = rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    player = room["players"].get(req.player_id)
    if not player:
        raise HTTPException(status_code=403, detail="Not in room")

    msg_obj = {
        "player_name": player["name"],
        "message": req.message,
        "timestamp": str(uuid.uuid4())[:8] # simplified ID
    }
    room.setdefault("messages", []).append(msg_obj)
    # limit to last 50 messages
    if len(room["messages"]) > 50:
        room["messages"].pop(0)

    return {"status": "ok"}


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

    return get_room_view(room, player_id)


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
        return get_room_view(room, player_id)

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

    return get_room_view(room, player_id)


@app.post("/api/room/{room_code}/next-round")
def next_round(room_code: str, player_id: str):
    room = rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["phase"] != "result":
        raise HTTPException(status_code=400, detail="Not in result phase")

    # current_turn is now incremented in _end_round
    
    # Check if we finished all turns (2 turns per round)
    if room["current_turn"] >= room["total_rounds"] * 2:
        room["phase"] = "final"
    else:
        # Increment round number every 2 turns
        # If current_turn is even, we just finished the 2nd part of a round
        if room["current_turn"] % 2 == 0:
            room["round"] += 1
            
        # Swap roles
        old_setter = room["setter_id"]
        room["setter_id"] = room["guesser_id"]
        room["guesser_id"] = old_setter
        room["current_game"] = None
        room["phase"] = "word_setting"

    return get_room_view(room, player_id)


def _end_round(room: dict, won: bool):
    game = room["current_game"]
    guesser_id = room["guesser_id"]
    score = game["remaining_guesses"] if won else 0
    room["players"][guesser_id]["score"] += score
    room["current_turn"] += 1
    room["phase"] = "result"
