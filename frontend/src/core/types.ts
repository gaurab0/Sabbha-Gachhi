import type { OverallState, ProfileStage } from './state'

/** Platform roles. Panjikar and admin are elevated; family roles are not. */
export type Role = 'family' | 'candidate' | 'panjikar' | 'admin'

/**
 * A login identity. Candidates intentionally share a login with their
 * guardian (many are not online often), but the data model keeps them
 * distinct: consent events record the *candidate* as the actor, never the
 * guardian, even though one account serves both.
 */
export interface Account {
  id: string
  role: Role
  /** Family accounts carry both the guardian and candidate names. */
  name: string
  /** Demonstration-only credential; a real deployment would use OTP/magic link. */
  passcode: string
  /** Only on family accounts: the candidate this profile is about. */
  candidateName?: string
  candidateAge?: number
  candidateGender?: 'female' | 'male'
}

/** Who within the family performed an action. */
export type FamilyActor = 'guardian' | 'candidate'

/** Record of an actor class, kept distinct from raw account ids. */
export type Actor = { kind: 'guardian' | 'candidate' } | { kind: 'panjikar' | 'admin'; accountId: string }

export interface GuardianDetails {
  name: string
  relation: 'father' | 'mother' | 'grandfather' | 'grandmother' | 'uncle' | 'elder brother' | 'other guardian'
  phone: string
  email: string
  village: string
  district: string
  inviteCode: string
}

export interface CandidateDetails {
  name: string
  gender: 'female' | 'male'
  age: number
  education: string
  occupation: string
  city: string
  /** Stated preferences used by the rule-based shortlist filter (stage 3). */
  preferences: {
    minAge: number
    maxAge: number
    preferredCities: string[]
    /** Gotras the family will not marry into (gotra + pravara restrictions). */
    excludedGotras: string[]
    notes?: string
  }
}

/**
 * Lineage / genealogy submission (panji record). Ancestors are listed as
 * male-line chains per panji convention; sapinda screening uses these plus
 * maternal-grandmother lines within the prohibited degrees.
 */
export interface LineageRecord {
  id: string
  profileId: string
  gotra: string
  pravara?: string
  shakha?: string
  kul?: string
  village: string
  mula: string
  /** Male-line ancestor chain, eldest first. */
  maleLine: string[]
  /** Maternal grandmother's gotra + village (sapinda relevance). */
  maternalGrandmother: { name: string; gotra: string; village: string }
  submittedAt: string
  /** Verified / flagged / info-requested — visible only to family + panjikar. */
  review: LineageReview
}

export type LineageReviewStatus = 'pending' | 'approved' | 'flagged' | 'info_requested'

export interface LineageReview {
  status: LineageReviewStatus
  reviewerPanjikarId?: string
  note?: string
  requestedInfo?: string
  reviewedAt?: string
}

/** Result of the automated sapinda (close blood-relation) screen — stage 2. */
export interface SapindaResult {
  profileId: string
  screenedAt: string
  conflicts: SapindaConflict[]
  passed: boolean
}

export interface SapindaConflict {
  /** The other profile this profile conflicts with (or `unknown` if within own line). */
  withProfileId: string | 'unknown'
  relation: string
  detail: string
  severity: 'blocked' | 'needs_review'
}

/** The shortlist candidates rule-based filter produced for a profile (stage 3). */
export interface ShortlistEntry {
  candidateProfileId: string
  matchedOn: string[]
  score: number
}

/** A proposed match. Created ONLY by a panjikar — families cannot browse. */
export interface Match {
  id: string
  stage: OverallState
  /** Profile ids of both sides; `a` is the profile that was shortlisted first. */
  sideAProfileId: string
  sideBProfileId: string
  proposedByPanjikarId: string
  proposedAt: string
  /** Panjikar's short rationale shown to both families equally. */
  panjikarNote: string
  /** Per-side consent. A side's decision is NEVER exposed to the other until both exist. */
  consents: Record<'A' | 'B', ConsentState>
  /** What each side is allowed to see of the other once contact opens. */
  contact: ContactChannel | null
  outcome?: MatchOutcome
}

export type MatchOutcome =
  | { kind: 'proceeded'; note?: string }
  | { kind: 'declined'; bySide: 'A' | 'B'; reason?: string }
  | { kind: 'withdrawn'; bySide: 'A' | 'B' }

export type ConsentState =
  | { decided: false }
  | { decided: true; consented: boolean; by: FamilyActor; at: string; reason?: string }

export interface ContactChannel {
  threadId: string
  openedAt: string
  /** Display name each side shows the other — NOT phone/address. */
  displayNames: Record<'A' | 'B', string>
}

export interface Message {
  id: string
  threadId: string
  /** Which side sent it; the receiving family sees "them". */
  side: 'A' | 'B'
  by: FamilyActor
  body: string
  at: string
}

/** Consent / audit event — accountability log, one side's entries hidden from the other. */
export interface ConsentEvent {
  id: string
  matchId: string | null
  profileId: string
  stage: ProfileStage
  action:
    | 'registration_consent'
    | 'panji_submitted'
    | 'panji_reviewed'
    | 'match_proposed'
    | 'match_consent_given'
    | 'match_consent_declined'
    | 'contact_opened'
    | 'withdrawn'
  by: Actor
  at: string
  note?: string
}

export type ConcernStatus = 'open' | 'under_review' | 'resolved' | 'escalated'

export interface Concern {
  id: string
  /** Null when reported from the public (logged-out) form. */
  reporterProfileId: string | null
  reporterName: string
  reporterContact: string
  subject: string
  body: string
  relatedMatchId?: string
  status: ConcernStatus
  filedAt: string
  resolutionNote?: string
}

export type DeletionStatus = 'requested' | 'in_progress' | 'completed' | 'rejected'

export interface DeletionRequest {
  id: string
  profileId: string
  requestedAt: string
  status: DeletionStatus
  completedAt?: string
  adminNote?: string
}

/** Profile = one family unit through the flow. */
export interface Profile {
  id: string
  accountId: string
  guardian: GuardianDetails
  candidate: CandidateDetails
  /** Current stage of the six-step ladder, or a terminal state. */
  stage: OverallState
  /** Required acknowledgement captured during registration — not homepage text. */
  noDowryAcknowledgedAt: string | null
  /** Candidate's own explicit registration consent — distinct from guardian's. */
  candidateRegistrationConsent: { given: boolean; by: FamilyActor; at: string } | null
  lineage: LineageRecord | null
  sapinda: SapindaResult | null
  shortlist: ShortlistEntry[]
  /** Stage history for the family status tracker. */
  history: { stage: ProfileStage; at: string; by: Actor; note?: string }[]
  assignedPanjikarId: string | null
  createdAt: string
  withdrawnAt?: string
}

export interface PlatformData {
  accounts: Account[]
  profiles: Profile[]
  matches: Match[]
  messages: Message[]
  consentEvents: ConsentEvent[]
  concerns: Concern[]
  deletionRequests: DeletionRequest[]
  auditLog: { id: string; at: string; actor: Actor; action: string; targetId?: string }[]
}
