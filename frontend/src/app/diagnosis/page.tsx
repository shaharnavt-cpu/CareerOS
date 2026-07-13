import type { Metadata } from "next";

import { DiagnosisWorkspace } from "@/components/diagnosis/diagnosis-workspace";

export const metadata: Metadata = {
  title: "Career Diagnosis",
};

export default function DiagnosisPage() {
  return <DiagnosisWorkspace />;
}
