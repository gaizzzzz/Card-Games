const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function createRoom(playerName, maxPlayers) {
  return request("/rooms", {
    method: "POST",
    body: JSON.stringify({ player_name: playerName, max_players: maxPlayers }),
  });
}

export function joinRoom(roomId, playerName) {
  return request(`/rooms/${roomId}/join`, {
    method: "POST",
    body: JSON.stringify({ player_name: playerName }),
  });
}

export function startRoom(roomId, playerId) {
  return request(`/rooms/${roomId}/start`, {
    method: "POST",
    body: JSON.stringify({ player_id: playerId }),
  });
}

export function roomAction(roomId, playerId, action) {
  return request(`/rooms/${roomId}/action`, {
    method: "POST",
    body: JSON.stringify({ player_id: playerId, action }),
  });
}

export function fetchRoomState(roomId, playerId) {
  const qs = playerId ? `?player_id=${encodeURIComponent(playerId)}` : "";
  return request(`/rooms/${roomId}/state${qs}`);
}

export { API_BASE };
