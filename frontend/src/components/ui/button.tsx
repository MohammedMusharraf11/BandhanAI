import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`px-4 py-2 bg-[#E8A020] text-[#291800] rounded font-bold hover:brightness-110 active:scale-[0.98] transition-all text-xs cursor-pointer ${className}`}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
