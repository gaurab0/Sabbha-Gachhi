/**
 * Minimal i18n: three languages (Maithili, Hindi, English), persisted to
 * localStorage. Keys are flat dot-notation; English is the reference set and
 * falls back for any missing key.
 */

export type Lang = 'mai' | 'hi' | 'en'

export const LANGUAGES: { id: Lang; label: string; native: string }[] = [
  { id: 'mai', label: 'Maithili', native: 'मैथिली' },
  { id: 'hi', label: 'Hindi', native: 'हिन्दी' },
  { id: 'en', label: 'English', native: 'English' }
]

const en = {
  'app.name': 'Sabha Gachhi',
  'app.tagline': 'Saurath Sabha Gachhi Panji Tradition',

  // Nav
  'nav.home': 'Home',
  'nav.mela': 'Saurath Mela',
  'nav.donate': 'Support Us',
  'nav.report': 'Report a Concern',
  'nav.login': 'Log In',
  'nav.dashboard': 'My Family',
  'nav.panjikar': 'Panjikar Desk',
  'nav.admin': 'Admin',
  'nav.logout': 'Log Out',
  'nav.menu': 'Menu',

  // Landing
  'landing.kicker': 'A private, non-profit community service',
  'landing.h1': 'Continuing a Tradition of Dignified Matchmaking',
  'landing.sub':
    'A private, invite-only platform preserving the panji tradition — dowry-free, genealogy-verified introductions made only by a human verifier. There is nothing to browse here, by design.',
  'landing.cta': 'Request an Invitation',
  'landing.notDating':
    'This is not a matrimonial marketplace. No profiles are public, nothing is searchable, and no family ever sees another family\u2019s information until both sides have consented through a panjikar.',
  'landing.missionTitle': 'Our Mission',
  'landing.missionBody':
    'For centuries the Saurath Sabha Gachhi brought Maithil Brahmin families together through panji-verified introductions, free of dowry. This platform continues that work as a charity, not a business: no fees, no advertising, no data sale.',
  'landing.mission2':
    'Every match is proposed by a panjikar — a human verifier of our community — only after your family\u2019s genealogy has been checked. Families never browse, never swipe, never search.',
  'landing.howTitle': 'How It Works',
  'landing.step1': 'Receive an invitation through the Sabha community — there is no public sign-up.',
  'landing.step2':
    'Register privately with a guardian, and confirm with the bride or groom\u2019s own consent. Submit your panji lineage record.',
  'landing.step3':
    'Automated checks screen for close blood relations. A panjikar then reviews your case by hand.',
  'landing.step4':
    'A panjikar proposes a specific match to both families at once. Each family consents privately; neither sees the other\u2019s answer until both have answered.',
  'landing.step5': 'Only after mutual consent is any contact opened — inside the platform, never a raw phone number first.',
  'landing.privacyTitle': 'Your Privacy Is Absolute',
  'landing.privacy1': 'Invite-only — no public profiles, no searchable directory, no swiping',
  'landing.privacy2': 'Your decision is never shown to the other family before both have responded',
  'landing.privacy3': 'Non-profit — no advertising, no monetization of your information',
  'landing.privacy4': 'Genealogy records are handled with the discretion of the traditional Sabha',
  'landing.langNote': 'Available in Maithili, Hindi and English.',

  // Mela
  'mela.title': 'Saurath Mela',
  'mela.sub': 'The annual gathering of the panji tradition, held in Mithila for over seven centuries.',
  'mela.p1':
    'The Saurath Sabha — popularly the Saurath Mela — is the historic assembly where Maithil Brahmin families, guided by panjikars holding the genealogical registers (panji), arranged marriages verified against generations of recorded lineage. The mela is traditionally held at Saurath village in Madhubani district.',
  'mela.p2':
    'This platform extends that gathering online for families who cannot travel, with the same safeguards: no dowry, no public display, and a panjikar at the centre of every introduction. The in-person mela continues; this service supports, and never replaces, it.',
  'mela.whenTitle': 'When & Where',
  'mela.whenBody': 'Traditionally observed in the Hindu month of Ashadha at Saurath, Madhubani district, Bihar. Dates for the coming year are announced through the Sabha.',
  'mela.etiquetteTitle': 'The Mela Covenant',
  'mela.etiquette1': 'No dowry is asked, offered, or discussed — this is a condition of participation.',
  'mela.etiquette2': 'Panjikar verification of both lineages comes before any introduction.',
  'mela.etiquette3': 'Families meet with dignity — there is no bargaining over persons.',

  // Donate
  'donate.title': 'Support This Work',
  'donate.sub': 'This platform is run by volunteers as a community charity. Nothing is charged to families.',
  'donate.p1':
    'Costs are small — hosting, and stipends for panjikars who verify records. Donations keep the service free and independent. We accept no advertising and sell no data, ever.',
  'donate.waysTitle': 'Ways to Support',
  'donate.way1': 'Volunteer as a panjikar — if you hold knowledge of the panji records, write to us.',
  'donate.way2': 'Contribute to running costs — UPI and bank transfer details are shared on request at our contact address.',
  'donate.way3': 'Spread the word among families who may need this service, with the same discretion we practice.',
  'donate.transparency': 'Transparency: a simple annual statement of accounts is shared with the Sabha community.',

  // Report
  'report.title': 'Report a Concern',
  'report.sub': 'This form is open to anyone — you do not need an account. Reports are confidential.',
  'report.name': 'Your name (may be initials)',
  'report.contact': 'How we may reach you (phone or email)',
  'report.subject': 'Subject',
  'report.body': 'What happened? Include any relevant names, dates, or match references.',
  'report.related': 'Related match reference (optional)',
  'report.submit': 'Submit Report',
  'report.thanks': 'Thank you. Your report has been recorded confidentially. A coordinator will follow up.',
  'report.dowryNote': 'If you are reporting a dowry demand, say so in the subject — such reports are treated with the highest priority.',

  // Login
  'login.title': 'Log In',
  'login.sub': 'Families, panjikars and administrators log in here. This is a demo build — use a seeded account below.',
  'login.accountId': 'Account ID',
  'login.passcode': 'Passcode',
  'login.submit': 'Log In',
  'login.error': 'Account ID or passcode not recognised.',
  'login.seeded': 'Demo accounts (seeded)',
  'login.role.family': 'Family / guardian',
  'login.role.panjikar': 'Panjikar (verifier)',
  'login.role.admin': 'Administrator',

  // Family dashboard
  'fam.title': 'My Family',
  'fam.noProfile': 'Your family has not registered a profile yet.',
  'fam.start': 'Begin Registration',
  'fam.statusTitle': 'Where things stand',
  'fam.auto': 'Automated check',
  'fam.human': 'Panjikar review',
  'fam.you': 'You',
  'fam.current': 'Current stage',
  'fam.pendingAction': 'What is needed from you now',
  'fam.waitAuto': 'Nothing — the automated checks run on their own.',
  'fam.waitPanjikar': 'Nothing yet — a panjikar is reviewing your case. You will be notified.',
  'fam.waitProposal': 'A panjikar will propose a match when one is ready. You cannot browse or search — that is by design.',
  'fam.respond': 'A proposed match is waiting for your response.',
  'fam.viewProposal': 'View Proposed Match',
  'fam.messages': 'Private Messages',
  'fam.openMessages': 'Open Conversation',
  'fam.withdraw': 'Withdraw / End Contact',
  'fam.withdrawConfirm':
    'This ends all contact and hides your profile from all future consideration. No reason is required. You may re-register later. Continue?',
  'fam.withdrawn': 'Your profile has been withdrawn. Your data remains deletable on request.',
  'fam.declined': 'You declined the proposed match. Thank you for letting us know.',
  'fam.settings': 'Account Settings',
  'fam.lineageStatus': 'Lineage verification (visible only to you and your panjikar)',
  'fam.sapindaStatus': 'Automated sapinda screen',
  'fam.passed': 'Passed',
  'fam.flagged': 'Needs review',
  'fam.pending': 'Pending',
  'fam.notSubmitted': 'Not yet submitted',

  // Intake wizard
  'intake.title': 'Private Registration',
  'intake.step1': 'Guardian Details',
  'intake.step2': 'Prospective Bride / Groom',
  'intake.step3': 'Lineage (Panji Record)',
  'intake.step4': 'Candidate\u2019s Own Consent',
  'intake.step5': 'Acknowledgements',
  'intake.inviteCode': 'Invitation code',
  'intake.inviteHint': 'Issued by the Sabha. Demo code: SABHA-2026',
  'intake.guardianName': 'Guardian name',
  'intake.relation': 'Relation to candidate',
  'intake.phone': 'Phone',
  'intake.email': 'Email',
  'intake.village': 'Village / town',
  'intake.district': 'District',
  'intake.candidateName': 'Candidate\u2019s full name',
  'intake.gender': 'Gender',
  'intake.female': 'Female',
  'intake.male': 'Male',
  'intake.age': 'Age',
  'intake.education': 'Education',
  'intake.occupation': 'Occupation',
  'intake.city': 'Current city',
  'intake.prefAge': 'Preferred age range',
  'intake.prefCities': 'Preferred cities (comma-separated, optional)',
  'intake.excludedGotras': 'Gotras excluded by your family (comma-separated)',
  'intake.prefNotes': 'Other notes for the panjikar (optional)',
  'intake.gotra': 'Gotra',
  'intake.pravara': 'Pravara (optional)',
  'intake.shakha': 'Shakha (optional)',
  'intake.kul': 'Kul / Kuladevata (optional)',
  'intake.mula': 'Mula (native village of the male line)',
  'intake.maleLine': 'Male-line ancestors, eldest first (comma-separated)',
  'intake.mgmName': 'Maternal grandmother\u2019s name',
  'intake.mgmGotra': 'Maternal grandmother\u2019s gotra',
  'intake.mgmVillage': 'Maternal grandmother\u2019s village',
  'intake.consentTitle': 'Confirmation by the candidate',
  'intake.consentBody':
    'This step must be completed by the prospective bride or groom in person. The guardian must not tick this on someone else\u2019s behalf. In the demo, select who is confirming.',
  'intake.consentQuestion': 'I, the candidate named above, confirm that I am aware of this registration and consent to it.',
  'intake.confirmAs': 'Confirming as',
  'intake.dowryTitle': 'No-dowry acknowledgement',
  'intake.dowryBody':
    'Our family affirms that no dowry, cash, goods, or "gifts" have been demanded, offered, or will be discussed at any stage. Participation in this platform is conditional on this acknowledgement.',
  'intake.dowryCheck': 'We acknowledge and affirm the no-dowry covenant.',
  'intake.back': 'Back',
  'intake.next': 'Next',
  'intake.submit': 'Submit Registration',
  'intake.submitted': 'Registration submitted. Your family\u2019s status will update as each stage completes.',

  // Proposal & consent
  'prop.title': 'Proposed Match',
  'prop.sub': 'Proposed to both families at the same time by your panjikar. The other family cannot see your answer.',
  'prop.proposedBy': 'Proposed by',
  'prop.note': 'Panjikar\u2019s note',
  'prop.aboutThem': 'About the other family (only what is needed to decide)',
  'prop.themGuardian': 'Guardian',
  'prop.themCandidate': 'Their bride / groom',
  'prop.themCity': 'City',
  'prop.themGotra': 'Gotra',
  'prop.themMatched': 'Matched on',
  'prop.consent': 'We consent to this match',
  'prop.decline': 'We decline',
  'prop.reasonOptional': 'Reason (optional — never required, never shared with the other family while they decide)',
  'prop.waiting': 'Your response is recorded and sealed. The other family will not learn of it unless they too respond — and you will not learn of theirs first.',
  'prop.mutual': 'Both families consented. A private conversation is now open inside the platform. Contact details are never exchanged automatically.',
  'prop.otherDecided': 'The other family has responded. The panjikar will contact you about next steps.',

  // Messages
  'msg.title': 'Private Conversation',
  'msg.placeholder': 'Write a message…',
  'msg.send': 'Send',
  'msg.empty': 'No messages yet. Write the first note — this thread exists only between the two families.',
  'msg.privacy': 'This thread is visible only to the two families and their panjikar for safeguarding. Phone numbers and addresses are not shared by the platform.',
  'msg.asGuardian': 'As guardian',
  'msg.asCandidate': 'As candidate',
  'msg.report': 'Report a concern about this match',
  'msg.withdraw': 'End this contact',

  // Settings
  'set.title': 'Account Settings',
  'set.language': 'Language',
  'set.notifications': 'Notification preferences',
  'set.notifMatch': 'Notify me when a panjikar proposes a match',
  'set.notifStage': 'Notify me when my case moves to a new stage',
  'set.notifReports': 'Notify me about updates to reports I filed',
  'set.delete': 'Delete my data',
  'set.deleteBody':
    'A full deletion removes your profile, lineage submission, match history and messages. An administrator reviews and completes the request; you will receive confirmation.',
  'set.deleteBtn': 'Request Full Deletion',
  'set.deleteConfirm': 'Request deletion of all your family\u2019s data? This cannot be undone.',
  'set.deleteDone': 'Deletion request filed. An administrator will process it.',

  // Panjikar
  'pk.title': 'Panjikar Desk',
  'pk.queue': 'Pending Lineage Submissions',
  'pk.cases': 'Case Tracker',
  'pk.concerns': 'Reported Concerns',
  'pk.review': 'Review Lineage',
  'pk.gotra': 'Gotra',
  'pk.mula': 'Mula',
  'pk.maleLine': 'Male line',
  'pk.mgm': 'Maternal grandmother',
  'pk.approve': 'Approve',
  'pk.flag': 'Flag sapinda concern',
  'pk.requestInfo': 'Request more info',
  'pk.note': 'Note to family',
  'pk.infoRequest': 'What is needed from the family',
  'pk.shortlist': 'Shortlist',
  'pk.propose': 'Propose Match',
  'pk.proposeWith': 'Propose match with',
  'pk.proposeNote': 'Note shown to both families',
  'pk.proposeHint': 'Pick one profile from the shortlist. Both families are notified together; neither can see the other\u2019s consent.',
  'pk.proposed': 'Match proposed to both families.',
  'pk.automated': 'Automated sapinda screen',
  'pk.clear': 'Clear',
  'pk.conflict': 'Conflict',
  'pk.blocked': 'Blocked',
  'pk.needsReview': 'Needs review',
  'pk.stage': 'Stage',
  'pk.candidate': 'Candidate',
  'pk.filter': 'Filter by stage',
  'pk.search': 'Search by name, village or gotra',
  'pk.resolved': 'Mark resolved',
  'pk.escalate': 'Escalate to admin',
  'pk.underReview': 'Start review',

  // Admin
  'adm.title': 'Administration',
  'adm.panjikars': 'Panjikar Accounts',
  'adm.deletions': 'Deletion Requests',
  'adm.concerns': 'Escalated Concerns',
  'adm.stats': 'Platform Statistics (anonymized counts)',
  'adm.addPanjikar': 'Add panjikar',
  'adm.name': 'Name',
  'adm.deactivate': 'Deactivate',
  'adm.activate': 'Activate',
  'adm.active': 'Active',
  'adm.inactive': 'Inactive',
  'adm.complete': 'Complete deletion',
  'adm.reject': 'Reject',
  'adm.requested': 'Requested',
  'adm.inProgress': 'In progress',
  'adm.completed': 'Completed',
  'adm.rejected': 'Rejected',
  'adm.audit': 'Audit log',
  'adm.statProfiles': 'Profiles registered',
  'adm.statVerified': 'Panji-verified',
  'adm.statShortlisted': 'Shortlisted',
  'adm.statIntroduced': 'Introduced',
  'adm.statConsent': 'Consent pending',
  'adm.statMutual': 'Mutually consented',
  'adm.statDeclined': 'Declined',
  'adm.statWithdrawn': 'Withdrawn',
  'adm.noBrowse':
    'Administrators cannot browse family data. Individual records appear only inside a report or deletion request you are resolving.',

  // Status tracker
  'stage.registered': 'Registered',
  'stage.panji_verified': 'Panji verified',
  'stage.shortlisted': 'Shortlisted',
  'stage.introduced': 'Match proposed',
  'stage.consent_pending': 'Awaiting both consents',
  'stage.mutually_consented': 'Contact open',
  'stage.declined': 'Declined',
  'stage.withdrawn': 'Withdrawn',
  'stage.auto': 'Automated',
  'stage.human': 'Panjikar',

  // Common
  'common.of': 'of',
  'common.close': 'Close',
  'common.optional': 'optional',
  'common.required': 'required',
  'common.demo': 'Demo build — data resets on reload',
  'common.back': 'Back',
  'common.footer':
    'Sabha Gachhi · A non-profit community service · Nothing here is public or searchable · No dowry'
} as const

