import type { CareerStory, StoryMembership } from "@/lib/story-api";

export function coreExperiences(story: CareerStory): StoryMembership[] {
  return story.memberships.filter(
    (membership) => membership.entity_type === "EXPERIENCE",
  );
}

export function canSplitStory(
  story: CareerStory,
  selectedMembershipIds: ReadonlySet<string>,
): boolean {
  const selected = story.memberships.filter((membership) =>
    selectedMembershipIds.has(membership.id),
  ).length;
  return selected > 0 && selected < story.memberships.length;
}

export function replaceStory(
  stories: CareerStory[],
  updated: CareerStory,
): CareerStory[] {
  return stories.map((story) => (story.id === updated.id ? updated : story));
}

export function activeStories(stories: CareerStory[]): CareerStory[] {
  return stories.filter(
    (story) => story.status !== "ARCHIVED" && story.status !== "REJECTED",
  );
}
