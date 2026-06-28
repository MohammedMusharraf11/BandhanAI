import React from "react";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={`w-full bg-[#0A0A0B] border border-[#27272A] rounded p-4 text-sm focus:outline-none focus:border-[#E8A020] focus:ring-1 focus:ring-[#E8A020] transition-all text-[#e5e2e3] placeholder-[#d7c3ae]/40 resize-none ${className}`}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";
