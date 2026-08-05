const isLocal = window.location.hostname === "localhost";

export const API_BASE = isLocal
  ? "http://localhost:8000"
  : "";

export const WS_BASE = isLocal
  ? "ws://localhost:8000"
  : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;