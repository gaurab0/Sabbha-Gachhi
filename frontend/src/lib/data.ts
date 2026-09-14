// ── Mock data for the Sabha Gachhi demo build ──
// Everything here is local placeholder data. No API calls are made.

export type RegistrationStatus =
  | 'registered'
  | 'verified'
  | 'introduced'
  | 'outcome'

export interface Ancestor {
  name: string
  village: string
  gotra: string
}

export interface Registrant {
  id: string
  candidate: string
  side: 'bride' | 'groom'
  age: number
  village: string
  education: string
  guardian: string
  gotra: string
  status: RegistrationStatus
  note?: string
}

/** The demo family logging in through the private link. */
export const MY_FAMILY = {
  id: 'SG-2026-0147',
  household: 'Jha household, Barhara',
  candidate: 'Shreya Jha',
  side: 'bride' as const,
  guardian: 'Shri Ramnandana Jha',
  status: 'verified' as RegistrationStatus,
  accessCode: 'SABHA-0147',
}

/** The proposal the demo family currently has on the table. */
export const PROPOSAL = {
  household: 'Thakur household, Simra',
  candidate: 'Rohan Thakur',
  age: 29,
  village: 'Simra, Darbhanga',
  education: 'BSc Agriculture, agriculturist by profession',
  panjikarNote:
    "The panjikar has reviewed both panjis and found no sapinda conflict. The Thakur family has affirmed the same dowry-free understanding your family registered with.",
  contact: {
    phone: '+91 98765 43210',
    email: 'rohan.thakur@example.in',
    note: 'Shared only because both families have accepted. Please treat this information as private.',
  },
}

/** Work-queue for the panjikar screens. */
export const REGISTRATIONS: Registrant[] = [
  {
    id: 'SG-2026-0147',
    candidate: 'Shreya Jha',
    side: 'bride',
    age: 26,
    village: 'Barhara',
    education: 'MA Sanskrit',
    guardian: 'Ramnandana Jha',
    gotra: 'Vatsa',
    status: 'introduced',
  },
  {
    id: 'SG-2026-0188',
    candidate: 'Anirudh Mishra',
    side: 'groom',
    age: 30,
    village: 'Kulharia',
    education: 'BCom, employed in Patna',
    guardian: 'Bhavani Mishra',
    gotra: 'Kashyapa',
    status: 'verified',
  },
  {
    id: 'SG-2026-0192',
    candidate: 'Kumari Vaidehi Jha',
    side: 'bride',
    age: 24,
    village: 'Pandaul',
    education: 'BEd',
    guardian: 'Shrikant Jha',
    gotra: 'Bharadwaja',
    status: 'registered',
  },
  {
    id: 'SG-2026-0195',
    candidate: 'Mahadev Choudhary',
    side: 'groom',
    age: 32,
    village: 'Madhubani',
    education: 'Farmer, ancestral lands',
    guardian: 'Ganga Choudhary',
    gotra: 'Sandilya',
    status: 'outcome',
    note: 'Introduced in 2025 — marriage solemnised. Kept for the record.',
  },
  {
    id: 'SG-2026-0201',
    candidate: 'Radhika Karn',
    side: 'bride',
    age: 27,
    village: 'Jhanjharpur',
    education: 'MBBS',
    guardian: 'Vidya Karn',
    gotra: 'Vashishtha',
    status: 'verified',
  },
  {
    id: 'SG-2026-0204',
    candidate: 'Ramvilas Jha',
    side: 'groom',
    age: 28,
    village: 'Barhara',
    education: 'MSc, lecturer',
    guardian: 'Suresh Jha',
    gotra: 'Vatsa',
    status: 'registered',
    note: 'Same village and gotra as SG-2026-0147 — panji check still open.',
  },
]

/** A panji record under open review (used on the lineage review screen). */
export const UNDER_REVIEW = {
  registrant: REGISTRATIONS[5],
  brideSide: [
    { relation: 'Father', name: 'Shri Suresh Jha', village: 'Barhara', gotra: 'Vatsa' },
    { relation: 'Grandfather', name: 'Late Devananda Jha', village: 'Barhara', gotra: 'Vatsa' },
    { relation: 'Great-grandfather', name: 'Late Tribhuvan Jha', village: 'Barhara', gotra: 'Vatsa' },
  ],
  existingHousehold: [
    { relation: 'Father of SG-2026-0147', name: 'Shri Ramnandana Jha', village: 'Barhara', gotra: 'Vatsa' },
    { relation: 'Grandfather of SG-2026-0147', name: 'Late Krishnananda Jha', village: 'Barhara', gotra: 'Vatsa' },
  ],
}
