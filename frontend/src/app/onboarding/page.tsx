import type { Metadata } from "next";

import { FlowHeader } from "@/components/common/flow-header";
import { OnboardingWorkspace } from "@/components/onboarding/onboarding-workspace";

export const metadata: Metadata = {
  title: "Guided Story",
};

export default function OnboardingPage() {
  return (
    <div className="min-h-screen bg-[#f3f5f0]">
      <FlowHeader current={1} />
      <OnboardingWorkspace />
    </div>
  );
}
