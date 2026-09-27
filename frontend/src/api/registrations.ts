// Re-export all registration API calls from the shared registration module.
export {
  submitRegistration,
  fetchMyRegistrationStatus,
  withdrawMyRegistration,
  fetchMatchProposal,
  respondToMatchProposal,
  submitConcernReport,
  type RegistrationPayload,
  type RegistrationCreatedResponse,
  type RegistrationStatusResponse,
  type MatchProposalResponse,
  type ConcernReportPayload,
} from "./registration";
