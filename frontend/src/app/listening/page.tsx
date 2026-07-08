import type { Metadata } from "next";

import { ListeningDashboard } from "@/components/listening/listening-dashboard";

export const metadata: Metadata = {
  title: "Listening Diagnostics",
};

export default function ListeningPage() {
  return <ListeningDashboard />;
}
