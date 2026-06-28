import { useCallback, useRef, useState } from "react";
import { useAuthStore } from "@/store/auth-store";
import { useChatStore, ChatMessage } from "@/store/chat-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * useChat — REST streaming hook that replaces WebSocket for chat.
 * Sends messages via POST /api/chat and reads SSE stream for responses.
 */
export function useChat(sessionId: string) {
  const token = useAuthStore((state) => state.token);
  const { addMessage, appendMessageChunk, setTyping, setActiveApproval } =
    useChatStore();
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!token) {
        console.error("[Chat] No auth token available");
        return;
      }

      if (isStreaming) {
        console.warn("[Chat] Already streaming, ignoring new message");
        return;
      }

      // Add user message to UI immediately
      addMessage({
        id: Math.random().toString(),
        type: "user_message",
        content,
        sender: "user",
        timestamp: new Date().toISOString(),
      });

      setIsStreaming(true);
      setTyping(true);

      // Create abort controller for cancellation
      const abortController = new AbortController();
      abortRef.current = abortController;

      try {
        const response = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message: content,
            session_id: sessionId,
          }),
          signal: abortController.signal,
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let fullMessage = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE events
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep incomplete line in buffer

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const data = JSON.parse(jsonStr);

              switch (data.type) {
                case "typing":
                  setTyping(data.status);
                  break;

                case "message_chunk":
                  fullMessage += data.content;
                  appendMessageChunk(data.content);
                  break;

                case "message":
                  // Final complete message — already built via chunks
                  setTyping(false);
                  break;

                case "tool_call":
                  addMessage({
                    id: Math.random().toString(),
                    type: "tool_call",
                    content: `Executing tool: ${data.tool_name}`,
                    sender: "system",
                    timestamp: new Date().toISOString(),
                    toolName: data.tool_name,
                    args: data.args,
                  });
                  break;

                case "approval_request":
                  const approvalMsg: ChatMessage = {
                    id: Math.random().toString(),
                    type: "approval_request",
                    content:
                      data.data?.message ||
                      "Approval required for campaign action.",
                    sender: "agent",
                    timestamp: new Date().toISOString(),
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
                    timestamp: new Date().toISOString(),
                  });
                  break;

                case "done":
                  break;
              }
            } catch (parseErr) {
              console.warn("[Chat] Failed to parse SSE event:", jsonStr);
            }
          }
        }
      } catch (err: any) {
        if (err.name === "AbortError") {
          console.log("[Chat] Request aborted");
        } else {
          console.error("[Chat] Stream error:", err);
          addMessage({
            id: Math.random().toString(),
            type: "error",
            content: `Connection error: ${err.message}`,
            sender: "system",
            timestamp: new Date().toISOString(),
          });
        }
      } finally {
        setIsStreaming(false);
        setTyping(false);
        abortRef.current = null;
      }
    },
    [token, sessionId, isStreaming, addMessage, appendMessageChunk, setTyping, setActiveApproval]
  );

  const sendApprovalResponse = useCallback(
    async (action: "continue" | "update" | "feedback", data?: string) => {
      if (!token) return;

      setIsStreaming(true);
      setTyping(true);

      try {
        const response = await fetch(`${API_URL}/api/chat/approve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            session_id: sessionId,
            action,
            data,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const evt = JSON.parse(jsonStr);
              switch (evt.type) {
                case "typing":
                  setTyping(evt.status);
                  break;
                case "message_chunk":
                  appendMessageChunk(evt.content);
                  break;
                case "message":
                  setTyping(false);
                  break;
                case "tool_call":
                  addMessage({
                    id: Math.random().toString(),
                    type: "tool_call",
                    content: `Executing tool: ${evt.tool_name}`,
                    sender: "system",
                    timestamp: new Date().toISOString(),
                    toolName: evt.tool_name,
                    args: evt.args,
                  });
                  break;
                case "error":
                  setTyping(false);
                  addMessage({
                    id: Math.random().toString(),
                    type: "error",
                    content: evt.message,
                    sender: "system",
                    timestamp: new Date().toISOString(),
                  });
                  break;
              }
            } catch {}
          }
        }
      } catch (err: any) {
        console.error("[Chat] Approval error:", err);
      } finally {
        setIsStreaming(false);
        setTyping(false);
        setActiveApproval(null);
      }
    },
    [token, sessionId, addMessage, appendMessageChunk, setTyping, setActiveApproval]
  );

  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
  }, []);

  return { sendMessage, sendApprovalResponse, cancelStream, isStreaming };
}
