import { apiRequest } from "./client";

// ---------------------------------------------------------------- Types --

export interface RegistrationPayload {
  language: "en" | "hi" | "mai";
  guardian_name: string;
  guardian_relation_to_candidate: string;
  guardian_village: string;
  guardian_district: string;
  guardian_phone: string;
  guardian_email: string;
  candidate_full_name: string;
  candidate_gender: string;
  candidate_dob: string;
  candidate_education: string;
  candidate_occupation: string;
  candidate_current_city: string;
  preferred_age_min: number | null;
  preferred_age_max: number | null;
  preferred_location: string;
  preferred_education: string;
  gotra: string;
  mool_gram: string;
  paternal_line: { label: string; name: string }[];
  maternal_line: { label: string; name: string }[];
  consent_choice: string;
  consent_own_words: string;
}

export interface RegistrationCreatedResponse {
  reference: string;
  created_at: string;
}

export interface MatchProposalResponse {
  id: number;
  shared_by_panjikar: string;
  proposed_on: string;
  shared_details: string[];
  your_response: "pending" | "accepted" | "declined";
  other_response: "pending" | "accepted" | "declined";
  state: "waiting_you" | "waiting_other" | "both_accepted" | "declined";
  contact_guardian_name: string;
  contact_phone: string;
  contact_email: string;
}

export interface RegistrationStatusResponse {
  reference: string;
  candidate_name: string;
  guardian_name: string;
  verification_status: "pending" | "verified";
  match: MatchProposalResponse | null;
}

export interface ConcernReportPayload {
  registration_reference_text: string;
  topic: string;
  description: string;
  contact_back: string;
}

// -------------------------------------------------------------- Calls --

export function submitRegistration(payload: RegistrationPayload) {
  return apiRequest<RegistrationCreatedResponse>("/registrations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchRegistrationStatus(reference: string) {
  return apiRequest<RegistrationStatusResponse>(
    `/registrations/${reference}/status/`
  );
}

export function withdrawRegistration(reference: string) {
  return apiRequest<void>(`/registrations/${reference}/withdraw/`, {
    method: "POST",
  });
}

export function fetchMatchProposal(matchId: string) {
  return apiRequest<MatchProposalResponse>(`/match-proposals/${matchId}/`);
}

export function respondToMatchProposal(
  matchId: string,
  action: "accept" | "decline"
) {
  return apiRequest<MatchProposalResponse>(
    `/match-proposals/${matchId}/respond/`,
    {
      method: "POST",
      body: JSON.stringify({ action }),
    }
  );
}

export function submitConcernReport(payload: ConcernReportPayload) {
  return apiRequest<{ received: boolean }>("/concern-reports/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}