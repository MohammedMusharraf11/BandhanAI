import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "@/store/auth-store";
import { useChatStore, ChatMessage } from "@/store/chat-store";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useWebSocket(sessionId: string) {
  const token = useAuthStore((state) => state.token);
  const { addMessage, appendMessageChunk, setTyping, setActiveApproval } = useChatStore();
  const socketRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 5;

  const connect = useCallback(() => {
    if (!token || !sessionId) {
      console.warn("[WS] Cannot connect: missing", !token ? "token" : "sessionId");
      return;
    }

    // Don't exceed max retries
    if (retryCountRef.current >= maxRetries) {
      console.error("[WS] Max retries reached, giving up.");
      return;
    }
    
    // Ensure we close any existing socket first
    if (socketRef.current) {
      socketRef.current.close();
    }

    const wsUrl = `${WS_URL}/ws/${sessionId}?token=${token}`;
    console.log("[WS] Connecting to:", wsUrl.substring(0, 80) + "...");
    
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("[WS] Connection established!");
      retryCountRef.current = 0; // Reset retry count on success
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("[WS] Received message:", data.type);

        switch (data.type) {
          case "typing":
            setTyping(data.status);
            break;
          case "message_chunk":
            appendMessageChunk(data.content);
            break;
          case "message":
            // Final, complete message
            setTyping(false);
            addMessage({
              id: Math.random().toString(),
              type: "message",
              content: data.content,
              sender: "agent",
              timestamp: data.timestamp || new Date().toISOString(),
            });
            break;
          case "user_message":
            // Echoed user message
            addMessage({
              id: Math.random().toString(),
              type: "user_message",
              content: data.content,
              sender: "user",
              timestamp: data.timestamp || new Date().toISOString(),
            });
            break;
          case "tool_call":
            addMessage({
              id: Math.random().toString(),
              type: "tool_call",
              content: `Executing tool: ${data.tool_name}`,
              sender: "system",
              timestamp: data.timestamp || new Date().toISOString(),
              toolName: data.tool_name,
              args: data.args,
            });
            break;
          case "approval_request":
            const approvalMsg: ChatMessage = {
              id: Math.random().toString(),
              type: "approval_request",
              content: data.data.message || "Approval required for campaign action.",
              sender: "agent",
              timestamp: data.timestamp || new Date().toISOString(),
              data: data.data,
              interruptId: data.interrupt_id,
            };
            addMessage(approvalMsg);
            setActiveApproval(approvalMsg);
            break;
          case "error":
            setTyping(false);
            addMessage({
              id: Math.random().toString(),
              type: "error",
              content: data.message,
              sender: "system",
              timestamp: data.timestamp || new Date().toISOString(),
            });
            break;
          case "pong":
            break;
          default:
            console.log("[WS] Unhandled message type:", data.type);
        }
      } catch (e) {
        console.error("Error parsing socket message:", e);
      }
    };

    socket.onerror = (err) => {
      console.error("[WS] Connection error (this is normal if server is starting up)");
    };

    socket.onclose = (event) => {
      console.log(`[WS] Connection closed: code=${event.code}, reason=${event.reason || "none"}, clean=${event.wasClean}`);
      
      // Auto-retry on unexpected close (not manual close)
      if (event.code !== 1000 && event.code !== 1001) {
        retryCountRef.current += 1;
        const delay = Math.min(2000 * retryCountRef.current, 10000);
        console.log(`[WS] Retrying in ${delay}ms (attempt ${retryCountRef.current}/${maxRetries})...`);
        setTimeout(() => connect(), delay);
      }
    };
  }, [token, sessionId, addMessage, appendMessageChunk, setTyping, setActiveApproval]);

  useEffect(() => {
    connect();
    return () => {
      retryCountRef.current = maxRetries; // Prevent retries on unmount
      if (socketRef.current) {
        socketRef.current.close(1000, "Component unmounted");
      }
    };
  }, [connect]);

  const sendMessage = useCallback((content: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "message",
          content,
        })
      );
    } else {
      console.error("Cannot send message: WebSocket is not open.");
    }
  }, []);

  const sendApprovalResponse = useCallback((action: "continue" | "update" | "feedback", data?: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "approval_response",
          action,
          data,
        })
      );
      // Clear active approval card from state
      setActiveApproval(null);
    } else {
      console.error("Cannot send approval response: WebSocket is not open.");
    }
  }, [setActiveApproval]);

  return { sendMessage, sendApprovalResponse };
}

function logger(...args: any[]) {
  if (process.env.NODE_ENV !== "production") {
    console.log("[WS]", ...args);
  }
}
