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

      <section id="about" className="page-section border-t border-t-border">
        <div className="container">
          <h2 className="text-heading mb-4">Our Mission</h2>
          <p className="text-body max-w-[600px] leading-relaxed">
            For centuries, the Saurath Sabha Gachhi tradition has brought
            families together through genealogy-verified introductions — rooted
            in dignity, free from dowry. Sabha Gachhi continues this work in a
            private, non-profit setting.
          </p>
          <p className="text-body max-w-[600px] leading-relaxed mt-4">
            We are not a dating service. We are a community platform that
            respects the depth of family heritage in finding a life partner.
          </p>
        </div>
      </section>

      <section
        id="how-it-works"
        className="page-section border-t border-t-border">
        <div className="container">
          <h2 className="text-heading mb-8">How It Works</h2>
          <ol className="flex flex-col gap-7">
            {[
              {
                title: "Receive an Invitation",
                body: "Access is extended through existing members of the Sabha community. There is no public sign-up.",
              },
              {
                title: "Submit Family Genealogy",
                body: "Your family's panji record is submitted and verified through our established network of genealogists.",
              },
              {
                title: "Begin Introductions",
                body: "Once verified, we facilitate introductions between compatible families through the Sabha network.",
              },
            ].map((step, i) => (
              <li key={step.title} className="flex gap-5 items-start">
                <span className="step-number">{i + 1}</span>
                <div>
                  <h3 className="text-body font-semibold mb-1">{step.title}</h3>
                  <p className="text-body leading-relaxed">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="privacy" className="page-section border-t border-t-border">
        <div className="container">
          <div className="quote-block">
            <h2 className="text-heading mb-3">Your Privacy Is Absolute</h2>
            <ul className="flex flex-col gap-2">
              {[
                "Invite-only — no public profiles or searchable database",
                "No personal data is sold or shared with third parties",
                "Non-profit — no advertising, no monetization of your information",
                "Genealogy records are handled with the same discretion as the traditional Sabha",
              ].map((item) => (
                <li
                  key={item}
                  className="text-body relative pl-5 leading-relaxed">
                  <span className="absolute left-0 top-[0.55em] w-[5px] h-[5px] rounded-full bg-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
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
      <div className="container max-w-[480px] text-center">
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
