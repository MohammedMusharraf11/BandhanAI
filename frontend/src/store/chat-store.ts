import { create } from "zustand";

export interface ChatMessage {
  id: string;
  type: "user_message" | "message" | "message_chunk" | "tool_call" | "typing" | "error" | "approval_request";
  content: string;
  sender: "user" | "agent" | "system";
  timestamp: string;
  toolName?: string;
  args?: any;
  data?: any;
  interruptId?: string;
}

interface ChatState {
  messages: ChatMessage[];
  typing: boolean;
  activeApproval: ChatMessage | null;
  addMessage: (message: ChatMessage) => void;
  appendMessageChunk: (chunk: string) => void;
  setTyping: (typing: boolean) => void;
  setActiveApproval: (approval: ChatMessage | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  typing: false,
  activeApproval: null,
  addMessage: (message) =>
    set((state) => {
      // Remove any existing duplicate message IDs
      const filtered = state.messages.filter((m) => m.id !== message.id);
      return { messages: [...filtered, message] };
    }),
  appendMessageChunk: (chunk) =>
    set((state) => {
      const messages = [...state.messages];
      const lastMsg = messages[messages.length - 1];
      
      if (lastMsg && (lastMsg.type === "message_chunk" || lastMsg.type === "message")) {
        lastMsg.content += chunk;
        lastMsg.type = "message_chunk"; // Keep type as chunk during streaming
        return { messages };
      } else {
        const newMsg: ChatMessage = {
          id: Math.random().toString(),
          type: "message_chunk",
          content: chunk,
          sender: "agent",
          timestamp: new Date().toISOString(),
        };
        return { messages: [...messages, newMsg] };
      }
    }),
  setTyping: (typing) => set({ typing }),
  setActiveApproval: (activeApproval) => set({ activeApproval }),
  clearMessages: () => set({ messages: [], activeApproval: null, typing: false }),
}));
