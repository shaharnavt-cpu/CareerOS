import assert from "node:assert/strict";
import test from "node:test";

import {
  applicationMatchSummary,
  applicationMemoryTypeLabel,
  draftStatusLabel,
  evidenceCountLabel,
} from "./application-utils.ts";

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
