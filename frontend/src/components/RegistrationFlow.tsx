import React, { useRef, useState } from "react";
import { ApiError } from "../api/client";
import { submitRegistration } from "../api/registration";

/**
 * RegistrationFlow
 * Component 1 of the Sabha Gachhi matrimonial-registration site.
 * Frontend only — all "submission" is mocked with a local delay.
 * Fully localized: once a language is chosen on step 1, every
 * subsequent screen (labels, help text, buttons) renders in that
 * language for the rest of the flow.
 */

// ---------------------------------------------------------------- Types --
function buildRegistrationPayload(
  language: LanguageCode,
  guardian: GuardianDetails,
  candidate: CandidateDetails,
  preferences: PartnerPreferences,
  lineage: Lineage,
  consent: ConsentState,
  t: CopyStrings
) {
  return {
    language,
    guardian_name: guardian.name,
    guardian_relation_to_candidate: guardian.relationToCandidate,
    guardian_village: guardian.village,
    guardian_district: guardian.district,
    guardian_phone: guardian.phone,
    guardian_email: guardian.email,
    candidate_full_name: candidate.fullName,
    candidate_gender: candidate.gender,
    candidate_dob: candidate.dob,
    candidate_education: candidate.education,
    candidate_occupation: candidate.occupation,
    candidate_current_city: candidate.currentCity,
    preferred_age_min: preferences.ageMin ? Number(preferences.ageMin) : null,
    preferred_age_max: preferences.ageMax ? Number(preferences.ageMax) : null,
    preferred_location: preferences.location,
    preferred_education: preferences.education,
    gotra: lineage.gotra,
    mool_gram: lineage.moolGram,
    paternal_line: lineage.paternal.map((e) => ({
      label: getAncestorLabel(t, e),
      name: e.name,
    })),
    maternal_line: lineage.maternal.map((e) => ({
      label: getAncestorLabel(t, e),
      name: e.name,
    })),
    consent_choice: consent.choice,
    consent_own_words: consent.ownWords,
  };
}
type StepId =
  | "language"
  | "guardian"
  | "candidate"
  | "preferences"
  | "lineage"
  | "consent"
  | "confirmation";

const STEP_ORDER: StepId[] = [
  "language",
  "guardian",
  "candidate",
  "preferences",
  "lineage",
  "consent",
  "confirmation",
];

type LanguageCode = "en" | "hi" | "mai";

// ---------------------------------------------------------------- Copy --

interface CopyStrings {
  brand: string;
  stepLabels: Record<StepId, string>;
  common: {
    back: string;
    continue: string;
  };
  language: {
    title: string;
    help: string;
    welcomeTitle: string;
    welcomeBody: string;
  };
  guardian: {
    kicker: string;
    title: string;
    help: string;
    nameLabel: string;
    namePlaceholder: string;
    relationLabel: string;
    relationPlaceholder: string;
    villageLabel: string;
    districtLabel: string;
    phoneLabel: string;
    phonePlaceholder: string;
    emailLabel: string;
  };
  candidate: {
    kicker: string;
    title: string;
    help: string;
    fullNameLabel: string;
    registeringAsLabel: string;
    brideLabel: string;
    groomLabel: string;
    dobLabel: string;
    cityLabel: string;
    educationLabel: string;
    occupationLabel: string;
    photoOptionalLabel: string;
    photoUploadLabel: string;
    photoHelpText: string;
    photoReplaceLabel: string;
    photoRemoveLabel: string;
    photoErrorType: string;
    photoErrorSize: string;
    photoPrivacyNote: string;
    photoAltText: string;
  };
  preferences: {
    kicker: string;
    title: string;
    help: string;
    ageMinLabel: string;
    ageMaxLabel: string;
    locationLabel: string;
    educationLabel: string;
    optionalNote: string;
  };
  lineage: {
    kicker: string;
    title: string;
    help: string;
    gotraLabel: string;
    moolGramLabel: string;
    paternalTitle: string;
    maternalTitle: string;
    addGenerationLabel: string;
    fatherLabel: string;
    grandfatherLabel: string;
    greatGrandfatherLabel: string;
    nanaLabel: string;
    maternalGrandfatherLabel: string;
    namePlaceholder: string;
    additionalAncestorLabelFn: (generation: number) => string;
  };
  consent: {
    kicker: string;
    titleFn: (name: string) => string;
    helpFn: (name: string) => string;
    agreeOption: string;
    notYetOption: string;
    ownWordsLabel: string;
    ownWordsPlaceholder: string;
    notYetHelp: string;
    photoConsentNote: string;
    defaultName: string;
    submit: string;
    submitting: string;
  };
  confirmation: {
    kicker: string;
    title: string;
    help: string;
    refLabel: string;
    footerHelp: string;
  };
}

