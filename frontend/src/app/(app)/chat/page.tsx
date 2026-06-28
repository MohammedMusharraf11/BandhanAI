"use client";

import React, { useState, useEffect, useRef } from "react";
import { useChat } from "@/hooks/use-chat";
import { useChatStore } from "@/store/chat-store";
import { useTenantStore } from "@/store/tenant-store";
import {
  Ban,
  CheckCircle2,
  Database,
  Edit3,
  MessageSquareText,
  Paperclip,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";

export default function ChatPage() {
  const { messages, typing, activeApproval, clearMessages, setActiveApproval } = useChatStore();
  const { agentName } = useTenantStore();

  // Generate a persistent local session_id or use user sub to scope state
  const [sessionId] = useState(() => Math.random().toString(36).substring(7));
  const { sendMessage, sendApprovalResponse, isStreaming } = useChat(sessionId);

  const [inputVal, setInputVal] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Approval modal states
  const [rejectFeedback, setRejectFeedback] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editDataStr, setEditDataStr] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  // Scroll thread to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    sendMessage(inputVal);
    setInputVal("");
  };

  const handleApprove = () => {
    sendApprovalResponse("continue");
    setActiveApproval(null);
  };

  const handleOpenEdit = () => {
    if (activeApproval && activeApproval.data) {
      setEditDataStr(JSON.stringify(activeApproval.data.tool_call?.args || {}, null, 2));
      setIsEditing(true);
    }
  };

  const handleSaveEdit = () => {
    try {
      // Validate JSON
      JSON.parse(editDataStr);
      sendApprovalResponse("update", editDataStr);
      setIsEditing(false);
      setActiveApproval(null);
    } catch {
      alert("Invalid JSON format. Please check syntax.");
    }
  };

  const handleRejectSubmit = () => {
    if (!rejectFeedback.trim()) return;
    sendApprovalResponse("feedback", rejectFeedback);
    setRejectFeedback("");
    setShowRejectForm(false);
    setActiveApproval(null);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-[#0A0A0B] relative">
      {/* Workspace Sub Header */}
      <div className="h-12 bg-[#0A0A0B] border-b border-[#27272A] flex justify-between items-center px-6 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-[#E8A020] rounded-full animate-pulse" />
          <span className="font-data-mono text-[10px] text-[#d7c3ae] uppercase font-bold tracking-wider">
            Connected Session: {sessionId.toUpperCase()}
          </span>
        </div>
        <button
          onClick={clearMessages}
          className="text-xs text-[#ffb4ab] hover:underline font-medium cursor-pointer"
        >
          Clear History
        </button>
      </div>

      {/* Message Thread Scroll View */}
      <div className="flex-grow overflow-y-auto p-6 space-y-6 max-w-5xl mx-auto w-full custom-scrollbar">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-50">
            <MessageSquareText className="h-10 w-10 text-[#E8A020]" />
            <p className="font-body-base text-sm text-[#d7c3ae]">
              Initialize conversation. Say hello to {agentName}!
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.type === "tool_call") {
            // Render Technical Tool Call Card
            return (
              <div key={i} className="flex justify-start ml-12 max-w-[60%]">
                <div className="w-full bg-[#0e0e0f] border border-[#27272A] rounded-lg overflow-hidden transition-all duration-300">
                  <div className="bg-[#201f20] px-3 py-2 flex items-center gap-2 border-b border-[#27272A]">
                    <Database className="h-4 w-4 text-[#E8A020]" />
                    <span className="font-data-mono text-[10px] uppercase tracking-tight text-[#e5e2e3]">
                      Executing: {msg.toolName}...
                    </span>
                  </div>
                  {msg.args && (
                    <pre className="p-3 font-data-mono text-[10px] text-[#6A9E6A] overflow-x-auto bg-[#0A0A0B]/80 max-h-[160px]">
                      {JSON.stringify(msg.args, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            );
          }

          const isUser = msg.sender === "user";
          return (
            <div
              key={i}
              className={`flex gap-4 max-w-[80%] ${isUser ? "flex-row-reverse ml-auto" : ""}`}
            >
              {/* Avatar circle */}
              <div
                className={`w-8 h-8 rounded flex-shrink-0 flex items-center justify-center font-bold text-xs ${
                  isUser
                    ? "bg-[#E8A020]/10 border border-[#E8A020]/20 text-[#E8A020]"
                    : "bg-[#3ac2ff]/10 border border-[#3ac2ff]/20 text-[#3ac2ff]"
                }`}
              >
                {isUser ? "ME" : agentName.substring(0, 1).toUpperCase()}
              </div>

              {/* Message box */}
              <div className={`space-y-1 ${isUser ? "text-right" : ""}`}>
                <div className={`text-[10px] font-bold ${isUser ? "text-[#E8A020]" : "text-[#3ac2ff]"}`}>
                  {isUser ? "You" : agentName}
                </div>
                <div
                  className={`p-3 rounded-lg text-sm leading-relaxed ${
                    isUser
                      ? "bg-[#1c1b1c] border-r-2 border-[#E8A020] text-left"
                      : "bg-[#111113] border-l-2 border-[#3ac2ff]"
                  }`}
                >
                  <p className="whitespace-pre-line text-[#e5e2e3] font-body-base">{msg.content}</p>
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing indicator bubble */}
        {typing && (
          <div className="flex gap-4 max-w-[80%]">
            <div className="w-8 h-8 rounded bg-[#3ac2ff]/10 border border-[#3ac2ff]/20 flex items-center justify-center text-[#3ac2ff] font-bold text-xs">
              {agentName.substring(0, 1).toUpperCase()}
            </div>
            <div className="bg-[#1c1b1c] px-4 py-3 rounded-full flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-[#d7c3ae] rounded-full animate-bounce delay-75" />
              <span className="w-1.5 h-1.5 bg-[#d7c3ae] rounded-full animate-bounce delay-150" />
              <span className="w-1.5 h-1.5 bg-[#d7c3ae] rounded-full animate-bounce delay-300" />
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input Form Panel */}
      <div className="p-4 border-t border-[#27272A] bg-[#0e0e0f] flex-shrink-0">
        <form onSubmit={handleSend} className="max-w-5xl mx-auto relative flex items-center w-full">
          <div className="flex-1 bg-[#111113] border border-[#27272A] rounded-lg flex items-center px-4 py-2 focus-within:ring-1 focus-within:ring-[#E8A020] transition-shadow">
            <button
              type="button"
              className="mr-3 text-[#d7c3ae]/40 hover:text-[#E8A020] transition-colors cursor-pointer"
              aria-label="Attach file"
            >
              <Paperclip className="h-4 w-4" />
            </button>
            <input
              className="flex-1 bg-transparent border-none focus:ring-0 text-sm text-[#e5e2e3] placeholder-[#d7c3ae]/40"
              placeholder={`Send message to ${agentName}...`}
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
            />
            <button
              type="submit"
              className="bg-[#E8A020] text-[#291800] p-1.5 rounded-lg hover:brightness-110 active:scale-[0.95] transition-all flex items-center justify-center cursor-pointer"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </form>
      </div>

      {/* 🚨 HUMAN-IN-THE-LOOP APPROVAL MODAL OVERLAY 🚨 */}
      {activeApproval && activeApproval.data && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm px-4">
          <div className="w-full max-w-[640px] bg-[#0e0e0f] border border-[#27272A] shadow-2xl rounded-xl overflow-hidden flex flex-col max-h-[85vh]">
            
            {/* Header */}
            <div className="px-6 py-4 border-b border-[#27272A] flex items-center justify-between bg-[#1c1b1c]">
              <div className="flex items-center gap-3">
                <span className="w-2.5 h-2.5 bg-[#E8A020] rounded-full animate-ping" />
                <h2 className="font-bold text-[#e5e2e3]">Human Verification Required</h2>
              </div>
              <button
                onClick={() => setActiveApproval(null)}
                className="text-[#d7c3ae] hover:text-[#e5e2e3] transition-colors"
                type="button"
                aria-label="Close approval modal"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Scrollable Content Body */}
            <div className="flex-grow overflow-y-auto p-6 space-y-4 custom-scrollbar">
              <div className="flex items-center gap-2">
                <span className="font-data-mono text-[10px] px-2 py-0.5 bg-[#E8A020]/10 text-[#E8A020] border border-[#E8A020]/20 rounded font-bold">
                  ACTION: {activeApproval.data.tool_call?.name.toUpperCase()}
                </span>
                <span className="font-data-mono text-[10px] px-2 py-0.5 bg-[#353436] text-[#d7c3ae] border border-[#27272A] rounded">
                  ID: {activeApproval.interruptId?.substring(0, 8).toUpperCase()}
                </span>
              </div>

              {/* Show edit panel vs read-only preview */}
              {isEditing ? (
                <div className="space-y-2">
                  <label className="block font-label-caps text-label-caps text-[#d7c3ae] uppercase">
                    Modify Arguments JSON
                  </label>
                  <textarea
                    className="w-full bg-[#0A0A0B] border border-[#27272A] rounded p-4 font-data-mono text-xs text-[#e5e2e3] focus:outline-none focus:border-[#E8A020] focus:ring-1 focus:ring-[#E8A020] resize-none h-[220px]"
                    value={editDataStr}
                    onChange={(e) => setEditDataStr(e.target.value)}
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1.5 border border-[#27272A] text-xs font-semibold rounded"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveEdit}
                      className="px-4 py-1.5 bg-[#E8A020] text-[#291800] text-xs font-bold rounded hover:opacity-90"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Subject preview */}
                  {activeApproval.data.tool_call?.args?.subject && (
                    <div className="space-y-1">
                      <label className="block font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase text-[10px]">
                        SUBJECT LINE
                      </label>
                      <div className="p-3 bg-[#1c1b1c] border border-[#27272A] rounded text-sm text-[#e5e2e3] font-semibold">
                        {activeApproval.data.tool_call.args.subject}
                      </div>
                    </div>
                  )}

                  {/* Body Preview */}
                  {activeApproval.data.tool_call?.args?.body && (
                    <div className="space-y-1">
                      <label className="block font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase text-[10px]">
                        HTML PREVIEW
                      </label>
                      <div className="border border-[#27272A] rounded-lg overflow-hidden bg-[#18181B]">
                        <div className="h-8 bg-[#111113] border-b border-[#27272A] flex items-center px-3 gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500/50" />
                          <span className="w-1.5 h-1.5 rounded-full bg-yellow-500/50" />
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500/50" />
                        </div>
                        <div className="h-[200px] overflow-y-auto p-4 bg-white text-gray-800 text-xs custom-scrollbar">
                          <div
                            dangerouslySetInnerHTML={{
                              __html: activeApproval.data.tool_call.args.body,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Non-HTML text payload args preview */}
                  {!activeApproval.data.tool_call?.args?.body && (
                    <div className="space-y-1">
                      <label className="block font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase text-[10px]">
                        PROPOSED PARAMETERS
                      </label>
                      <pre className="p-4 bg-[#111113] border border-[#27272A] rounded font-data-mono text-xs text-[#6A9E6A] overflow-x-auto max-h-[220px]">
                        {JSON.stringify(activeApproval.data.tool_call?.args, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Reject / Feedback input */}
              {showRejectForm ? (
                <div className="bg-[#1c1b1c] p-4 border border-[#27272A] rounded space-y-2 animate-in slide-in-from-top-2 duration-300">
                  <label className="block font-label-caps text-label-caps text-[#ffb4ab] uppercase text-[10px]">
                    Feedback to Agent (Reason for rejection)
                  </label>
                  <textarea
                    required
                    placeholder="Provide comments (e.g. 'Use a more warm tone' or 'Wait until Q4')"
                    className="w-full bg-[#0A0A0B] border border-[#27272A] rounded p-2 text-xs text-[#e5e2e3] focus:outline-none focus:border-[#ffb4ab] resize-none h-20"
                    value={rejectFeedback}
                    onChange={(e) => setRejectFeedback(e.target.value)}
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setShowRejectForm(false)}
                      className="px-3 py-1 border border-[#27272A] text-xs font-semibold text-[#d7c3ae]"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleRejectSubmit}
                      className="px-4 py-1 bg-red-500/20 text-[#ffb4ab] border border-red-500/40 text-xs font-bold rounded hover:bg-red-500/30"
                    >
                      Send Feedback
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-3 p-3 bg-[#111113] border-l-2 border-[#E8A020]">
                  <ShieldCheck className="h-4 w-4 shrink-0 text-[#E8A020]" />
                  <p className="text-xs text-[#d7c3ae] leading-relaxed">
                    Review and edit the action parameters. Approving triggers the campaign sequence.
                  </p>
                </div>
              )}
            </div>

            {/* Actions Footer */}
            {!isEditing && !showRejectForm && (
              <div className="px-6 py-4 bg-[#1c1b1c] border-t border-[#27272A] flex justify-end gap-3 flex-shrink-0">
                <button
                  onClick={() => setShowRejectForm(true)}
                  className="px-4 py-2 border border-[#27272A] text-[#ffb4ab] font-medium hover:bg-red-500/10 transition-all rounded text-xs flex items-center gap-2 cursor-pointer"
                >
                  <Ban className="h-4 w-4" />
                  Reject
                </button>
                <button
                  onClick={handleOpenEdit}
                  className="px-4 py-2 border border-[#27272A] text-[#e5e2e3] font-medium hover:bg-[#353436] transition-all rounded text-xs flex items-center gap-2 cursor-pointer"
                >
                  <Edit3 className="h-4 w-4" />
                  Modify
                </button>
                <button
                  onClick={handleApprove}
                  className="px-6 py-2 bg-[#E8A020] text-[#291800] font-bold hover:brightness-110 transition-all rounded text-xs flex items-center gap-2 cursor-pointer animate-pulse"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Approve & Execute
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
