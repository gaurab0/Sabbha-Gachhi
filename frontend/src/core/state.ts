/**
 * The six-stage match state machine — the single source of truth for the
 * entire platform. Nothing is browsable, nothing is public: a match can only
 * move forward through these explicit transitions, and every transition is
 * gated server-side (enforced again in `store.ts` actions, never trusted
 * from the client).
 */

/** Sequential stages of a match between two verified families. */
export const MATCH_STAGES = [
  'registered', // 1. family profile registered; candidate consent captured
  'panji_verified', // 2. automated sapinda (close blood-relation) screening passed
  'shortlisted', // 3. rule-based preference filter narrowed candidates
  'introduced', // 4. panjikar manually proposed a specific match to both families
  'consent_pending', // 5. one or both families responded; other side's decision hidden
  'mutually_consented' // 6. both consented — contact channel unlocked
] as const

export type MatchStage = (typeof MATCH_STAGES)[number]

/**
 * Profile lifecycle. A family profile itself moves `registered →
 * panji_verified → shortlisted` while awaiting introduction, then rides the
 * match stage once a proposal exists. `declined` / `withdrawn` are terminal
 * and can be entered from any step (declined = said no to a proposal,
 * withdrawn = family ended contact on their own, no justification needed).
 */
export const PROFILE_STAGES = [
  'registered',
  'panji_verified',
  'shortlisted',
  'introduced',
  'consent_pending',
  'mutually_consented'
] as const

export type ProfileStage = (typeof PROFILE_STAGES)[number]

export type TerminalState = 'declined' | 'withdrawn'
export type OverallState = ProfileStage | TerminalState

export const TERMINAL_STATES: readonly TerminalState[] = ['declined', 'withdrawn']

export function isTerminal(state: OverallState): state is TerminalState {
  return (TERMINAL_STATES as readonly string[]).includes(state)
}

/** Ordered index of a stage — used to gate "can I act at this stage?" checks. */
export function stageIndex(stage: OverallState): number {
  return (PROFILE_STAGES as readonly string[]).indexOf(stage)
}

/** True when `current` has reached at least `required` (false for terminal). */
export function hasReached(current: OverallState, required: ProfileStage): boolean {
  if (isTerminal(current)) return false
  return stageIndex(current) >= stageIndex(required)
}

/**
 * Explicit forward transitions of the six-stage ladder. `declined` and
 * `withdrawn` are reachable from every stage (see `canEnterTerminal`) but are
 * not listed as forward targets — they are terminal exits, not steps.
 * There is deliberately no transition that skips the panjikar (stage 4 is
 * human-only) or that skips candidate consent (stage 1 requires it).
 */
export const TRANSITIONS: Readonly<Record<ProfileStage, readonly ProfileStage[]>> = {
  registered: ['panji_verified'],
  panji_verified: ['shortlisted'],
  shortlisted: ['introduced'],
  introduced: ['consent_pending'],
  consent_pending: ['mutually_consented'],
  mutually_consented: []
}

/** Terminal states reachable from a given stage — allowed from any step. */
export function canEnterTerminal(_from: ProfileStage): readonly TerminalState[] {
  return TERMINAL_STATES
}

/**
 * Enforce that a requested transition is legal. Throws on any attempt to
 * jump stages or move backwards. Store actions call this before mutating.
 */
export function assertTransition(from: ProfileStage, to: ProfileStage): void {
  const allowed = TRANSITIONS[from] ?? []
  if (!allowed.includes(to)) {
    throw new Error(
      `Illegal state transition: ${from} → ${to}. Allowed: ${allowed.join(', ') || 'none (terminal)'}`
    )
  }
}

/** Human-readable plain-language label of each stage (i18n keys off `stage.<id>`). */
export const STAGE_LABELS: Readonly<Record<ProfileStage, string>> = {
  registered: 'Registered',
  panji_verified: 'Panji verified',
  shortlisted: 'Shortlisted',
  introduced: 'Match proposed',
  consent_pending: 'Awaiting both consents',
  mutually_consented: 'Mutual consent — contact open'
}

/** Which stage actor completed each step: automated system vs human panjikar vs family. */
export const STAGE_ACTOR: Readonly<Record<ProfileStage, 'automated' | 'panjikar' | 'family'>> = {
  registered: 'family',
  panji_verified: 'automated',
  shortlisted: 'automated',
  introduced: 'panjikar',
  consent_pending: 'family',
  mutually_consented: 'family'
}