const COPY: Record<LanguageCode, CopyStrings> = {
  // ---------------------------------------------------------- English --
  en: {
    brand: "Saurath Sabha Gachhi",
    stepLabels: {
      language: "Language",
      guardian: "Guardian details",
      candidate: "About the candidate",
      preferences: "Partner preferences",
      lineage: "Lineage",
      consent: "Consent",
      confirmation: "Confirmation",
    },
    common: { back: "Back", continue: "Continue" },
    language: {
      title: "Choose your language",
      help: "You can change this any time.",
      welcomeTitle: "Before we begin",
      welcomeBody:
        "This registration is handled personally by our panjikars. Nothing here is public, and nothing is shared until a family agrees to it.",
    },
    guardian: {
      kicker: "Guardian & family details",
      title: "Who is registering on the family's behalf?",
      help: "Most families register through a parent or elder. This is who our panjikar will speak with first.",
      nameLabel: "Your full name",
      namePlaceholder: "e.g. Ramesh Jha",
      relationLabel: "Your relation to the candidate",
      relationPlaceholder: "e.g. Father, Mother, Elder brother, Self",
      villageLabel: "Village / Gram",
      districtLabel: "District",
      phoneLabel: "Phone number",
      phonePlaceholder: "+91",
      emailLabel: "Email (optional)",
    },
    candidate: {
      kicker: "About the candidate",
      title: "Now, a little about them",
      help: "These details help the panjikar understand who they are looking for a match for.",
      fullNameLabel: "Full name",
      registeringAsLabel: "They are registering as",
      brideLabel: "Bride",
      groomLabel: "Groom",
      dobLabel: "Date of birth",
      cityLabel: "Current city",
      educationLabel: "Education",
      occupationLabel: "Occupation",
      photoOptionalLabel: "A photograph (optional)",
      photoUploadLabel: "Upload a photo",
      photoHelpText: "JPG or PNG, up to 5MB.",
      photoReplaceLabel: "Replace",
      photoRemoveLabel: "Remove",
      photoErrorType: "That file type isn't supported. Please choose a JPG or PNG.",
      photoErrorSize: "That photo is larger than 5MB. Please choose a smaller one.",
      photoPrivacyNote:
        "Shared only with a specific family, only after a match is proposed. Never public.",
      photoAltText:
        "Portrait of the candidate — shared only at the moment a match is proposed.",
    },
    preferences: {
      kicker: "What they're looking for",
      title: "A little about what they have in mind",
      help: "Everything here is optional and used only to help the panjikari process find a thoughtful match — it's never shown to anyone else.",
      ageMinLabel: "Preferred age — from",
      ageMaxLabel: "Preferred age — to",
      locationLabel: "Preferred location",
      educationLabel: "Preferred education level",
      optionalNote: "Leave anything blank if there's no strong preference.",
    },
    lineage: {
      kicker: "Lineage",
      title: "Family lineage, for the panji",
      help: "This is used only to check for sapinda relation — never shown to a prospective match. Fill in what you know; the panjikar can help complete the rest.",
      gotraLabel: "Gotra / Mool",
      moolGramLabel: "Ancestral village (Mool gram)",
      paternalTitle: "Paternal line",
      maternalTitle: "Maternal line",
      addGenerationLabel: "+ Add another generation",
      fatherLabel: "Father",
      grandfatherLabel: "Grandfather",
      greatGrandfatherLabel: "Great-grandfather",
      nanaLabel: "Mother's father (Nana)",
      maternalGrandfatherLabel: "Mother's grandfather",
      namePlaceholder: "Name",
      additionalAncestorLabelFn: (n) => `Ancestor (generation ${n})`,
    },
    consent: {
      kicker: "Consent",
      titleFn: (name) => `This part is ${name}'s alone`,
      helpFn: (name) =>
        `Everything so far was filled in by the guardian. Before we accept this registration, ${name} should confirm — in their own words — that they agree to be registered.`,
      agreeOption: "Yes — I agree to be registered, of my own will.",
      notYetOption: "Not yet — I need more time before deciding.",
      ownWordsLabel: "In your own words, tell us you agree",
      ownWordsPlaceholder:
        "e.g. I, [name], agree to be registered with Sabha Gachhi for the purpose of finding a marriage match.",
      notYetHelp:
        "That's alright. Nothing is submitted until this step is complete — come back to it whenever you're ready.",
      photoConsentNote:
        "If a photograph was added to this registration, it is shown to one specific family only, at the moment a match is proposed — never publicly, never made browsable. If no photograph was added, this part can be left untouched.",
      defaultName: "The candidate",
      submit: "Submit registration",
      submitting: "Submitting…",
    },
    confirmation: {
      kicker: "Registration received",
      title: "Your registration is with us.",
      help: "A panjikar will review the details and lineage over the coming days. There's nothing further to do right now — we'll reach the guardian directly once there is something to share.",
      refLabel: "Reference",
      footerHelp:
        "You can check on this registration any time using the private status link that will be shared with the guardian.",
    },
  },

  // ------------------------------------------------------------ Hindi --
  hi: {
    brand: "सौराठ सभा गाछी",
    stepLabels: {
      language: "भाषा",
      guardian: "अभिभावक विवरण",
      candidate: "उम्मीदवार के बारे में",
      preferences: "साथी की पसंद",
      lineage: "वंशावली",
      consent: "सहमति",
      confirmation: "पुष्टि",
    },
    common: { back: "पीछे", continue: "आगे बढ़ें" },
    language: {
      title: "अपनी भाषा चुनें",
      help: "आप इसे कभी भी बदल सकते हैं।",
      welcomeTitle: "शुरू करने से पहले",
      welcomeBody:
        "यह पंजीकरण हमारे पंजीकार व्यक्तिगत रूप से संभालते हैं। यहाँ कुछ भी सार्वजनिक नहीं है, और जब तक परिवार सहमत न हो, कुछ भी साझा नहीं किया जाता।",
    },
    guardian: {
      kicker: "अभिभावक एवं परिवार विवरण",
      title: "परिवार की ओर से पंजीकरण कौन कर रहा है?",
      help: "अधिकांश परिवार माता-पिता या किसी बुजुर्ग के माध्यम से पंजीकरण कराते हैं। हमारे पंजीकार सबसे पहले इन्हीं से बात करेंगे।",
      nameLabel: "आपका पूरा नाम",
      namePlaceholder: "जैसे रमेश झा",
      relationLabel: "उम्मीदवार से आपका संबंध",
      relationPlaceholder: "जैसे पिता, माता, बड़े भाई, स्वयं",
      villageLabel: "गाँव / ग्राम",
      districtLabel: "जिला",
      phoneLabel: "फ़ोन नंबर",
      phonePlaceholder: "+91",
      emailLabel: "ईमेल (वैकल्पिक)",
    },
    candidate: {
      kicker: "उम्मीदवार के बारे में",
      title: "अब, उनके बारे में थोड़ा बताएं",
      help: "ये विवरण पंजीकार को यह समझने में मदद करते हैं कि वे किसके लिए उपयुक्त जोड़ा खोज रहे हैं।",
      fullNameLabel: "पूरा नाम",
      registeringAsLabel: "वे पंजीकरण करा रहे हैं",
      brideLabel: "वधू",
      groomLabel: "वर",
      dobLabel: "जन्म तिथि",
      cityLabel: "वर्तमान शहर",
      educationLabel: "शिक्षा",
      occupationLabel: "व्यवसाय",
      photoOptionalLabel: "एक तस्वीर (वैकल्पिक)",
      photoUploadLabel: "तस्वीर अपलोड करें",
      photoHelpText: "JPG या PNG, अधिकतम 5MB।",
      photoReplaceLabel: "बदलें",
      photoRemoveLabel: "हटाएँ",
      photoErrorType: "यह फ़ाइल प्रकार समर्थित नहीं है। कृपया JPG या PNG चुनें।",
      photoErrorSize: "यह तस्वीर 5MB से बड़ी है। कृपया छोटी तस्वीर चुनें।",
      photoPrivacyNote:
        "केवल किसी एक विशिष्ट परिवार के साथ, और केवल रिश्ता प्रस्तावित होने के बाद साझा की जाती है। कभी सार्वजनिक नहीं।",
      photoAltText: "उम्मीदवार का चित्र — केवल रिश्ता प्रस्तावित होने के समय साझा किया जाता है।",
    },
    preferences: {
      kicker: "वे किसकी तलाश में हैं",
      title: "उनके मन में क्या है, इसके बारे में थोड़ा",
      help: "यहाँ सब कुछ वैकल्पिक है और केवल पंजीकार प्रक्रिया को उपयुक्त जोड़ा खोजने में मदद के लिए उपयोग किया जाता है — यह कभी किसी और को नहीं दिखाया जाता।",
      ageMinLabel: "पसंदीदा आयु — से",
      ageMaxLabel: "पसंदीदा आयु — तक",
      locationLabel: "पसंदीदा स्थान",
      educationLabel: "पसंदीदा शिक्षा स्तर",
      optionalNote: "यदि कोई खास पसंद नहीं है तो खाली छोड़ दें।",
    },
    lineage: {
      kicker: "वंशावली",
      title: "पंजी के लिए पारिवारिक वंशावली",
      help: "इसका उपयोग केवल सपिंड संबंध जांचने के लिए किया जाता है — यह कभी भी संभावित रिश्ते को नहीं दिखाया जाता। जो जानते हैं वह भरें; बाकी में पंजीकार मदद कर सकते हैं।",
      gotraLabel: "गोत्र / मूल",
      moolGramLabel: "पैतृक गाँव (मूल ग्राम)",
      paternalTitle: "पितृ पक्ष",
      maternalTitle: "मातृ पक्ष",
      addGenerationLabel: "+ एक और पीढ़ी जोड़ें",
      fatherLabel: "पिता",
      grandfatherLabel: "दादा",
      greatGrandfatherLabel: "परदादा",
      nanaLabel: "नाना",
      maternalGrandfatherLabel: "नाना के पिता",
      namePlaceholder: "नाम",
      additionalAncestorLabelFn: (n) => `पूर्वज (पीढ़ी ${n})`,
    },
    consent: {
      kicker: "सहमति",
      titleFn: (name) => `यह हिस्सा केवल ${name} का है`,
      helpFn: (name) =>
        `अब तक सब कुछ अभिभावक द्वारा भरा गया है। इस पंजीकरण को स्वीकार करने से पहले, ${name} को अपने शब्दों में पुष्टि करनी चाहिए कि वे पंजीकरण के लिए सहमत हैं।`,
      agreeOption: "हाँ — मैं अपनी इच्छा से पंजीकरण के लिए सहमत हूँ।",
      notYetOption: "अभी नहीं — मुझे निर्णय लेने के लिए और समय चाहिए।",
      ownWordsLabel: "अपने शब्दों में बताएं कि आप सहमत हैं",
      ownWordsPlaceholder:
        "जैसे मैं, [नाम], विवाह हेतु उपयुक्त जोड़ा खोजने के लिए सभा गाछी के साथ पंजीकरण के लिए सहमत हूँ।",
      notYetHelp:
        "कोई बात नहीं। जब तक यह चरण पूरा नहीं होता, तब तक कुछ भी सबमिट नहीं किया जाएगा — जब भी तैयार हों, वापस आएं।",
      photoConsentNote:
        "यदि इस पंजीकरण में कोई तस्वीर जोड़ी गई है, तो वह केवल एक विशिष्ट परिवार को दिखाई जाएगी — उसी समय जब कोई रिश्ता प्रस्तावित हो — कभी सार्वजनिक रूप से नहीं, और कभी खोजी नहीं जा सकती। यदि कोई तस्वीर नहीं जोड़ी गई है, तो इस भाग को यों ही छोड़ा जा सकता है।",
      defaultName: "उम्मीदवार",
      submit: "पंजीकरण सबमिट करें",
      submitting: "सबमिट किया जा रहा है…",
    },
    confirmation: {
      kicker: "पंजीकरण प्राप्त हुआ",
      title: "आपका पंजीकरण हमारे पास है।",
      help: "आने वाले दिनों में एक पंजीकार विवरण और वंशावली की समीक्षा करेंगे। अभी कुछ और करने की आवश्यकता नहीं है — जैसे ही कुछ साझा करने योग्य होगा, हम सीधे अभिभावक से संपर्क करेंगे।",
      refLabel: "संदर्भ",
      footerHelp:
        "अभिभावक के साथ साझा किए जाने वाले निजी स्टेटस लिंक का उपयोग करके आप कभी भी इस पंजीकरण की स्थिति देख सकते हैं।",
    },
  },

  // --------------------------------------------------------- Maithili --
  mai: {
    brand: "सौराठ सभा गाछी",
    stepLabels: {
      language: "भाषा",
      guardian: "अभिभावकक विवरण",
      candidate: "उम्मीदवारक बारेमे",
      preferences: "जोड़ाक पसंद",
      lineage: "वंशावली",
      consent: "सहमति",
      confirmation: "पुष्टि",
    },
    common: { back: "पाछू", continue: "आगू बढ़ू" },
    language: {
      title: "अपन भाषा चुनू",
      help: "अहाँ एकरा कखनहुँ बदैल सकैत छी।",
      welcomeTitle: "शुरू करबाक पहिने",
      welcomeBody:
        "ई पंजीकरण हमर पंजीकार व्यक्तिगत रूपसँ देखैत छथि। इहाँ किछुओ सार्वजनिक नहि अछि, आ जाबे धरि परिवार सहमत नहि होइत, किछुओ साझा नहि कएल जाइत अछि।",
    },
    guardian: {
      kicker: "अभिभावक आ परिवारक विवरण",
      title: "परिवारक ओरसँ पंजीकरण के क' रहल अछि?",
      help: "बेसीतर परिवार माता-पिता वा कोनो बुजुर्गक माध्यमसँ पंजीकरण करबैत छथि। हमर पंजीकार सभसँ पहिने इनहिसँ बात करता।",
      nameLabel: "अहाँक पूरा नाम",
      namePlaceholder: "जेना रमेश झा",
      relationLabel: "उम्मीदवारसँ अहाँक संबंध",
      relationPlaceholder: "जेना पिता, माता, पैघ भाइ, स्वयं",
      villageLabel: "गाम / ग्राम",
      districtLabel: "जिला",
      phoneLabel: "फोन नंबर",
      phonePlaceholder: "+91",
      emailLabel: "ईमेल (वैकल्पिक)",
    },
    candidate: {
      kicker: "उम्मीदवारक बारेमे",
      title: "अखन, हुनका बारेमे किछु बताउ",
      help: "ई विवरण पंजीकारकेँ ई बुझबामे मदद करैत अछि जे ओ केकरा लेल उपयुक्त जोड़ा खोजि रहल छथि।",
      fullNameLabel: "पूरा नाम",
      registeringAsLabel: "ओ पंजीकरण करा रहल छथि",
      brideLabel: "वधू",
      groomLabel: "वर",
      dobLabel: "जन्म तिथि",
      cityLabel: "वर्तमान शहर",
      educationLabel: "शिक्षा",
      occupationLabel: "व्यवसाय",
      photoOptionalLabel: "एकटा फोटो (वैकल्पिक)",
      photoUploadLabel: "फोटो अपलोड करू",
      photoHelpText: "JPG वा PNG, अधिकतम 5MB।",
      photoReplaceLabel: "बदलू",
      photoRemoveLabel: "हटाउ",
      photoErrorType: "ई फ़ाइल प्रकार समर्थित नहि अछि। कृपया JPG वा PNG चुनू।",
      photoErrorSize: "ई फोटो 5MB सँ पैघ अछि। कृपया छोट फोटो चुनू।",
      photoPrivacyNote:
        "केवल कोनो एकटा विशिष्ट परिवारक संग, आ केवल रिश्ता प्रस्तावित भेलाक बाद साझा कएल जाइत अछि। कहियो सार्वजनिक नहि।",
      photoAltText: "उम्मीदवारक चित्र — केवल रिश्ता प्रस्तावित होइबाक समय साझा कएल जाइत अछि।",
    },
    preferences: {
      kicker: "ओ केकरा खोजि रहल छथि",
      title: "हुनका मोनमे की अछि, ओकर बारेमे किछु",
      help: "इहाँ सभटा वैकल्पिक अछि आ सिर्फ पंजीकार प्रक्रियाकेँ उपयुक्त जोड़ा खोजबामे मदद लेल उपयोग होइत अछि — ई कहियो केओ आर केँ नहि देखाओल जाइत अछि।",
      ageMinLabel: "पसंदीदा आयु — सँ",
      ageMaxLabel: "पसंदीदा आयु — धरि",
      locationLabel: "पसंदीदा स्थान",
      educationLabel: "पसंदीदा शिक्षा स्तर",
      optionalNote: "जँ कोनो खास पसंद नहि अछि त' खाली छोड़ू।",
    },
    lineage: {
      kicker: "वंशावली",
      title: "पंजीक लेल पारिवारिक वंशावली",
      help: "एकर उपयोग सिर्फ सपिंड संबंध जाँचबाक लेल होइत अछि — ई कहियो संभावित रिश्तादारकेँ नहि देखाओल जाइत अछि। जे जानैत छी से भरू; बाकीमे पंजीकार मदद क' सकैत छथि।",
      gotraLabel: "गोत्र / मूल",
      moolGramLabel: "पैतृक गाम (मूल ग्राम)",
      paternalTitle: "पितृ पक्ष",
      maternalTitle: "मातृ पक्ष",
      addGenerationLabel: "+ आर एक पीढ़ी जोड़ू",
      fatherLabel: "पिता",
      grandfatherLabel: "दादा",
      greatGrandfatherLabel: "परदादा",
      nanaLabel: "नाना",
      maternalGrandfatherLabel: "नानाक पिता",
      namePlaceholder: "नाम",
      additionalAncestorLabelFn: (n) => `पुरखा (पीढ़ी ${n})`,
    },
    consent: {
      kicker: "सहमति",
      titleFn: (name) => `ई हिस्सा सिर्फ ${name}क अछि`,
      helpFn: (name) =>
        `एतय धरि सभटा अभिभावक द्वारा भरल गेल अछि। ई पंजीकरण स्वीकार करबासँ पहिने, ${name}केँ अपन शब्दमे पुष्टि करबाक चाही जे ओ पंजीकरण लेल सहमत छथि।`,
      agreeOption: "हँ — हम अपन इच्छासँ पंजीकरण लेल सहमत छी।",
      notYetOption: "अखन नहि — हमरा निर्णय लेबाक लेल आर समय चाही।",
      ownWordsLabel: "अपन शब्दमे बताउ जे अहाँ सहमत छी",
      ownWordsPlaceholder:
        "जेना हम, [नाम], विवाहक लेल उपयुक्त जोड़ा खोजबाक हेतु सभा गाछीक संग पंजीकरण लेल सहमत छी।",
      notYetHelp:
        "कोनो बात नहि। जाबे धरि ई चरण पूरा नहि होइत अछि, ताबे धरि किछुओ जमा नहि कएल जेतैक — जखन तैयार होइ त' वापस आउ।",
      photoConsentNote:
        "जँ ई पंजीकरणमे कोनो फोटो जोड़ल गेल अछि, तँ ओ केवल एकटा विशिष्ट परिवारकेँ देखाओल जेतै — सेहो समय पर जब कोनो रिश्ता प्रस्तावित होइत — कहियो सार्वजनिक रूपसँ नहि, आ कहियो खोजल नहि जाइत अछि। जँ कोनो फोटो नहि जोड़ल गेल अछि, तँ ई हिस्सा यहिना छोड़ल जा सकैत अछि।",
      defaultName: "उम्मीदवार",
      submit: "पंजीकरण जमा करू",
      submitting: "जमा कएल जा रहल अछि…",
    },
    confirmation: {
      kicker: "पंजीकरण प्राप्त भेल",
      title: "अहाँक पंजीकरण हमरा लग अछि।",
      help: "आगामी दिनमे एकटा पंजीकार विवरण आ वंशावलीक समीक्षा करता। अखन आर किछु करबाक आवश्यकता नहि अछि — जखने किछु साझा करबा योग्य हएत, हम सीधा अभिभावकसँ संपर्क करब।",
      refLabel: "संदर्भ",
      footerHelp:
        "अभिभावकक संग साझा कएल जाएत निजी स्टेटस लिंकक उपयोग क' क' अहाँ कखनहुँ ई पंजीकरणक स्थिति देख सकैत छी।",
    },
  },
};

