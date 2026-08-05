import { useEffect } from "react";
import { WS_BASE } from "../config";

export default function useDisplaySocket(
  restaurantId,
  onMessage,
  enabled = true
) {
  useEffect(() => {
    if (!restaurantId || !enabled) return;

    const socket = new WebSocket(
      `${WS_BASE}/ws/display/${restaurantId}/`
    );

    socket.onopen = () => {
      console.log("Display WebSocket connected ✅");
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        console.error("Invalid WS message:", err);
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socket.onclose = () => {
      console.log("WebSocket closed");
    };

    return () => socket.close();
  }, [restaurantId, enabled]);
}