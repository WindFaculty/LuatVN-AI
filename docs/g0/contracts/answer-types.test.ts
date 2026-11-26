import type { components, paths } from "./answer-types";

type Schema = components["schemas"];
type Result = Schema["AnswerResult"];
type Stream = paths["/v1/answers/{id}/events"]["get"]["responses"][200]["content"]["text/event-stream"];
declare const verified: Schema["AnswerWithEvidence"];
declare const failed: Schema["AnswerWithoutEvidence"];
declare const state: Schema["RunState"];
declare const frame: Schema["SseData"];

const verifiedResult: Result = { ...verified, status: "verified" };
const failedResult: Result = { ...failed, status: "failed" };
// @ts-expect-error A verified result requires evidence.
const missingEvidence: Result = { ...verified, evidence: [] };
// @ts-expect-error A failed result has no summary.
const failedWithSummary: Result = { ...failed, status: "failed", summary: "Fixture summary." };

const body: Stream = "event: answer.progress";
if (frame.type === "answer.progress") {
  const stage: Schema["ProgressEvent"]["stage"] = frame.stage;
} else {
  const result: Result = frame.result;
}
if (state.status === "verified" || state.status === "partial") {
  const summary: string = state.summary;
}