// ------------------------------------------------------------- Data --

interface GuardianDetails {
  name: string;
  relationToCandidate: string;
  village: string;
  district: string;
  phone: string;
  email: string;
}

type Gender = "" | "Bride" | "Groom";

/** A single uploaded photo. Mock-only — a real build would store a URL, not a data URL. */
interface CandidatePhoto {
  name: string;
  dataUrl: string;
}

interface CandidateDetails {
  fullName: string;
  gender: Gender;
  dob: string;
  education: string;
  occupation: string;
  currentCity: string;
  /** Optional single photo. Never shown in a grid; only to one family at proposal time. */
  photo: CandidatePhoto | null;
}

/** What the family is looking for in a match. All fields optional — refined with the panjikar. */
interface PartnerPreferences {
  ageMin: string;
  ageMax: string;
  location: string;
  education: string;
}

type AncestorLabelKey =
  | "father"
  | "grandfather"
  | "greatGrandfather"
  | "nana"
  | "maternalGrandfather"
  | "custom";

interface LineageEntry {
  labelKey: AncestorLabelKey;
  customLabel?: string; // only used when labelKey === "custom"
  name: string;
}

type LineageSide = "paternal" | "maternal";

interface Lineage {
  gotra: string;
  moolGram: string;
  paternal: LineageEntry[];
  maternal: LineageEntry[];
}

