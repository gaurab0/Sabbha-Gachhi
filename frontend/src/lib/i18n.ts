// ── Minimal trilingual labels for the registration flow ──
// Maithili and Hindi render in Devanagari; English in Latin.

export type Language = 'maithili' | 'hindi' | 'english'

export const LANGUAGES: { code: Language; label: string }[] = [
  { code: 'maithili', label: 'मैथिली' },
  { code: 'hindi', label: 'हिन्दी' },
  { code: 'english', label: 'English' },
]

const strings: Record<Language, Record<string, string>> = {
  maithili: {
    languageHeading: 'भाषा चुनू',
    guardian: 'अभिभावक आ परिवारक विवरण',
    candidate: 'वर / वधूक विवरण',
    lineage: 'वंशावली (पंजि)',
    consent: 'सक्षम व्यक्तिक सहमति',
    confirm: 'पंजीकरण भेल गेल',
    back: 'घुक',
    next: 'आगू',
    submit: 'पंजीकरण भेटाउ',
    consentPrompt:
      'अपन शब्दमे लिखू जे अहाँ ई मंच पर पंजीकृत होबाक लेल सहमत अछि।',
  },
  hindi: {
    languageHeading: 'भाषा चुनें',
    guardian: 'अभिभावक एवं परिवार का विवरण',
    candidate: 'वर / वधू का विवरण',
    lineage: 'वंशावली (पंजि)',
    consent: 'संबंधित व्यक्ति की सहमति',
    confirm: 'पंजीकरण हो गया',
    back: 'वापस',
    next: 'आगे',
    submit: 'पंजीकरण भेजें',
    consentPrompt: 'अपने शब्दों में लिखें कि आप इस मंच पर पंजीकरण के लिए सहमत हैं।',
  },
  english: {
    languageHeading: 'Choose your language',
    guardian: 'Guardian and family details',
    candidate: 'Details of the prospective bride or groom',
    lineage: 'Family lineage (panji)',
    consent: 'Consent of the person being registered',
    confirm: 'Your registration is with us',
    back: 'Back',
    next: 'Continue',
    submit: 'Submit registration',
    consentPrompt:
      'In your own words, state that you agree to be registered on this platform.',
  },
}

export function t(lang: Language, key: string): string {
  return strings[lang][key] ?? strings.english[key] ?? key
}
