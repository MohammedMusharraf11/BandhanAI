import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={`w-full bg-[#0A0A0B] border border-[#27272A] rounded p-3 text-sm focus:outline-none focus:border-[#E8A020] focus:ring-1 focus:ring-[#E8A020] transition-all text-[#e5e2e3] placeholder-[#d7c3ae]/40 ${className}`}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";
