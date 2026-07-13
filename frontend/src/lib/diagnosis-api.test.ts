import assert from "node:assert/strict";
import test from "node:test";

import {
  createFeedbackEvent,
  DiagnosisApiError,
  isDuplicateFeedbackError,
} from "./diagnosis-api.ts";

test("feedback API preserves structured duplicate response details", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: {
          code: "DUPLICATE_FEEDBACK_EVENT",
          message: "This looks similar to an existing feedback event.",
          existing_event_id: "existing-feedback-id",
        },
      }),
      {
        status: 409,
        headers: { "Content-Type": "application/json" },
      },
    );

  try {
    await assert.rejects(
      () => createFeedbackEvent({ raw_note: "Repeated feedback note" }),
      (error: unknown) => {
        assert.ok(error instanceof DiagnosisApiError);
        assert.ok(isDuplicateFeedbackError(error));
        assert.equal(error.code, "DUPLICATE_FEEDBACK_EVENT");
        assert.equal(error.existingEventId, "existing-feedback-id");
        return true;
      },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
