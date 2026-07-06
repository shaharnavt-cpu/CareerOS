import type { Metadata } from "next";

import { StoryWorkspace } from "@/components/stories/story-workspace";

export const metadata: Metadata = {
  title: "Career Stories",
};

export default function StoriesPage() {
  return <StoryWorkspace />;
}
