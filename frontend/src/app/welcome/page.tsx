import type { Metadata } from "next";

import { WelcomeScreen } from "@/components/onboarding/welcome-screen";

export const metadata: Metadata = {
  title: "Welcome",
};

export default function WelcomePage() {
  return <WelcomeScreen />;
}
