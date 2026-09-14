import type { Account, PlatformData, Profile } from './types'

/**
 * Seed / mock data for the end-to-end demo: two families at different
 * stages, one panjikar, one admin. Reload resets to this state (demo-only
 * persistence via localStorage in `store.ts`).
 *
 * Demo timeline:
 *  - Meera (F1, female, 26) — fully registered + consented, lineage submitted,
 *    sapinda passed. Panjikar can shortlist + propose against Aarav (F2).
 *  - Aarav (F2, male, 28) — same, ready to be matched with F1.
 *  - A third profile (F3) exists in `registered` only, so the panjikar queue
 *    shows a pending lineage review and the admin sees stage variety.
 */

function iso(daysAgo: number): string {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  return d.toISOString()
}

export const ACCOUNTS: Account[] = [
  { id: 'fam-meera', role: 'family', name: 'Suresh Jha', passcode: '1234', candidateName: 'Meera Jha', candidateAge: 26, candidateGender: 'female' },
  { id: 'fam-aarav', role: 'family', name: 'Ramesh Thakur', passcode: '1234', candidateName: 'Aarav Thakur', candidateAge: 28, candidateGender: 'male' },
  { id: 'fam-kiran', role: 'family', name: 'Mohan Pathak', passcode: '1234', candidateName: 'Kiran Pathak', candidateAge: 25, candidateGender: 'female' },
  { id: 'panjikar-1', role: 'panjikar', name: 'Pt. Bhairav Jha (Panjikar)', passcode: '1234' },
  { id: 'admin-1', role: 'admin', name: 'Sabha Coordinator', passcode: '1234' }
]

function profile(p: Partial<Profile> & Pick<Profile, 'id' | 'accountId' | 'guardian' | 'candidate'>): Profile {
  return {
    stage: 'registered',
    noDowryAcknowledgedAt: null,
    candidateRegistrationConsent: null,
    lineage: null,
    sapinda: null,
    shortlist: [],
    history: [],
    assignedPanjikarId: null,
    createdAt: iso(30),
    ...p
  }
}

