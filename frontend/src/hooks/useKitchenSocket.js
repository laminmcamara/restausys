import { useEffect, useRef } from "react";
import { WS_BASE } from "../config";

/**
 * Kitchen Order WebSocket Hook
 * Connects to:
 *   ws://.../ws/kitchen/{restaurantId}/
 */
export default function useKitchenSocket(
  restaurantId,
  onMessage,
  enabled = true
) {
  const socketRef = useRef(null);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (!restaurantId || !enabled) return;

    const socket = new WebSocket(`${WS_BASE}/ws/kitchen/${restaurantId}/`);

    socketRef.current = socket;

    socket.onopen = () => {
      console.log("✅ Kitchen WebSocket connected");
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (onMessageRef.current) {
          onMessageRef.current(data);
        }
      } catch (err) {
        console.error("Invalid WebSocket message:", err);
      }
    };

    socket.onerror = (error) => {
      console.error("Kitchen WebSocket error:", error);
    };

    socket.onclose = () => {
      console.log("⚠️ Kitchen WebSocket closed");
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [restaurantId, enabled]);
}