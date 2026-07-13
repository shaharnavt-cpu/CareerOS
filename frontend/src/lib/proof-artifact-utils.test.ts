import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  buildProofArtifactHref,
  proofArtifactStatusLabel,
  proofArtifactTypeLabel,
  proofAudienceLabel,
  proofReadinessLabel,
  proofVariantText,
} from "./proof-artifact-utils.ts";

test("proof artifact labels are calm and user-facing", () => {
  assert.equal(proofArtifactTypeLabel("CASE_STUDY"), "Case study");
  assert.equal(
    proofAudienceLabel("APPLICATION_UPLOAD"),
    "Optional application upload",
  );
  assert.equal(proofReadinessLabel("STRONG_DRAFT"), "Strong draft");
  assert.equal(proofArtifactStatusLabel("READY"), "Ready");
});

test("diagnosis prefill URL preserves memory, result, and target role", () => {
  assert.equal(
    buildProofArtifactHref({
      sourceMemoryId: "memory-1",
      sourceDiagnosisResultId: "result-1",
      targetRole: "Data Analytics / AI internship",
    }),
    "/proof-artifacts?source_memory_id=memory-1&source_diagnosis_result_id=result-1&target_role=Data+Analytics+%2F+AI+internship",
  );
  assert.equal(buildProofArtifactHref({}), "/proof-artifacts");
});

test("supporting variants become copy-ready plain text", () => {
  assert.equal(
    proofVariantText(["First evidence-backed bullet", "Second bullet"]),
    "- First evidence-backed bullet\n- Second bullet",
  );
  assert.equal(proofVariantText("One outreach paragraph"), "One outreach paragraph");
  assert.equal(proofVariantText({ unsupported: true }), "");
});

test("proof artifact route and workspace expose the complete v0 flow", () => {
  const route = readFileSync(
    new URL("../app/proof-artifacts/page.tsx", import.meta.url),
    "utf8",
  );
  const workspace = readFileSync(
    new URL(
      "../components/proof-artifacts/proof-artifact-workspace.tsx",
      import.meta.url,
    ),
    "utf8",
  );

  assert.match(route, /ProofArtifactWorkspace/);
  assert.match(route, /searchParams: Promise/);
  assert.match(route, /source_memory_id/);
  assert.match(route, /source_diagnosis_result_id/);
  assert.match(route, /target_role/);
  assert.match(workspace, /Approved memory/);
  assert.match(workspace, /Approve career memories before building a proof artifact/);
  assert.match(workspace, /Generate proof artifact/);
  assert.match(workspace, /One-page artifact preview/);
  assert.match(workspace, /Evidence used/);
  assert.match(workspace, /What not to claim/);
  assert.match(workspace, /Readiness assessment/);
  assert.match(workspace, /Outcome signals · not canonical proof/);
  assert.match(workspace, /Edit generated text/);
  assert.match(workspace, /Save version edits/);
  assert.match(workspace, /Mark as ready/);
  assert.match(workspace, /Archive/);
  assert.match(workspace, /Copy case study/);
  assert.match(workspace, /Resume bullets/);
  assert.match(workspace, /Outreach blurb/);
  assert.match(workspace, /label={`Copy \$\{label\.toLowerCase\(\)\}`}/);
  assert.match(workspace, /Open print view/);
});

test("print route offers a clean browser PDF path", () => {
  const route = readFileSync(
    new URL("../app/proof-artifacts/[id]/print/page.tsx", import.meta.url),
    "utf8",
  );
  const view = readFileSync(
    new URL(
      "../components/proof-artifacts/proof-artifact-print-view.tsx",
      import.meta.url,
    ),
    "utf8",
  );
  const styles = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

  assert.match(route, /ProofArtifactPrintView/);
  assert.match(view, /Print or save as PDF/);
  assert.match(view, /window\.print\(\)/);
  assert.match(styles, /@media print/);
  assert.match(styles, /@page/);
  assert.match(styles, /proof-print-actions/);
});

test("navigation, dashboard, and diagnosis connect to Proof", () => {
  const navigation = readFileSync(
    new URL("../components/common/workspace-nav.tsx", import.meta.url),
    "utf8",
  );
  const flowHeader = readFileSync(
    new URL("../components/common/flow-header.tsx", import.meta.url),
    "utf8",
  );
  const dashboard = readFileSync(
    new URL("../components/dashboard/dashboard-shell.tsx", import.meta.url),
    "utf8",
  );
  const diagnosis = readFileSync(
    new URL(
      "../components/diagnosis/diagnosis-workspace.tsx",
      import.meta.url,
    ),
    "utf8",
  );

  assert.match(navigation, /href: "\/proof-artifacts", label: "Proof"/);
  assert.match(flowHeader, /href="\/proof-artifacts"/);
  assert.match(dashboard, /Build a proof artifact/);
  assert.match(dashboard, /href: "\/proof-artifacts"/);
  assert.match(diagnosis, /Build this artifact/);
  assert.match(diagnosis, /sprint\.evidence_to_strengthen\[0\]/);
  assert.match(diagnosis, /sourceDiagnosisResultId: result\.id/);
  assert.match(diagnosis, /buildProofArtifactHref/);
});
