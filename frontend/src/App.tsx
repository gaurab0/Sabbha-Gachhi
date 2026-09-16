import { useState } from "react";
import {
  Link,
  Outlet,
  Route,
  Routes,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import AboutPage from "./components/AboutPage";
import SupportPage from "./components/Donation";
import SaurathMelaPage from "./components/Mela";
import MatchProposalScreen from "./components/MatchProposalScreen";
import PanjikarPage from "./components/PanjikarPage";
import ReportConcernForm from "./components/ReportConcernForm";
import RegistrationFlow from "./components/RegistrationFlow";
import StatusPage from "./components/StatusPage";
import { submitConcernReport } from "./api/registration";
import { Footer, Navbar } from "./components/chrome";

function PublicLayout() {
  return (
    <>
      <Navbar />
      <Outlet />
      <Footer />
    </>
  );
}

function LandingPage() {
  return (
    <>
      <section className="hero-section">
        <div className="container">
          <div className="hero-inner">
            <p className="hero-eyebrow">
              <span aria-hidden="true" className="hero-eyebrow-rule" />
              Saurath Sabha Gachhi Panji Tradition
              <span aria-hidden="true" className="hero-eyebrow-rule" />
            </p>
            <h1 className="hero-title">
              Continuing a Tradition of
              <br />
              <em>Dignified Matchmaking</em>
            </h1>
            <p className="hero-subtitle">
              A private, non-profit platform preserving the seven-century panji
              tradition — dowry-free, genealogy-verified matchmaking by
              invitation only.
            </p>
            <div className="hero-actions">
              <Link to="/register" className="btn-primary">
                Request an Invitation
              </Link>
              <Link to="/about" className="btn-ghost">
                Read Our Charter
              </Link>
            </div>
            <dl className="hero-proof">
              <div className="hero-proof-item">
                <dt>Origin &amp; History</dt>
                <dd>
                  Centuries of community assembly in the shade of
                  Saurath&rsquo;s orchards
                </dd>
              </div>
              <div className="hero-proof-item">
                <dt>Uncompromising Ethic</dt>
                <dd>
                  Strictly dowry-free introductions anchored in mutual respect
                </dd>
              </div>
              <div className="hero-proof-item">
                <dt>Record Verification</dt>
                <dd>
                  Multi-generational genealogy authenticated by authorized
                  Panjikars
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      <section id="tradition" className="tradition-section">
        <div className="container tradition-grid max-w-6xl">
          <div>
            <p className="section-eyebrow">
              <span aria-hidden="true" className="hero-eyebrow-rule" />§ 01 —
              The Tradition
            </p>
            <h2 className="tradition-title">
              Before there were profiles,
              <br />
              there were panjis.
            </h2>
            <div className="tradition-body">
              <p>
                Every family keeps its story in the panji — a handwritten
                registry maintained across generations by hereditary
                genealogists, the panjikars. Before any marriage, the record is
                consulted: which line is unbroken, which branch may join which.
              </p>
              <p>
                Saurath Sabha Gachhi was where that consultation became a
                congregation. Families gathering beneath the mango orchard, the
                gachhi, meeting panjikars face to face with the panji open
                before them.
              </p>
            </div>
          </div>
          <dl className="tradition-faq">
            <div className="tradition-faq-item">
              <dt>What is the Sabha?</dt>
              <dd>
                The historic gathering of Maithil families in Saurath where
                matches were arranged with the consent and verified backing of
                the community.
              </dd>
            </div>
            <div className="tradition-faq-item">
              <dt>What is the Panji?</dt>
              <dd>
                A family&rsquo;s authentic genealogical record, kept, updated,
                and carefully cross-verified by traditional panjikars.
              </dd>
            </div>
            <div className="tradition-faq-item">
              <dt>What has changed?</dt>
              <dd>
                Nothing essential. The same sacred rules of lineage and honor
                apply — carried thoughtfully onto a quieter, secure modern
                platform.
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="border-t border-border">
        <div className="max-w-255 mx-auto text-center py-20 md:py-28">
          <blockquote className="m-0 flex flex-col items-center gap-4">
            <p className="m-0 italic text-balance text-[clamp(1.5rem,3.4vw,2.1rem)] leading-[1.45] text-text/90">
              &ldquo;We are not a dating service. We are a family record, opened
              carefully, for one purpose.&rdquo;
            </p>
            <footer className="text-[0.78rem] font-medium uppercase tracking-[0.14em] text-text/55">
              — The Sabha Charter
            </footer>
          </blockquote>
        </div>
      </section>

      <section id="how-it-works" className="border-t border-border">
        <div className="container max-w-6xl text-center py-16 md:py-24">
          <p className="m-0 mb-5 flex items-center justify-center gap-3 text-[0.78rem] font-medium uppercase tracking-[0.14em] text-text/60">
            <span aria-hidden="true" className="hero-eyebrow-rule" />§ 02 — The
            Method
          </p>
          <h2 className="m-0 mb-4 font-medium tracking-[-0.01em] text-primary text-[clamp(1.8rem,3vw,2.4rem)]">
            How Sabha Gachhi Works
          </h2>
          <p className="mx-auto mb-12 md:mb-14 max-w-140 leading-[1.65] text-text/75">
            A deliberate, three-stage pathway designed for utmost solemnity and
            authentic verification.
          </p>
          <ol className="m-0 grid list-none gap-5 p-0 text-left md:grid-cols-3">
            {[
              {
                stage: "Stage 01",
                title: "Invitation from Community",
                body: "Access is extended solely through verified families already within the Sabha circle. There is no open registration or public listing.",
              },
              {
                stage: "Stage 02",
                title: "Panji Verification",
                body: "Your family's ancestral records (mool and gotra) are examined and certified through our network of recognized genealogists (*Panjikars*).",
              },
              {
                stage: "Stage 03",
                title: "Facilitated Introductions",
                body: "Once genealogy and non-negotiable dowry-free commitments are affirmed, introductions take place discreetly between respected families.",
              },
            ].map((step) => (
              <li
                key={step.stage}
                className="rounded-lg border border-border p-7">
                <p className="m-0 mb-3 text-[0.75rem] font-semibold uppercase tracking-[0.12em] text-primary">
                  {step.stage}
                </p>
                <h3 className="m-0 mb-3 text-[1.15rem] font-semibold leading-snug">
                  {step.title}
                </h3>
                <p className="m-0 text-[0.98rem] leading-[1.65] text-text/80">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="about" className="border-t border-border">
        <div className="container grid max-w-255 items-start gap-12 py-16 md:grid-cols-[0.8fr_1.4fr] md:gap-16 md:py-24 lg:gap-20">
          <div>
            <p className="m-0 mb-5 flex items-center gap-3 text-[0.78rem] font-medium uppercase tracking-[0.14em] text-text/60">
              <span aria-hidden="true" className="hero-eyebrow-rule" />§ 03 —
              Core Standards
            </p>
            <h2 className="m-0 font-medium tracking-[-0.01em] text-primary text-[clamp(1.8rem,3vw,2.4rem)] leading-[1.2]">
              Our Unbending
              <br />
              Principles
            </h2>
          </div>
          <div className="flex flex-col">
            {[
              {
                title: "Dowry-Free Commitment",
                body: "Participation requires an irrevocable personal commitment to zero dowry or financial demands in any form. We treat the commercialization of marriage as an affront to our lineage.",
              },
              {
                title: "Genealogical Authenticity",
                body: "Every introduction rests upon verified panji lineage, honoring the ancient scientific prevention of close consanguinity across seven paternal and maternal degrees.",
              },
              {
                title: "Mutual Dignity",
                body: "Both sides meet on equal terms as honored partners in community continuity, with decisions guided by mutual respect, temperament, and shared values.",
              },
            ].map((item, i, arr) => (
              <div
                key={item.title}
                className={
                  i < arr.length - 1 ? "mb-8 border-b border-border pb-8" : ""
                }>
                <h3 className="m-0 mb-2.5 text-[1.15rem] font-semibold leading-snug">
                  {item.title}
                </h3>
                <p className="m-0 leading-[1.7] text-text/80">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="privacy" className="border-t border-border">
        <div className="container max-w-255 py-16 md:py-24">
          <p className="m-0 mb-5 flex items-center gap-3 text-[0.78rem] font-medium uppercase tracking-[0.14em] text-text/60">
            <span aria-hidden="true" className="hero-eyebrow-rule" />§ 04 —
            Transparency
          </p>
          <h2 className="m-0 mb-5 font-medium tracking-[-0.01em] text-primary text-[clamp(1.8rem,3vw,2.4rem)] leading-[1.2]">
            Absolute Discretion by Design
          </h2>
          <p className="m-0 mb-10 max-w-155 leading-[1.7] text-text/85">
            We recognize that family records and matrimonial inquiries require
            confidential stewardship. Our infrastructure is purpose-built to
            eliminate digital exposure.
          </p>
          <ul className="m-0 grid list-disc gap-x-12 gap-y-6 p-0 pl-5 marker:text-accent sm:grid-cols-2">
            {[
              "Zero searchable databases or publicly indexed candidate listings",
              "No commercial advertising, monetization, or third-party data broker sharing",
              "Strict non-profit governance overseen by respected community trustees",
              "Genealogy records guarded with the solemn discretion of traditional Panjikars",
            ].map((item) => (
              <li key={item} className="pl-1 leading-[1.65] text-text/85">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="border-t border-border">
        <div className="container max-w-160 text-center py-16 md:py-24">
          <h2 className="m-0 mb-4 font-medium tracking-[-0.01em] text-primary text-[clamp(1.7rem,3vw,2.2rem)] leading-tight">
            Continuing Lineage with Dignity
          </h2>
          <p className="m-0 mb-8 leading-[1.7] text-text/75">
            If your family upholds the dowry-free tradition and holds verified
            panji roots, request an introduction through a verified community
            sponsor.
          </p>
          <Link to="/register" className="btn-primary">
            Request an Invitation
          </Link>
        </div>
      </section>
    </>
  );
}

/**
 * Entry point for the bare "/status" route — no login system exists yet,
 * so this stands in for one: the family types in the private reference
 * they were given and we route them to their actual status page.
 */
function StatusLookup() {
  const navigate = useNavigate();
  const [reference, setReference] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = reference.trim();
    if (trimmed) {
      navigate(`/status/${trimmed}`);
    }
  };

  return (
    <section className="page-section">
      <div className="container max-w-120 text-center">
        <h1 className="text-heading text-primary mb-4">
          Check your registration status
        </h1>
        <p className="text-body mb-8 leading-relaxed">
          Enter the private reference that was shared with your family when you
          registered.
        </p>
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 items-center">
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="e.g. SG-482913"
            className="input w-full max-w-[320px]"
          />
          <button type="submit" className="btn-primary">
            View status
          </button>
        </form>
      </div>
    </section>
  );
}

function StatusRoute() {
  const navigate = useNavigate();
  const { reference } = useParams<{ reference: string }>();

  return (
    <StatusPage
      reference={reference ?? ""}
      onOpenMatchProposal={(matchId) => navigate(`/status/match/${matchId}`)}
      onReportConcern={() => navigate(`/concern?ref=${reference}`)}
    />
  );
}

function ProposalRoute() {
  const navigate = useNavigate();
  const { matchId } = useParams<{ matchId: string }>();
  return (
    <MatchProposalScreen
      matchId={matchId ?? ""}
      onBackToStatus={() => navigate(-1)}
    />
  );
}

function ConcernRoute() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const reference = searchParams.get("ref") ?? "";

  return (
    <ReportConcernForm
      registrationId={reference}
      onSubmit={async (submission) => {
        await submitConcernReport({
          registration_reference_text: submission.registrationId,
          topic: submission.topic,
          description: submission.description,
          contact_back: submission.contactBack,
        });
      }}
      onBackToStatus={() => navigate(-1)}
    />
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/mela" element={<SaurathMelaPage />} />
        <Route path="/register/*" element={<RegistrationFlow />} />
        <Route path="/status" element={<StatusLookup />} />
        <Route path="/status/:reference" element={<StatusRoute />} />
        <Route path="/status/match/:matchId" element={<ProposalRoute />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/concern" element={<ConcernRoute />} />
      </Route>
      <Route path="/panjikar/*" element={<PanjikarPage />} />
    </Routes>
  );
}