export type TKey = keyof typeof en

const hi: Partial<Record<TKey, string>> = {
  'app.tagline': 'सौराठ सभा गछी पंजी परंपरा',
  'nav.home': 'मुख्य पृष्ठ',
  'nav.mela': 'सौराठ मेला',
  'nav.donate': 'सहयोग करें',
  'nav.report': 'शिकायत दर्ज करें',
  'nav.login': 'प्रवेश करें',
  'nav.dashboard': 'मेरा परिवार',
  'nav.panjikar': 'पंजिकार पेठ',
  'nav.admin': 'प्रशासन',
  'nav.logout': 'बाहर जाएँ',
  'nav.menu': 'मेनू',
  'landing.kicker': 'एक निजी, अलाभकारी सामुदायिक सेवा',
  'landing.h1': 'गरिमामय विवाह मिलान की परंपरा को आगे बढ़ाते हुए',
  'landing.sub':
    'पंजी परंपरा को सँभालता एक निजी, निमंत्रण-आधारित मंच — दहेज-मुक्त, वंशावली-सत्यापित परिचय केवल मानव पंजिकार द्वारा। यहाँ ब्राउज़ करने के लिए कुछ भी नहीं है, जानबूझकर।',
  'landing.cta': 'निमंत्रण का अनुरोध करें',
  'landing.missionTitle': 'हमारा उद्देश्य',
  'landing.howTitle': 'यह कैसे काम करता है',
  'landing.privacyTitle': 'आपकी गोपनीयता परम है',
  'mela.title': 'सौराठ मेला',
  'donate.title': 'इस कार्य में सहयोग दें',
  'report.title': 'शिकायत दर्ज करें',
  'login.title': 'प्रवेश',
  'fam.title': 'मेरा परिवार',
  'intake.title': 'निजी पंजीकरण',
  'prop.title': 'प्रस्तावित मिलान',
  'msg.title': 'निजी वार्तालाप',
  'set.title': 'खाता सेटिंग्स',
  'pk.title': 'पंजिकार पेठ',
  'adm.title': 'प्रशासन',
  'common.footer': 'सभा गछी · एक अलाभकारी सामुदायिक सेवा · यहाँ कुछ भी सार्वजनिक या खोजयोग्य नहीं है · दहेज नहीं'
}

