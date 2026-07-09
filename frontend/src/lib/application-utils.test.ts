import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  applicationMatchSummary,
  applicationMemoryTypeLabel,
  draftPrimaryMemory,
  draftStatusLabel,
  draftSupportingMemories,
  draftUsesApprovedMemoryOnly,
  draftVariantLabel,
  evidenceCountLabel,
} from "./application-utils.ts";
import type { ApplicationDraft } from "./application-api.ts";

test("application helpers format memory and evidence labels", () => {
  assert.equal(applicationMemoryTypeLabel("SKILL_SET"), "Skill Set");
  assert.equal(evidenceCountLabel(1), "1 evidence reference");
  assert.equal(evidenceCountLabel(3), "3 evidence references");
});

test("application match summary separates approved matches from gaps", () => {
  assert.equal(
    applicationMatchSummary([{ id: "one" }, { id: "two" }], []),
    "CareerOS found 2 relevant memories from approved memory.",
  );
  assert.match(
    applicationMatchSummary([{ id: "one" }], ["Reporting"]),
    /1 gap still need evidence/,
  );
  assert.match(applicationMatchSummary([], []), /No approved memories/);
});

test("draft statuses are user-facing", () => {
  assert.equal(draftStatusLabel("APPROVED"), "Approved");
});

test("draft variants and metadata are user-facing", () => {
  const draft: ApplicationDraft = {
    id: "draft-1",
    opportunity_id: "opp-1",
    draft_type: "QUESTION_ANSWER",
    prompt: "Tell us about a project.",
    draft_text: "A project that prepared me...",
    evidence_ids: ["e1", "e2"],
    status: "DRAFT",
    draft_metadata: {
      uses_approved_memory_only: true,
      primary_memory: {
        id: "memory-1",
        title: "Gas Kinematics Honors Capstone",
        type: "PROJECT",
        evidence_count: 2,
        themes_matched: ["Python"],
      },
      supporting_memories: [
        {
          id: "memory-2",
          title: "Technical Skills",
          type: "SKILL_SET",
          evidence_count: 3,
          themes_matched: ["SQL"],
        },
      ],
    },
    created_at: "2026-07-09T00:00:00Z",
    updated_at: "2026-07-09T00:00:00Z",
  };

  assert.equal(draftVariantLabel("SHORT"), "Short");
  assert.equal(draftVariantLabel("DETAILED"), "Detailed");
  assert.equal(draftUsesApprovedMemoryOnly(draft), true);
  assert.equal(draftPrimaryMemory(draft)?.title, "Gas Kinematics Honors Capstone");
  assert.deepEqual(
    draftSupportingMemories(draft).map((memory) => memory.title),
    ["Technical Skills"],
  );
});

test("application workspace exposes variant, copy, save, and metadata UI", () => {
  const source = readFileSync(
    new URL("../components/applications/application-workspace.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /Draft variant/);
  assert.match(source, /Short/);
  assert.match(source, /Medium/);
  assert.match(source, /Detailed/);
  assert.match(source, /Copy draft/);
  assert.match(source, /Save draft/);
  assert.match(source, /Primary memory/);
  assert.match(source, /approved memory only/);
});
