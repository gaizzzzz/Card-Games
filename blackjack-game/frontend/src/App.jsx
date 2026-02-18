import { useEffect, useMemo, useState } from "react";
import { API_BASE, createRoom, fetchRoomState, joinRoom, roomAction, startRoom } from "./api";

function CardView({ card }) {
  if (!card || card.hidden) return <div className="card back">?</div>;
  return (
    <div className="card">
      <img src={`${API_BASE}${card.image_url}`} alt={`${card.rank} of ${card.suit}`} />
    </div>
  );
}

function Hand({ title, score, cards = [], subtitle }) {
  return (
    <section className="hand">
      <div className="hand-header">
        <h3>{title}</h3>
        <span>Score: {score ?? "-"}</span>
      </div>
      {subtitle ? <p className="subtitle">{subtitle}</p> : null}
      <div className="cards">
        {cards.map((card, idx) => (
          <CardView key={idx} card={card} />
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const [playerName, setPlayerName] = useState("");
  const [roomIdInput, setRoomIdInput] = useState("");
  const [maxPlayers, setMaxPlayers] = useState(2);
  const [session, setSession] = useState(null);
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const hasSession = !!session?.roomId && !!session?.playerId;

  async function refresh() {
    if (!hasSession) return;
    try {
      const data = await fetchRoomState(session.roomId, session.playerId);
      setState(data);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (!hasSession) return undefined;
    refresh();
    const timer = setInterval(refresh, 1000);
    return () => clearInterval(timer);
  }, [session?.roomId, session?.playerId]);

  async function onCreateRoom() {
    if (!playerName.trim()) return setError("Enter your name.");
    setBusy(true);
    try {
      const data = await createRoom(playerName.trim(), Number(maxPlayers));
      setSession({ roomId: data.room_id, playerId: data.player_id });
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onJoinRoom() {
    if (!playerName.trim() || !roomIdInput.trim()) return setError("Enter name and room ID.");
    setBusy(true);
    try {
      const data = await joinRoom(roomIdInput.trim().toUpperCase(), playerName.trim());
      setSession({ roomId: data.room_id, playerId: data.player_id });
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onStart() {
    if (!hasSession) return;
    setBusy(true);
    try {
      await startRoom(session.roomId, session.playerId);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onAction(action) {
    if (!hasSession) return;
    setBusy(true);
    try {
      await roomAction(session.roomId, session.playerId, action);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const youAreCurrent = useMemo(() => {
    if (!state || state.your_player_index === null) return false;
    return state.current_player_index === state.your_player_index;
  }, [state]);

  return (
    <main className="app">
      <header>
        <h1>Blackjack Multiplayer</h1>
      </header>

      {!hasSession ? (
        <section className="panel">
          <h2>Join A Room</h2>
          <div className="row">
            <label>Name</label>
            <input value={playerName} onChange={(e) => setPlayerName(e.target.value)} />
          </div>
          <div className="row">
            <label>Max Players (Create)</label>
            <input
              type="number"
              min={1}
              max={8}
              value={maxPlayers}
              onChange={(e) => setMaxPlayers(e.target.value)}
            />
          </div>
          <div className="actions">
            <button onClick={onCreateRoom} disabled={busy}>
              Create Room
            </button>
          </div>
          <div className="row">
            <label>Room ID (Join)</label>
            <input value={roomIdInput} onChange={(e) => setRoomIdInput(e.target.value.toUpperCase())} />
          </div>
          <div className="actions">
            <button onClick={onJoinRoom} disabled={busy}>
              Join Room
            </button>
          </div>
        </section>
      ) : (
        <>
          <section className="panel">
            <p>
              <strong>Room:</strong> {session.roomId}
            </p>
            <p>
              <strong>Phase:</strong> {state?.phase || "loading"}
            </p>
            {state?.phase === "waiting" ? (
              <button onClick={onStart} disabled={!state?.can_start || busy}>
                Start Game
              </button>
            ) : null}
            {state?.phase === "player_turns" ? (
              <div className="actions">
                <button onClick={() => onAction("hit")} disabled={!state?.can_act || busy}>
                  Hit
                </button>
                <button onClick={() => onAction("stand")} disabled={!state?.can_act || busy}>
                  Stand
                </button>
              </div>
            ) : null}
            {state?.phase === "player_turns" ? (
              <p className="subtitle">{youAreCurrent ? "Your turn" : "Waiting for another player"}</p>
            ) : null}
          </section>

          {state ? (
            <>
              <Hand title="Dealer" score={state.dealer.score} cards={state.dealer.cards} />
              <section className="players">
                {state.players.map((player, idx) => (
                  <Hand
                    key={idx}
                    title={player.name}
                    score={player.score}
                    cards={player.cards}
                    subtitle={player.result || (player.resolved ? "Resolved" : "")}
                  />
                ))}
              </section>
            </>
          ) : null}

          {state?.phase === "results" && state.results?.length ? (
            <section className="panel">
              <h2>Results</h2>
              <ul>
                {state.results.map((r, idx) => (
                  <li key={idx}>
                    {r.name}: {r.result}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}

      {error ? <p className="error">{error}</p> : null}
    </main>
  );
}