const mai: Partial<Record<TKey, string>> = {
  ...hi,
  'app.tagline': 'सौराठ सभा गछी पंजी परंपरा',
  'landing.kicker': 'एकटा निजी, अलाभकारी सामुदायिक सेवा',
  'landing.h1': 'गरिमामय विवाह मिलानक परंपराक अगुवाई',
  'nav.home': 'मुख्य पृष्ठ',
  'nav.mela': 'सौराठ मेला',
  'nav.dashboard': 'हमर परिवार',
  'fam.title': 'हमर परिवार'
}

const DICTS: Record<Lang, Partial<Record<TKey, string>>> = { en, hi, mai }

const STORAGE_KEY = 'sabha-gachhi.lang'

export function loadLang(): Lang {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'mai' || v === 'hi' || v === 'en') return v
  } catch {
    /* storage unavailable */
  }
  return 'en'
}

export function saveLang(lang: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    /* storage unavailable */
  }
}

export function t(lang: Lang, key: TKey): string {
  return DICTS[lang][key] ?? en[key]
}

/** Devanagari-capable font stack, per the platform\u2019s UI requirements. */
export function fontStackFor(lang: Lang): string {
  if (lang === 'en') return 'var(--font-sans)'
  return '"Noto Sans Devanagari", "Mangal", var(--font-sans)'
}
