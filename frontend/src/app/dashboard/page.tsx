import type { Metadata } from "next";

import { FlowHeader } from "@/components/common/flow-header";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";

export const metadata: Metadata = {
  title: "Profile dashboard",
};

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#f6f7f2]">
      <FlowHeader current={3} />
      <DashboardShell />
    </div>
  );
}
