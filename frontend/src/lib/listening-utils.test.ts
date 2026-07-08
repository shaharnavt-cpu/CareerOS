import assert from "node:assert/strict";
import test from "node:test";

import {
  evidenceCategoryLabel,
  friendlyFailureMessage,
  listeningStageLabel,
  mergeById,
  nextListeningStep,
  replacePendingById,
  validateListeningAttachments,
} from "./listening-utils.ts";

test("mergeById keeps prior proposals and replaces matching ids", () => {
  const result = mergeById(
    [
      { id: "one", value: "old" },
      { id: "two", value: "kept" },
    ],
    [{ id: "one", value: "new" }],
  );

  assert.deepEqual(result, [
    { id: "one", value: "new" },
    { id: "two", value: "kept" },
  ]);
});

test("listening progress stops at its final user-facing stage", () => {
  assert.equal(nextListeningStep(0, 5), 1);
  assert.equal(nextListeningStep(4, 5), 4);
});

test("evidence labels prefer extracted category and format source fallback", () => {
  assert.equal(
    evidenceCategoryLabel({ category: "EDUCATION", source_type: "RESUME" }),
    "EDUCATION",
  );
  assert.equal(
    evidenceCategoryLabel({ source_type: "GENERIC_DOCUMENT" }),
    "GENERIC DOCUMENT",
  );
});

test("a fresh multi-source pass replaces stale pending proposals", () => {
  const proposal = (id: string, approval_state: string) => ({ id, approval_state });
  const result = replacePendingById(
    [proposal("old", "NEEDS_REVIEW"), proposal("kept", "CANONICAL")],
    [proposal("fused", "NEEDS_REVIEW")],
  );

  assert.deepEqual(
    result.map((item) => item.id),
    ["kept", "fused"],
  );
});

test("composer accepts supported multiple attachments without manual classification", () => {
  const files = [
    { name: "resume.pdf", size: 1200 },
    { name: "transcript.docx", size: 2400 },
    { name: "projects.csv", size: 800 },
  ] as File[];

  assert.equal(validateListeningAttachments(files), null);
  assert.match(
    validateListeningAttachments([
      { name: "headshot.png", size: 200 } as File,
    ]) ?? "",
    /isn’t supported yet/,
  );
});

test("queue progress uses clear user-facing stage labels", () => {
  assert.equal(listeningStageLabel("UPLOAD"), "Uploaded");
  assert.equal(
    listeningStageLabel("PERSIST_EVIDENCE"),
    "Saving to Career Memory",
  );
  assert.equal(listeningStageLabel("GENERATE_PROPOSALS"), "Generating proposals");
});

test("database failures explain that parsed evidence is retained", () => {
  assert.match(friendlyFailureMessage("DATABASE_TIMEOUT"), /document is safe/i);
  assert.match(
    friendlyFailureMessage("DATABASE_CONSTRAINT_FAILURE"),
    /document is safe/i,
  );
  assert.match(friendlyFailureMessage("PERSISTENCE_FAILURE"), /can be retried/i);
  assert.match(friendlyFailureMessage("NO_TEXT_FOUND"), /scanned document/i);
});
