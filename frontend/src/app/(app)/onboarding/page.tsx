"use client";

import OnboardingFlow from "@/components/onboarding/onboarding-flow";

export default function OnboardingPage() {
  return (
    <div className="flex w-full min-h-screen bg-[#0A0A0B] text-[#e5e2e3]">
      <main className="flex-grow flex flex-col items-center justify-center p-6 relative">
        <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-20 z-0">
          <div className="absolute -top-1/2 -left-1/4 w-full h-full bg-[radial-gradient(circle_at_center,#E8A020_0%,transparent_70%)] blur-[120px]" />
        </div>
        <OnboardingFlow />
      </main>
    </div>
  );
}
