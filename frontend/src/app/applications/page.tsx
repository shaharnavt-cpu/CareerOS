import type { Metadata } from "next";

import { ApplicationWorkspace } from "@/components/applications/application-workspace";

export const metadata: Metadata = {
  title: "Application Intelligence",
};

export default function ApplicationsPage() {
  return <ApplicationWorkspace />;
}
