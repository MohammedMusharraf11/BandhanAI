import React from "react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen w-full bg-[#0A0A0B] text-[#e5e2e3] relative overflow-hidden flex items-center justify-center">
      {children}
    </div>
  );
}
