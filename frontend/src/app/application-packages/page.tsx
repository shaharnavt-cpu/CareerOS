import type { Metadata } from "next";

import { ApplicationPackageWorkspace } from "@/components/application-packages/application-package-workspace";

export const metadata: Metadata = {
  title: "Application Package Builder",
};

export default function ApplicationPackagesPage() {
  return <ApplicationPackageWorkspace />;
}