const initialLineage: Lineage = {
  gotra: "",
  moolGram: "",
  paternal: [
    { labelKey: "father", name: "" },
    { labelKey: "grandfather", name: "" },
    { labelKey: "greatGrandfather", name: "" },
  ],
  maternal: [
    { labelKey: "nana", name: "" },
    { labelKey: "maternalGrandfather", name: "" },
  ],
};

const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // 5MB
const ACCEPTED_PHOTO_TYPES = ["image/jpeg", "image/png"];

function getAncestorLabel(t: CopyStrings, entry: LineageEntry): string {
  switch (entry.labelKey) {
    case "father":
      return t.lineage.fatherLabel;
    case "grandfather":
      return t.lineage.grandfatherLabel;
    case "greatGrandfather":
      return t.lineage.greatGrandfatherLabel;
    case "nana":
      return t.lineage.nanaLabel;
    case "maternalGrandfather":
      return t.lineage.maternalGrandfatherLabel;
    case "custom":
      return entry.customLabel ?? "";
    default:
      return "";
  }
}

type ConsentChoice = "" | "agree" | "not-yet";

interface ConsentState {
  choice: ConsentChoice;
  ownWords: string;
}

// ---------------------------------------------------------------- Root --

export default function RegistrationFlow(): React.ReactElement {
  const [stepIndex, setStepIndex] = useState<number>(0);
  const [language, setLanguage] = useState<LanguageCode>("en");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [registrationId, setRegistrationId] = useState<string | null>(null);

  const [guardian, setGuardian] = useState<GuardianDetails>({
    name: "",
    relationToCandidate: "",
    village: "",
    district: "",
    phone: "",
    email: "",
  });

  const [candidate, setCandidate] = useState<CandidateDetails>({
    fullName: "",
    gender: "",
    dob: "",
    education: "",
    occupation: "",
    currentCity: "",
    photo: null,
  });

  const [preferences, setPreferences] = useState<PartnerPreferences>({
    ageMin: "",
    ageMax: "",
    location: "",
    education: "",
  });

  const [lineage, setLineage] = useState<Lineage>(initialLineage);

  const [consent, setConsent] = useState<ConsentState>({
    choice: "",
    ownWords: "",
  });

  const t = COPY[language] || COPY.en;
  const step = STEP_ORDER[stepIndex];

  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));

  const updateAncestor = (side: LineageSide, idx: number, value: string) => {
    setLineage((prev) => {
      const list = [...prev[side]];
      list[idx] = { ...list[idx], name: value };
      return { ...prev, [side]: list };
    });
  };

  const addAncestor = (side: LineageSide) => {
    setLineage((prev) => {
      const nextGeneration = prev[side].length + 1;
      return {
        ...prev,
        [side]: [
          ...prev[side],
          {
            labelKey: "custom" as const,
            customLabel: t.lineage.additionalAncestorLabelFn(nextGeneration),
            name: "",
          },
        ],
      };
    });
  };

  const canSubmitConsent =
    consent.choice === "agree" && consent.ownWords.trim().length > 0;

  const handleFinalSubmit = async () => {
    setSubmitting(true);
    try {
      const payload = buildRegistrationPayload(
        language,
        guardian,
        candidate,
        preferences,
        lineage,
        consent,
        t
      );
      const result = await submitRegistration(payload);
      setRegistrationId(result.reference);
      goNext();
    } catch (err) {
      if (err instanceof ApiError) {
        console.error("Registration validation failed:", err.body);
      } else {
        console.error("Registration submission failed:", err);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="container py-16">
      <p className="text-caption text-text/60 tracking-wider mb-2">{t.brand}</p>
      <p className="text-caption text-text/60 mb-8">{t.stepLabels[step]}</p>
      <div className="card max-w-[620px]">
        {step === "language" && (
          <LanguageStep language={language} setLanguage={setLanguage} t={t} onNext={goNext} />
        )}

        {step === "guardian" && (
          <GuardianStep data={guardian} setData={setGuardian} t={t} onNext={goNext} onBack={goBack} />
        )}

        {step === "candidate" && (
          <CandidateStep data={candidate} setData={setCandidate} t={t} onNext={goNext} onBack={goBack} />
        )}

        {step === "preferences" && (
          <PreferencesStep data={preferences} setData={setPreferences} t={t} onNext={goNext} onBack={goBack} />
        )}

        {step === "lineage" && (
          <LineageStep
            lineage={lineage}
            t={t}
            updateAncestor={updateAncestor}
            addAncestor={addAncestor}
            onNext={goNext}
            onBack={goBack}
          />
        )}

        {step === "consent" && (
          <ConsentStep
            candidateName={candidate.fullName}
            consent={consent}
            setConsent={setConsent}
            t={t}
            canSubmit={canSubmitConsent}
            submitting={submitting}
            onSubmit={handleFinalSubmit}
            onBack={goBack}
          />
        )}

        {step === "confirmation" && <ConfirmationStep registrationId={registrationId} t={t} />}
      </div>
    </main>
  );
}

// ---------------------------------------------------------------- Steps --

interface LanguageStepProps {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: CopyStrings;
  onNext: () => void;
}

function LanguageStep({ language, setLanguage, t, onNext }: LanguageStepProps) {
  const options: { code: LanguageCode; label: string; sub: string }[] = [
    { code: "mai", label: "मैथिली", sub: "Maithili" },
    { code: "hi", label: "हिन्दी", sub: "Hindi" },
    { code: "en", label: "English", sub: "" },
  ];
  return (
    <section>
      <h1 className="text-heading text-primary leading-tight mb-3">{t.language.title}</h1>
      <p className="text-body leading-relaxed mb-8">{t.language.help}</p>

      <div className="flex flex-col gap-3 mb-8" role="radiogroup" aria-label="Language">
        {options.map((opt) => (
          <button
            key={opt.code}
            type="button"
            role="radio"
            aria-checked={language === opt.code}
            className={language === opt.code ? "btn-primary text-left" : "btn-outline text-left"}
            onClick={() => setLanguage(opt.code)}
          >
            {opt.label}
            {opt.sub ? ` · ${opt.sub}` : ""}
          </button>
        ))}
      </div>

      <div className="quote-block mb-8">
        <p className="text-body font-semibold mb-1">{t.language.welcomeTitle}</p>
        <p className="text-body leading-relaxed">{t.language.welcomeBody}</p>
      </div>

      <div className="flex justify-end border-t border-border pt-6">
        <button type="button" className="btn-primary" onClick={onNext}>
          {t.common.continue}
        </button>
      </div>
    </section>
  );
}

interface GuardianStepProps {
  data: GuardianDetails;
  setData: (data: GuardianDetails) => void;
  t: CopyStrings;
  onNext: () => void;
  onBack: () => void;
}

function GuardianStep({ data, setData, t, onNext, onBack }: GuardianStepProps) {
  const set =
    (k: keyof GuardianDetails) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setData({ ...data, [k]: e.target.value });

  const valid = Boolean(
    data.name.trim() && data.phone.trim() && data.relationToCandidate.trim()
  );

  return (
    <section>
      <p className="text-caption text-text/60 tracking-wider mb-3">{t.guardian.kicker}</p>
      <h1 className="text-heading text-primary leading-tight mb-3">{t.guardian.title}</h1>
      <p className="text-body leading-relaxed mb-8">{t.guardian.help}</p>

      <div className="field">
        <label className="label">{t.guardian.nameLabel}</label>
        <input className="input" value={data.name} onChange={set("name")} placeholder={t.guardian.namePlaceholder} />
      </div>

      <div className="field">
        <label className="label">{t.guardian.relationLabel}</label>
        <input
          className="input"
          value={data.relationToCandidate}
          onChange={set("relationToCandidate")}
          placeholder={t.guardian.relationPlaceholder}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="field">
          <label className="label">{t.guardian.villageLabel}</label>
          <input className="input" value={data.village} onChange={set("village")} />
        </div>
        <div className="field">
          <label className="label">{t.guardian.districtLabel}</label>
          <input className="input" value={data.district} onChange={set("district")} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="field">
          <label className="label">{t.guardian.phoneLabel}</label>
          <input className="input" value={data.phone} onChange={set("phone")} placeholder={t.guardian.phonePlaceholder} />
        </div>
        <div className="field">
          <label className="label">{t.guardian.emailLabel}</label>
          <input className="input" value={data.email} onChange={set("email")} />
        </div>
      </div>

      <div className="flex justify-between items-center border-t border-border pt-6 mt-2">
        <button type="button" className="btn-outline" onClick={onBack}>{t.common.back}</button>
        <button type="button" className="btn-primary" disabled={!valid} onClick={onNext}>
          {t.common.continue}
        </button>
      </div>
    </section>
  );
}

interface CandidateStepProps {
  data: CandidateDetails;
  setData: (data: CandidateDetails) => void;
  t: CopyStrings;
  onNext: () => void;
  onBack: () => void;
}

function CandidateStep({ data, setData, t, onNext, onBack }: CandidateStepProps) {
  const set =
    (k: keyof CandidateDetails) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setData({ ...data, [k]: e.target.value });

  const valid = Boolean(data.fullName.trim() && data.gender && data.dob);

  const genderLabel = (g: Gender): string =>
    g === "Bride" ? t.candidate.brideLabel : g === "Groom" ? t.candidate.groomLabel : "";

  return (
    <section>
      <p className="text-caption text-text/60 tracking-wider mb-3">{t.candidate.kicker}</p>
      <h1 className="text-heading text-primary leading-tight mb-3">{t.candidate.title}</h1>
      <p className="text-body leading-relaxed mb-8">{t.candidate.help}</p>

      <div className="field">
        <label className="label">{t.candidate.fullNameLabel}</label>
        <input className="input" value={data.fullName} onChange={set("fullName")} />
      </div>

      <div className="field">
        <label className="label">{t.candidate.registeringAsLabel}</label>
        <div className="flex flex-wrap gap-3">
          {(["Bride", "Groom"] as Gender[]).map((g) => (
            <button
              type="button"
              key={g}
              className={data.gender === g ? "btn-primary" : "btn-outline"}
              onClick={() => setData({ ...data, gender: g })}
            >
              {genderLabel(g)}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="field">
          <label className="label">{t.candidate.dobLabel}</label>
          <input className="input" type="date" value={data.dob} onChange={set("dob")} />
        </div>
        <div className="field">
          <label className="label">{t.candidate.cityLabel}</label>
          <input className="input" value={data.currentCity} onChange={set("currentCity")} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="field">
          <label className="label">{t.candidate.educationLabel}</label>
          <input className="input" value={data.education} onChange={set("education")} />
        </div>
        <div className="field">
          <label className="label">{t.candidate.occupationLabel}</label>
          <input className="input" value={data.occupation} onChange={set("occupation")} />
        </div>
      </div>

      <PhotoField
        photo={data.photo}
        onChange={(photo) => setData({ ...data, photo })}
        t={t}
      />

      <div className="flex justify-between items-center border-t border-border pt-6 mt-2">
        <button type="button" className="btn-outline" onClick={onBack}>{t.common.back}</button>
        <button type="button" className="btn-primary" disabled={!valid} onClick={onNext}>
          {t.common.continue}
        </button>
      </div>
    </section>
  );
}

interface PreferencesStepProps {
  data: PartnerPreferences;
  setData: (data: PartnerPreferences) => void;
  t: CopyStrings;
  onNext: () => void;
  onBack: () => void;
}

function PreferencesStep({ data, setData, t, onNext, onBack }: PreferencesStepProps) {
  const set =
    (k: keyof PartnerPreferences) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setData({ ...data, [k]: e.target.value });

  return (
    <section>
      <style>{STYLES}</style>
      <p className="mh-kicker" data-accent="mango">{t.preferences.kicker}</p>
      <h1 className="mh-title">{t.preferences.title}</h1>
      <p className="mh-help">{t.preferences.help}</p>

      <div className="mh-field-row">
        <div className="mh-field">
          <label>{t.preferences.ageMinLabel}</label>
          <input type="number" value={data.ageMin} onChange={set("ageMin")} min={18} />
        </div>
        <div className="mh-field">
          <label>{t.preferences.ageMaxLabel}</label>
          <input type="number" value={data.ageMax} onChange={set("ageMax")} min={18} />
        </div>
      </div>

      <div className="mh-field">
        <label>{t.preferences.locationLabel}</label>
        <input value={data.location} onChange={set("location")} />
      </div>

      <div className="mh-field">
        <label>{t.preferences.educationLabel}</label>
        <input value={data.education} onChange={set("education")} />
      </div>

      <p className="mh-help mh-help-muted">{t.preferences.optionalNote}</p>

      <div className="mh-actions">
        <button className="mh-btn mh-btn-ghost" onClick={onBack}>{t.common.back}</button>
        <button className="mh-btn mh-btn-primary" onClick={onNext}>{t.common.continue}</button>
      </div>
    </section>
  );
}

interface PhotoFieldProps {
  photo: CandidatePhoto | null;
  onChange: (photo: CandidatePhoto | null) => void;
  t: CopyStrings;
}

function PhotoField({ photo, onChange, t }: PhotoFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File | undefined) => {
    if (!file) return;

    if (!ACCEPTED_PHOTO_TYPES.includes(file.type)) {
      setError(t.candidate.photoErrorType);
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      setError(t.candidate.photoErrorSize);
      return;
    }

    setError(null);
    onChange({ name: file.name, dataUrl: URL.createObjectURL(file) });
  };

  const removePhoto = () => {
    if (photo) URL.revokeObjectURL(photo.dataUrl);
    setError(null);
    onChange(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="field">
      <p className="label">{t.candidate.photoOptionalLabel}</p>

      {photo ? (
        <div className="flex flex-wrap items-start gap-4">
          <img
            src={photo.dataUrl}
            alt={t.candidate.photoAltText}
            className="h-36 w-28 rounded-lg object-cover"
          />
          <div className="flex flex-col items-start gap-3 pt-1">
            <button type="button" className="btn-outline" onClick={() => inputRef.current?.click()}>
              {t.candidate.photoReplaceLabel}
            </button>
            <button type="button" className="btn-quiet" onClick={removePhoto}>
              {t.candidate.photoRemoveLabel}
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="btn-outline" onClick={() => inputRef.current?.click()}>
          {t.candidate.photoUploadLabel}
        </button>
      )}

      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        accept="image/jpeg,image/png"
        onChange={(event) => handleFile(event.target.files?.[0])}
      />
      <p className="field-hint">{t.candidate.photoHelpText}</p>
      <p className="field-hint">{t.candidate.photoPrivacyNote}</p>
      {error && <p className="field-hint text-primary">{error}</p>}
    </div>
  );
}

interface LineageStepProps {
  lineage: Lineage;
  t: CopyStrings;
  updateAncestor: (side: LineageSide, idx: number, value: string) => void;
  addAncestor: (side: LineageSide) => void;
  onNext: () => void;
  onBack: () => void;
}

function LineageStep({ lineage, t, updateAncestor, addAncestor, onNext, onBack }: LineageStepProps) {
  return (
    <section>
      <p className="text-caption text-text/60 tracking-wider mb-3">{t.lineage.kicker}</p>
      <h1 className="text-heading text-primary leading-tight mb-3">{t.lineage.title}</h1>
      <p className="text-body leading-relaxed mb-8">{t.lineage.help}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="field">
          <label className="label">{t.lineage.gotraLabel}</label>
          <input className="input" value={lineage.gotra} onChange={() => {}} />
        </div>
        <div className="field">
          <label className="label">{t.lineage.moolGramLabel}</label>
          <input className="input" value={lineage.moolGram} onChange={() => {}} />
        </div>
      </div>

      <LineageTree
        title={t.lineage.paternalTitle}
        entries={lineage.paternal}
        t={t}
        onChange={(idx, val) => updateAncestor("paternal", idx, val)}
        onAdd={() => addAncestor("paternal")}
      />

      <LineageTree
        title={t.lineage.maternalTitle}
        entries={lineage.maternal}
        t={t}
        onChange={(idx, val) => updateAncestor("maternal", idx, val)}
        onAdd={() => addAncestor("maternal")}
      />

      <div className="flex justify-between items-center border-t border-border pt-6 mt-2">
        <button type="button" className="btn-outline" onClick={onBack}>{t.common.back}</button>
        <button type="button" className="btn-primary" onClick={onNext}>{t.common.continue}</button>
      </div>
    </section>
  );
}

interface LineageTreeProps {
  title: string;
  entries: LineageEntry[];
  t: CopyStrings;
  onChange: (idx: number, value: string) => void;
  onAdd: () => void;
}

function LineageTree({ title, entries, t, onChange, onAdd }: LineageTreeProps) {
  return (
    <div className="mb-8">
      <p className="text-body font-semibold mb-3">{title}</p>
      <ol className="flex flex-col">
        {entries.map((entry, idx) => (
          <li key={idx} className="field">
            <label className="label">{getAncestorLabel(t, entry)}</label>
            <input
              className="input"
              value={entry.name}
              onChange={(e) => onChange(idx, e.target.value)}
              placeholder={t.lineage.namePlaceholder}
            />
          </li>
        ))}
      </ol>
      <button type="button" className="btn-quiet" onClick={onAdd}>
        {t.lineage.addGenerationLabel}
      </button>
    </div>
  );
}

interface ConsentStepProps {
  candidateName: string;
  consent: ConsentState;
  setConsent: (c: ConsentState) => void;
  t: CopyStrings;
  canSubmit: boolean;
  submitting: boolean;
  onSubmit: () => void;
  onBack: () => void;
}

function ConsentStep({
  candidateName,
  consent,
  setConsent,
  t,
  canSubmit,
  submitting,
  onSubmit,
  onBack,
}: ConsentStepProps) {
  const name = candidateName || t.consent.defaultName;
  return (
    <section>
      <p className="text-caption text-text/60 tracking-wider mb-3">{t.consent.kicker}</p>
      <h1 className="text-heading text-primary leading-tight mb-3">{t.consent.titleFn(name)}</h1>
      <p className="text-body leading-relaxed mb-8">{t.consent.helpFn(name)}</p>

      <div className="flex flex-col gap-3 mb-6" role="radiogroup" aria-label="Consent">
        <button
          type="button"
          role="radio"
          aria-checked={consent.choice === "agree"}
          className={consent.choice === "agree" ? "btn-primary text-left" : "btn-outline text-left"}
          onClick={() => setConsent({ ...consent, choice: "agree" })}
        >
          {t.consent.agreeOption}
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={consent.choice === "not-yet"}
          className={consent.choice === "not-yet" ? "btn-primary text-left" : "btn-outline text-left"}
          onClick={() => setConsent({ ...consent, choice: "not-yet" })}
        >
          {t.consent.notYetOption}
        </button>
      </div>

      {consent.choice === "agree" && (
        <div className="field">
          <label className="label">{t.consent.ownWordsLabel}</label>
          <textarea
            className="textarea"
            rows={3}
            value={consent.ownWords}
            onChange={(e) => setConsent({ ...consent, ownWords: e.target.value })}
            placeholder={t.consent.ownWordsPlaceholder}
          />
        </div>
      )}

      {consent.choice === "not-yet" && (
        <p className="text-body text-text/55 leading-relaxed mb-6">{t.consent.notYetHelp}</p>
      )}

      <div className="quote-block mb-6">
        <p className="text-body leading-relaxed">{t.consent.photoConsentNote}</p>
      </div>

      <div className="flex justify-between items-center border-t border-border pt-6 mt-2">
        <button type="button" className="btn-outline" onClick={onBack}>{t.common.back}</button>
        <button
          type="button"
          className="btn-primary"
          disabled={!canSubmit || submitting}
          onClick={onSubmit}
        >
          {submitting ? t.consent.submitting : t.consent.submit}
        </button>
      </div>
    </section>
  );
}

interface ConfirmationStepProps {
  registrationId: string | null;
  t: CopyStrings;
}

function ConfirmationStep({ registrationId, t }: ConfirmationStepProps) {
  return (
    <section>
      <p className="text-caption text-text/60 tracking-wider mb-3">{t.confirmation.kicker}</p>
      <h1 className="text-heading text-primary leading-tight mb-3">{t.confirmation.title}</h1>
      <p className="text-body leading-relaxed mb-6">{t.confirmation.help}</p>

      {registrationId && (
        <div className="card mb-6">
          <span className="label">{t.confirmation.refLabel}</span>
          <strong className="text-body text-primary">{registrationId}</strong>
        </div>
      )}

      <p className="text-body text-text/55 leading-relaxed">{t.confirmation.footerHelp}</p>
    </section>
  );
}

// ---------------------------------------------------------------- Styles --

const STYLES = `
:root {
  --sindoor: #7A1F2E;
  --turmeric: #DD9A34;
  --mango: #5B7A3A;
  --ink: #3B2A1E;
  --paper: #FDFBF8;
  --paper-alt: #FDFBF8;
  --line: #E7E1D8;
}

.mh-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.mh-kicker[data-accent="mango"] { color: var(--mango); }

.mh-title {
  font-family: Georgia, "Times New Roman", serif;
  color: var(--sindoor);
  font-size: 24px;
  line-height: 1.25;
  margin: 0 0 10px;
}

.mh-help {
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink);
  margin: 0 0 24px;
}
.mh-help-muted {
  color: var(--ink);
  opacity: 0.6;
  margin-bottom: 0;
}

.mh-field-row {
  display: flex;
  gap: 16px;
}
.mh-field-row .mh-field {
  flex: 1;
}

.mh-field { margin-bottom: 20px; }
.mh-field label {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--ink);
  opacity: 0.75;
}
.mh-field input, .mh-field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--line);
  background: var(--paper-alt);
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  color: var(--ink);
  resize: vertical;
}
.mh-field input:focus, .mh-field textarea:focus {
  outline: 2px solid color-mix(in srgb, var(--sindoor) 22%, transparent);
  outline-offset: 1px;
  border-color: var(--sindoor);
}

.mh-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.mh-btn {
  border: 1px solid var(--ink);
  background: transparent;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease,
    border-color 0.15s ease, transform 0.15s ease;
}
.mh-btn:active {
  transform: translateY(1px);
}
.mh-btn-primary {
  background: var(--sindoor);
  border-color: var(--sindoor);
  color: var(--paper);
}
.mh-btn-primary:not(:disabled):hover {
  background: #63182A;
  border-color: #63182A;
}
.mh-btn-primary:disabled {
  background: var(--line);
  border-color: var(--line);
  cursor: not-allowed;
}
.mh-btn-ghost {
  border-color: var(--line);
  color: #6b5d4d;
  background: transparent;
}
.mh-btn-ghost:not(:disabled):hover {
  border-color: var(--ink);
  color: var(--ink);
}
`;