export const PROFILES: Profile[] = [
  profile({
    id: 'prof-meera',
    accountId: 'fam-meera',
    stage: 'shortlisted',
    noDowryAcknowledgedAt: iso(28),
    candidateRegistrationConsent: { given: true, by: 'candidate', at: iso(28) },
    guardian: {
      name: 'Suresh Jha',
      relation: 'father',
      phone: '+91 90000 00001',
      email: 'suresh.jha@example.org',
      village: 'Bisfi',
      district: 'Madhubani',
      inviteCode: 'SABHA-2026'
    },
    candidate: {
      name: 'Meera Jha',
      gender: 'female',
      age: 26,
      education: 'M.A. (Maithili), B.Ed.',
      occupation: 'Teacher',
      city: 'Darbhanga',
      preferences: {
        minAge: 25,
        maxAge: 31,
        preferredCities: ['Darbhanga', 'Patna', 'Madhubani'],
        excludedGotras: ['Kashyap'],
        notes: 'Family values simplicity; no dowry under any circumstance.'
      }
    },
    lineage: {
      id: 'lin-meera',
      profileId: 'prof-meera',
      gotra: 'Bharadwaj',
      pravara: 'Three rishis',
      shakha: 'Vajasaneyi',
      kul: 'Durga',
      village: 'Bisfi',
      mula: 'Bisfi',
      maleLine: ['Pt. Ram Jha', 'Pt. Lakshman Jha', 'Pt. Sharan Jha', 'Pt. Kishori Jha'],
      maternalGrandmother: { name: 'Sona Devi', gotra: 'Gautam', village: 'Jhanjharpur' },
      submittedAt: iso(27),
      review: { status: 'approved', reviewerPanjikarId: 'panjikar-1', note: 'Cross-checked against the Bisfi register.', reviewedAt: iso(25) }
    },
    sapinda: { profileId: 'prof-meera', screenedAt: iso(25), conflicts: [], passed: true },
    assignedPanjikarId: 'panjikar-1',
    history: [
      { stage: 'registered', at: iso(28), by: { kind: 'guardian' }, note: 'Registration complete; candidate consent recorded.' },
      { stage: 'panji_verified', at: iso(25), by: { kind: 'panjikar', accountId: 'panjikar-1' }, note: 'Automated sapinda screen passed.' },
      { stage: 'shortlisted', at: iso(24), by: { kind: 'panjikar', accountId: 'panjikar-1' } }
    ]
  }),
  profile({
    id: 'prof-aarav',
    accountId: 'fam-aarav',
    stage: 'shortlisted',
    noDowryAcknowledgedAt: iso(26),
    candidateRegistrationConsent: { given: true, by: 'candidate', at: iso(26) },
    guardian: {
      name: 'Ramesh Thakur',
      relation: 'father',
      phone: '+91 90000 00002',
      email: 'ramesh.thakur@example.org',
      village: 'Ranti',
      district: 'Madhubani',
      inviteCode: 'SABHA-2026'
    },
    candidate: {
      name: 'Aarav Thakur',
      gender: 'male',
      age: 28,
      education: 'B.Tech (Civil)',
      occupation: 'Engineer, Bihar WRD',
      city: 'Patna',
      preferences: {
        minAge: 24,
        maxAge: 29,
        preferredCities: ['Patna', 'Darbhanga', 'Muzaffarpur'],
        excludedGotras: ['Vashishtha'],
        notes: ''
      }
    },
    lineage: {
      id: 'lin-aarav',
      profileId: 'prof-aarav',
      gotra: 'Shandilya',
      pravara: 'Shandilya, Asit, Deval',
      shakha: 'Vajasaneyi',
      kul: 'Vishahari',
      village: 'Ranti',
      mula: 'Ranti',
      maleLine: ['Pt. Dev Thakur', 'Pt. Man Thakur', 'Pt. Hari Thakur', 'Pt. Gopal Thakur'],
      maternalGrandmother: { name: 'Kamla Devi', gotra: 'Bharadwaj', village: 'Rajnagar' },
      submittedAt: iso(25),
      review: { status: 'approved', reviewerPanjikarId: 'panjikar-1', note: 'Ranti register matches.', reviewedAt: iso(23) }
    },
    sapinda: { profileId: 'prof-aarav', screenedAt: iso(23), conflicts: [], passed: true },
    assignedPanjikarId: 'panjikar-1',
    history: [
      { stage: 'registered', at: iso(26), by: { kind: 'guardian' }, note: 'Registration complete; candidate consent recorded.' },
      { stage: 'panji_verified', at: iso(23), by: { kind: 'panjikar', accountId: 'panjikar-1' }, note: 'Automated sapinda screen passed.' },
      { stage: 'shortlisted', at: iso(22), by: { kind: 'panjikar', accountId: 'panjikar-1' } }
    ]
  }),
  profile({
    id: 'prof-kiran',
    accountId: 'fam-kiran',
    stage: 'registered',
    noDowryAcknowledgedAt: iso(2),
    candidateRegistrationConsent: { given: true, by: 'candidate', at: iso(2) },
    guardian: {
      name: 'Mohan Pathak',
      relation: 'elder brother',
      phone: '+91 90000 00003',
      email: 'mohan.pathak@example.org',
      village: 'Andhratharhi',
      district: 'Madhubani',
      inviteCode: 'SABHA-2026'
    },
    candidate: {
      name: 'Kiran Pathak',
      gender: 'female',
      age: 25,
      education: 'MBBS (final year)',
      occupation: 'Doctor',
      city: 'Madhubani',
      preferences: {
        minAge: 25,
        maxAge: 30,
        preferredCities: [],
        excludedGotras: [],
        notes: ''
      }
    },
    history: [
      { stage: 'registered', at: iso(2), by: { kind: 'guardian' }, note: 'Awaiting lineage submission.' }
    ]
  })
]

export function freshData(): PlatformData {
  const data: PlatformData = {
    accounts: structuredClone(ACCOUNTS),
    profiles: structuredClone(PROFILES),
    matches: [],
    messages: [],
    consentEvents: [],
    concerns: [
      {
        id: 'con-1',
        reporterProfileId: null,
        reporterName: 'R. (initials withheld)',
        reporterContact: 'r***@example.org',
        subject: 'Dowry demand reported at a private introduction',
        body:
          'A family attending a private introduction asked for cash before further talks. Details available on contact. Requesting confidential handling.',
        status: 'escalated',
        filedAt: iso(5)
      }
    ],
    deletionRequests: [
      {
        id: 'del-1',
        profileId: 'prof-kiran',
        requestedAt: iso(1),
        status: 'requested'
      }
    ],
    auditLog: [
      { id: 'a-1', at: iso(5), actor: { kind: 'admin', accountId: 'admin-1' }, action: 'concern escalated to admin', targetId: 'con-1' },
      { id: 'a-2', at: iso(1), actor: { kind: 'guardian' }, action: 'data deletion requested', targetId: 'prof-kiran' }
    ]
  }

  // F3 (Kiran) asked for deletion — reflect that in the profile stage.
  const kiran = data.profiles.find((p) => p.id === 'prof-kiran')
  if (kiran) kiran.stage = 'withdrawn'
  const kiranReq = data.deletionRequests[0]
  kiranReq.status = 'requested'

  return data
}
