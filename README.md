# 🎮 Hangman — Multiplayer Web Game

A real-time multiplayer Hangman game built with a **Python FastAPI** backend and a **React (Vite)** frontend.

---

## ✨ Features

- 🕹️ **Multiplayer Mode** — One player sets the word + hint, the other guesses
- 🔄 **Role Swapping** — Players alternate between word-setter and guesser each round
- 🏆 **Scoring System** — Score = remaining guesses (max 6, min 0)
- 📊 **Final Scoreboard** — After 10 rounds, the player with the most points wins
- 🎨 **Premium UI** — Glassmorphism design with smooth animations
- 🔗 **Room Codes** — Share a 4-letter code with a friend to join the same game

---

## 🗂️ Project Structure

```
Hangman/
├── backend/
│   ├── main.py            # FastAPI server — game logic, room management
│   └── requirements.txt   # Python dependencies
└── frontend/
    ├── src/
    │   ├── App.jsx        # All screens: Lobby, WordSetter, Guesser, Scoreboard
    │   └── index.css      # Full styling
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## 🎲 How to Play

1. **Open two browser tabs** at `http://localhost:5173`
2. **Tab 1 (Player 1):** Enter name → **Create Room** → share the 4-letter code
3. **Tab 2 (Player 2):** Enter name → paste code → **Join Room**
4. The word-setter types a **secret word** and a **hint**, then submits
5. The guesser sees the hint and guesses **one letter at a time**
6. Roles **swap** after every round
7. After **10 rounds**, the player with the highest score wins!

### Scoring

| Result | Score |
|--------|-------|
| Flawless guess (0 mistakes) | **6 pts** |
| Guessed with N mistakes | **(6 - N) pts** |
| Failed to guess | **0 pts** |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| Frontend | React 18, Vite |
| Styling | Vanilla CSS (Glassmorphism) |
| Multiplayer | HTTP Polling |
| Word API | Datamuse API |

---

## 📦 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/room/create` | Create a new room |
| `POST` | `/api/room/join` | Join an existing room |
| `GET` | `/api/room/{code}` | Poll room state |
| `POST` | `/api/room/{code}/submit-word` | Word-setter submits word & hint |
| `POST` | `/api/room/{code}/guess` | Guesser guesses a letter |
| `POST` | `/api/room/{code}/next-round` | Advance to next round |
