import { useState, useEffect, useCallback } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000/api';
const MAX_GUESSES = 6;

// ============================================================
// SCREEN: Lobby
// ============================================================
function LobbyScreen({ onRoomCreated, onRoomJoined }) {
  const [playerName, setPlayerName] = useState('');
  const [roomCode, setRoomCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const createRoom = async () => {
    if (!playerName.trim()) return setError('Please enter your name');
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_URL}/room/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_name: playerName.trim() })
      });
      const data = await res.json();
      onRoomCreated(data.room_code, data.player_id, playerName.trim());
    } catch { setError('Could not connect to server'); }
    finally { setLoading(false); }
  };

  const joinRoom = async () => {
    if (!playerName.trim()) return setError('Please enter your name');
    if (!roomCode.trim()) return setError('Please enter a room code');
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_URL}/room/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_name: playerName.trim(), room_code: roomCode.trim().toUpperCase() })
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      const data = await res.json();
      onRoomJoined(data.room_code, data.player_id, playerName.trim());
    } catch (e) { setError(e.message || 'Failed to join room'); }
    finally { setLoading(false); }
  };

  return (
    <div className="screen lobby-screen">
      <h1>HANGMAN</h1>
      <p className="subtitle">Multiplayer Mode</p>
      <div className="card">
        <input
          className="text-input"
          placeholder="Your name"
          value={playerName}
          onChange={e => setPlayerName(e.target.value)}
        />
        {error && <p className="error-msg">{error}</p>}
        <button className="primary-btn" onClick={createRoom} disabled={loading}>
          Create Room
        </button>
        <div className="divider">— or —</div>
        <input
          className="text-input code-input"
          placeholder="Room Code (e.g. XKBQ)"
          maxLength={4}
          value={roomCode}
          onChange={e => setRoomCode(e.target.value.toUpperCase())}
        />
        <button className="secondary-btn" onClick={joinRoom} disabled={loading}>
          Join Room
        </button>
      </div>
    </div>
  );
}

// ============================================================
// SCREEN: Waiting
// ============================================================
function WaitingScreen({ roomCode, message }) {
  return (
    <div className="screen waiting-screen">
      <h2>Waiting...</h2>
      <p>{message}</p>
      {roomCode && (
        <div className="room-code-display">
          <span className="label">Room Code</span>
          <span className="code">{roomCode}</span>
          <span className="hint-text">Share this with your friend!</span>
        </div>
      )}
      <div className="waiting-dots"><span /><span /><span /></div>
    </div>
  );
}

// ============================================================
// SCREEN: Word Setter
// ============================================================
function WordSetterScreen({ roomCode, playerId }) {
  const [word, setWord] = useState('');
  const [hint, setHint] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submitWord = async () => {
    if (!word.trim()) return setError('Please enter a word');
    if (!hint.trim()) return setError('Please enter a hint');
    if (!/^[a-zA-Z ]+$/.test(word)) return setError('Word can only contain letters');
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_URL}/room/${roomCode}/submit-word?player_id=${playerId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word: word.trim(), hint: hint.trim() })
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
    } catch (e) { setError(e.message || 'Failed to submit word'); setLoading(false); }
  };

  return (
    <div className="screen word-setter-screen">
      <h2>🖊️ Your Turn to Set</h2>
      <p className="subtitle">Choose a word for your opponent to guess</p>
      <div className="card">
        <input
          className="text-input"
          placeholder="Word (e.g. ELEPHANT)"
          value={word}
          onChange={e => setWord(e.target.value)}
        />
        <input
          className="text-input"
          placeholder="Hint / Category (e.g. Animal)"
          value={hint}
          onChange={e => setHint(e.target.value)}
        />
        {error && <p className="error-msg">{error}</p>}
        <button className="primary-btn" onClick={submitWord} disabled={loading}>
          {loading ? 'Submitting...' : 'Submit Word'}
        </button>
      </div>
    </div>
  );
}

