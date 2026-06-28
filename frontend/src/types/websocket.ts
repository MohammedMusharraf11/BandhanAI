export type WSMessageType =
  | "message"
  | "user_message"
  | "message_chunk"
  | "tool_call"
  | "typing"
  | "approval_request"
  | "approval_response"
  | "error"
  | "ping"
  | "pong";

export interface WSMessagePayload {
  type: WSMessageType;
  content?: string;
  timestamp?: string;
  status?: boolean;
  tool_name?: string;
  args?: any;
  data?: any;
  interrupt_id?: string;
}
