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
  /** Relative URL returned by uploadCandidatePhoto, or "" when none was given. */
  candidate_photo: string;
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

export interface RegistrationStatusResponse {
  reference?: string;
  candidate_name?: string;
  guardian_name?: string;
  verification_status?: "pending" | "verified";
  matches?: MatchProposalResponse[];
  withdrawn?: boolean;
  withdrawn_at?: string | null;
  email_verified?: boolean;
  registration?: unknown;
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

export interface ConcernReportPayload {
  registration_reference_text?: string;
  topic: string;
  description: string;
  contactBack: string;
}

export interface MatchContactResponse {
  photo_url: string;
  email: string;
  phone: string;
}

export const WITHDRAW_REASONS = [
  "Found a match through Sabha Gachhi",
  "Found a match elsewhere",
  "Not ready right now",
  "Other",
] as const;

export type WithdrawReason = (typeof WITHDRAW_REASONS)[number];

// -------------------------------------------------------------- Calls --

export function submitRegistration(payload: RegistrationPayload) {
  return apiRequest<RegistrationCreatedResponse>("/registrations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function uploadCandidatePhoto(file: File) {
  const form = new FormData();
  form.append("photo", file);
  return apiRequest<{ photo_url: string }>("/registrations/photo/", {
    method: "POST",
    body: form,
  });
}

export function fetchMyRegistrationStatus() {
  return apiRequest<RegistrationStatusResponse>("/registrations/me/status/");
}

export function withdrawMyRegistration(reason?: string) {
  return apiRequest<void>("/registrations/me/withdraw/", {
    method: "POST",
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

export function fetchMatchProposal(matchId: string) {
  return apiRequest<MatchProposalResponse>(`/match-proposals/${matchId}/`);
}

export function fetchMatchContact(matchId: string) {
  return apiRequest<MatchContactResponse>(`/match-proposals/${matchId}/contact/`);
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

export interface StatusCheckResponse {
  verified: boolean;
  match_found: boolean;
  match_count: number;
  stage: "pending_verification" | "verified_awaiting_match" | "matched";
}

export function submitConcernReport(payload: ConcernReportPayload) {
  const { registration_reference_text: _registration_reference_text, ...rest } = payload;
  return apiRequest<{ received: boolean }>("/concern-reports/", {
    method: "POST",
    body: JSON.stringify(rest),
  });
}

export function checkStatusByToken(token: string) {
  return apiRequest<StatusCheckResponse>("/status/check/", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}