// ============================================================
// SCREEN: Guesser (main game board)
// ============================================================
function GuesserScreen({ roomCode, playerId, room }) {
  const game = room.game;

  const handleGuess = async (letter) => {
    await fetch(`${API_URL}/room/${roomCode}/guess?player_id=${playerId}&letter=${letter}`, {
      method: 'POST'
    });
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (game?.status === 'playing') {
        const key = e.key.toUpperCase();
        if (/^[A-Z]$/.test(key) && !game.guessed_letters.includes(key)) {
          handleGuess(key);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [game]);

  if (!game) return <div className="screen"><p>Loading game...</p></div>;

  const MAX_GUESSES_LOCAL = MAX_GUESSES;
  const incorrectGuesses = MAX_GUESSES_LOCAL - game.remaining_guesses;
  const words = game.masked_word.split(' ');

  return (
    <div className="screen guesser-screen">
      <div className="round-info">Round {room.round} / {room.total_rounds}</div>
      <div className="container glass-panel">
        <div className="game-area">
          <Gallows incorrect={incorrectGuesses} />
          <div className="game-info">
            <div className="hint-display">Hint: <strong>{game.hint}</strong></div>
            <div className="word-display">
              {words.map((word, wi) => (
                <div key={wi} className="word-group">
                  {word.split('').map((c, ci) => (
                    <div key={ci} className={`letter-box ${c !== '_' ? 'revealed' : ''}`}>{c !== '_' ? c : ''}</div>
                  ))}
                </div>
              ))}
            </div>
            <div className="stats">Mistakes left: <strong className="guesses-left">{game.remaining_guesses}</strong></div>
          </div>
        </div>
        <Keyboard guessed={game.guessed_letters} onGuess={handleGuess} disabled={game.status !== 'playing'} />
      </div>
    </div>
  );
}

// ============================================================
// SCREEN: Round Result
// ============================================================
function RoundResultScreen({ room, playerId, onNext }) {
  const game = room.game;
  const players = Object.entries(room.players);
  const guesserName = room.players[room.guesser_id]?.name;
  const won = game?.status === 'won';

  return (
    <div className="screen result-screen">
      <div className={`result-banner ${won ? 'won' : 'lost'}`}>
        {won ? `🎉 ${guesserName} guessed it!` : `💀 ${guesserName} failed!`}
      </div>
      <p className="word-reveal">The word was: <strong>{game?.masked_word}</strong></p>
      <div className="scoreboard-mini">
        {players.map(([pid, p]) => (
          <div key={pid} className="score-row">
            <span>{p.name}</span>
            <span className="score-value">{p.score}</span>
          </div>
        ))}
      </div>
      <button className="primary-btn" onClick={onNext}>
        {room.round >= room.total_rounds ? 'See Final Results' : `Next Round →`}
      </button>
    </div>
  );
}

// ============================================================
// SCREEN: Final Scoreboard
// ============================================================
function FinalScreen({ room, onRestart }) {
  const players = Object.entries(room.players).sort((a, b) => b[1].score - a[1].score);
  const winner = players[0];
  const tie = players.length > 1 && players[0][1].score === players[1][1].score;

  return (
    <div className="screen final-screen">
      <h2>🏆 Game Over!</h2>
      {tie ? <p className="winner-text">It's a Tie!</p> : <p className="winner-text">{winner[1].name} wins!</p>}
      <div className="final-scoreboard">
        {players.map(([pid, p], i) => (
          <div key={pid} className={`final-score-row ${i === 0 && !tie ? 'winner' : ''}`}>
            <span className="rank">{i === 0 && !tie ? '🥇' : '🥈'}</span>
            <span>{p.name}</span>
            <span className="score-value">{p.score} pts</span>
          </div>
        ))}
      </div>
      <button className="primary-btn" onClick={onRestart}>Play Again</button>
    </div>
  );
}

// ============================================================
// SHARED COMPONENTS
// ============================================================
function Gallows({ incorrect }) {
  return (
    <div className="gallows-container">
      <svg viewBox="0 0 200 250" className="gallows-svg">
        <line x1="20" y1="230" x2="180" y2="230" className="draw-line" />
        <line x1="50" y1="230" x2="50" y2="20" className="draw-line" />
        <line x1="50" y1="20" x2="130" y2="20" className="draw-line" />
        <line x1="130" y1="20" x2="130" y2="50" className="draw-line" />
        <circle cx="130" cy="70" r="20" className={`figure-part head ${incorrect >= 1 ? 'visible' : ''}`} />
        <line x1="130" y1="90" x2="130" y2="150" className={`figure-part ${incorrect >= 2 ? 'visible' : ''}`} />
        <line x1="130" y1="100" x2="100" y2="130" className={`figure-part ${incorrect >= 3 ? 'visible' : ''}`} />
        <line x1="130" y1="100" x2="160" y2="130" className={`figure-part ${incorrect >= 4 ? 'visible' : ''}`} />
        <line x1="130" y1="150" x2="100" y2="190" className={`figure-part ${incorrect >= 5 ? 'visible' : ''}`} />
        <line x1="130" y1="150" x2="160" y2="190" className={`figure-part ${incorrect >= 6 ? 'visible' : ''}`} />
      </svg>
    </div>
  );
}

function Keyboard({ guessed, onGuess, disabled }) {
  return (
    <div className="keyboard">
      {'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map(letter => {
        const isGuessed = guessed.includes(letter);
        return (
          <button
            key={letter}
            className={`key-btn ${isGuessed ? (guessed.includes(letter) ? 'used' : '') : ''}`}
            disabled={disabled || isGuessed}
            onClick={() => onGuess(letter)}
          >{letter}</button>
        );
      })}
    </div>
  );
}

// ============================================================
// MAIN APP
// ============================================================
export default function App() {
  const [roomCode, setRoomCode] = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [room, setRoom] = useState(null);

  // Polling
  useEffect(() => {
    if (!roomCode) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/room/${roomCode}`);
        if (res.ok) setRoom(await res.json());
      } catch { }
    }, 1000);
    return () => clearInterval(interval);
  }, [roomCode]);

  const handleRoomCreated = (code, pid) => { setRoomCode(code); setPlayerId(pid); };
  const handleRoomJoined = (code, pid) => { setRoomCode(code); setPlayerId(pid); };

  const handleNextRound = async () => {
    await fetch(`${API_URL}/room/${roomCode}/next-round?player_id=${playerId}`, { method: 'POST' });
  };

  const handleRestart = () => { setRoomCode(null); setPlayerId(null); setRoom(null); };

  if (!roomCode) return (
    <>
      <div className="background-abstract" />
      <LobbyScreen onRoomCreated={handleRoomCreated} onRoomJoined={handleRoomJoined} />
    </>
  );

  if (!room) return (
    <>
      <div className="background-abstract" />
      <WaitingScreen roomCode={roomCode} message="Connecting to room..." />
    </>
  );

  const phase = room.phase;
  const isSetter = room.setter_id === playerId;
  const isGuesser = room.guesser_id === playerId;

  return (
    <>
      <div className="background-abstract" />
      {phase === 'waiting_for_player2' && (
        <WaitingScreen roomCode={roomCode} message="Waiting for your friend to join..." />
      )}
      {phase === 'word_setting' && isSetter && (
        <WordSetterScreen roomCode={roomCode} playerId={playerId} />
      )}
      {phase === 'word_setting' && !isSetter && (
        <WaitingScreen roomCode={null} message="Waiting for your opponent to set a word..." />
      )}
      {phase === 'guessing' && isGuesser && (
        <GuesserScreen roomCode={roomCode} playerId={playerId} room={room} />
      )}
      {phase === 'guessing' && !isGuesser && (
        <WaitingScreen roomCode={null} message="Your opponent is guessing..." />
      )}
      {phase === 'result' && (
        <RoundResultScreen room={room} playerId={playerId} onNext={handleNextRound} />
      )}
      {phase === 'final' && (
        <FinalScreen room={room} onRestart={handleRestart} />
      )}
    </>
  );
}
