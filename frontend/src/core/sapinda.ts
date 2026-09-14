/**
 * Stage 2 — automated sapinda (close blood-relation) screening, and
 * Stage 3 — rule-based shortlist filter. Both run before any human review.
 * Pure functions over the data model so they can lift to a real backend
 * verbatim.
 */
import type {
  Profile,
  SapindaConflict,
  SapindaResult,
  ShortlistEntry
} from './types'
import { hasReached } from './state'

function nowIso(): string {
  return new Date().toISOString()
}

/**
 * Run the automated sapinda screen for one profile against all other
 * submitted profiles. Deterministic and side-effect free.
 *
 * Screens: (1) same gotra on the male line, (2) same maternal
 * grandmother's gotra, (3) same mula (original village of the male line),
 * (4) an internal data-quality check on the submitted ancestor chain.
 */
export function runSapindaScreen(profile: Profile, all: Profile[]): SapindaResult {
  const conflicts: SapindaConflict[] = []
  const own = profile.lineage

  if (!own) {
    return { profileId: profile.id, screenedAt: nowIso(), conflicts, passed: false }
  }

  for (const other of all) {
    if (other.id === profile.id) continue
    if (other.candidate.gender === profile.candidate.gender) continue
    if (!other.lineage) continue

    // Same gotra on the male line is prohibited outright.
    if (own.gotra === other.lineage.gotra) {
      conflicts.push({
        withProfileId: other.id,
        relation: 'same gotra',
        detail: `Both families belong to ${own.gotra} gotra.`,
        severity: 'blocked'
      })
      continue
    }

    // Same maternal grandmother's gotra is also prohibited.
    if (
      own.maternalGrandmother.gotra !== '' &&
      own.maternalGrandmother.gotra === other.lineage.maternalGrandmother.gotra
    ) {
      conflicts.push({
        withProfileId: other.id,
        relation: 'same maternal gotra',
        detail: `Maternal grandmother's gotra (${own.maternalGrandmother.gotra}) matches the other family's.`,
        severity: 'needs_review'
      })
      continue
    }

    // Same mula (native village of the male line) treated as likely close kin.
    if (own.mula !== '' && own.mula === other.lineage.mula) {
      conflicts.push({
        withProfileId: other.id,
        relation: 'same mula',
        detail: `Both families trace the male line to ${own.mula}.`,
        severity: 'needs_review'
      })
    }
  }

  // Internal data-quality check: a repeated ancestor name in the male line
  // suggests a transcription error the panjikar should resolve.
  const seen = new Set<string>()
  for (const ascendant of own.maleLine) {
    if (seen.has(ascendant)) {
      conflicts.push({
        withProfileId: 'unknown',
        relation: 'internal data check',
        detail: `Ancestor "${ascendant}" appears twice in the submitted male line.`,
        severity: 'needs_review'
      })
    }
    seen.add(ascendant)
  }

  return {
    profileId: profile.id,
    screenedAt: nowIso(),
    conflicts,
    passed: conflicts.length === 0
  }
}

/**
 * Stage 3 — rule-based shortlist filter. Narrows the pool by stated
 * preferences (age window, city, excluded gotras). Automated only — a
 * human panjikar reviews afterwards. Returns entries ordered by score.
 */
export function buildShortlist(profile: Profile, all: Profile[]): ShortlistEntry[] {
  const out: ShortlistEntry[] = []
  const own = profile.candidate

  for (const other of all) {
    if (other.id === profile.id) continue
    if (other.candidate.gender === own.gender) continue
    // Only profiles that passed the sapinda screen are eligible.
    if (!other.sapinda || !other.sapinda.passed) continue
    if (!hasReached(other.stage, 'panji_verified')) continue

    const matchedOn: string[] = []
    let score = 0

    // Mutual age-window overlap.
    const ageLo = Math.max(own.preferences.minAge, other.candidate.preferences.minAge)
    const ageHi = Math.min(own.preferences.maxAge, other.candidate.preferences.maxAge)
    if (ageLo > ageHi) continue
    matchedOn.push(`age window ${ageLo}\u2013${ageHi}`)
    score += 2

    // Other candidate's age inside my window.
    if (own.preferences.minAge <= other.candidate.age && other.candidate.age <= own.preferences.maxAge) {
      matchedOn.push(`age ${other.candidate.age}`)
      score += 1
    }

    // City preference.
    const cityMatch =
      own.preferences.preferredCities.length === 0 ||
      own.preferences.preferredCities.includes(other.candidate.city)
    if (cityMatch) {
      matchedOn.push(`city ${other.candidate.city}`)
      score += 1
    }

    // Excluded gotras (e.g. within forbidden degrees).
    const otherGotra = other.lineage?.gotra ?? ''
    if (otherGotra !== '' && own.preferences.excludedGotras.includes(otherGotra)) continue
    matchedOn.push(`gotra ${otherGotra || 'n/a'}`)

    out.push({ candidateProfileId: other.id, matchedOn, score })
  }

  out.sort((a, b) => b.score - a.score)
  return out
}
