import assert from "node:assert/strict";
import test from "node:test";

import type { CareerStory } from "./story-api.ts";
import {
  activeStories,
  canSplitStory,
  coreExperiences,
  replaceStory,
} from "./story-utils.ts";

function story(id: string, status: CareerStory["status"] = "PROPOSED") {
  return {
    id,
    title: `Story ${id}`,
    summary: "Summary",
    primary_goal: null,
    transformation: null,
    confidence: 0.8,
    status,
    chapters: [],
    evidence: [],
    memberships: [
      {
        id: `${id}-experience`,
        entity_type: "EXPERIENCE" as const,
        entity_id: "entity-1",
        chapter_id: null,
        label: "Researcher",
        organization: "Lab",
        role: "CORE_EXPERIENCE",
        rationale: "Shared research theme.",
        confidence: 0.9,
      },
      {
        id: `${id}-skill`,
        entity_type: "SKILL" as const,
        entity_id: "entity-2",
        chapter_id: null,
        label: "Python",
        organization: null,
        role: "RELATED_ENTITY",
        rationale: "Used in the experience.",
        confidence: 0.8,
      },
    ],
    created_at: "2026-07-06T00:00:00Z",
    updated_at: "2026-07-06T00:00:00Z",
    approved_at: null,
  } satisfies CareerStory;
}

test("story helpers identify experiences and valid split selections", () => {
  const value = story("one");
  assert.equal(coreExperiences(value).length, 1);
  assert.equal(canSplitStory(value, new Set(["one-experience"])), true);
  assert.equal(
    canSplitStory(value, new Set(["one-experience", "one-skill"])),
    false,
  );
});

test("story helpers replace records and hide closed stories", () => {
  const original = story("one");
  const updated = { ...original, summary: "Edited" };
  assert.equal(replaceStory([original], updated)[0].summary, "Edited");
  assert.deepEqual(
    activeStories([original, story("two", "ARCHIVED")]).map((item) => item.id),
    ["one"],
  );
});
