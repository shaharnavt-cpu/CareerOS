import type { Metadata } from "next";

import { FlowHeader } from "@/components/common/flow-header";
import { ReviewWorkspace } from "@/components/review/review-workspace";

export const metadata: Metadata = {
  title: "Review your knowledge",
};

export default function ReviewPage() {
  return (
    <div className="min-h-screen bg-[#f6f7f2]">
      <FlowHeader current={2} />
      <ReviewWorkspace />
    </div>
  );
}
