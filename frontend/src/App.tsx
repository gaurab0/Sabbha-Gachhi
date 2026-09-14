import { useState } from 'react'
import {
  Link,
  Outlet,
  Route,
  Routes,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom'
import AboutPage from './components/AboutPage'
import SupportPage from './components/Donation'
import SaurathMelaPage from './components/Mela'
import MatchProposalScreen from './components/MatchProposalScreen'
import PanjikarPage from './components/PanjikarPage'
import ReportConcernForm from './components/ReportConcernForm'
import RegistrationFlow from './components/RegistrationFlow'
import StatusPage from './components/StatusPage'
import { submitConcernReport } from './api/registration'
import { Footer, Navbar } from './components/chrome'

function PublicLayout() {
  return (
    <>
      <Navbar />
      <Outlet />
      <Footer />
    </>
  )
}

function LandingPage() {
  return (
    <>
      <section className="page-section">
        <div className="container text-center">
          <p className="text-caption text-text/60 tracking-wider mb-4">Saurath Sabha Gachhi Panji Tradition</p>
          <h1 className="text-heading sm:text-display text-primary leading-tight mb-5">
            Continuing a Tradition of<br className="hidden sm:inline" /> Dignified Matchmaking
          </h1>
          <p className="text-body max-w-[540px] mx-auto mb-10 leading-relaxed">
            A private, non-profit platform preserving the panji tradition —
            dowry-free, genealogy-verified matchmaking by invitation only.
          </p>
          <Link to="/register" className="btn-primary">Request an Invitation</Link>
        </div>
      </section>

      <section id="about" className="page-section border-t border-t-border">
        <div className="container">
          <h2 className="text-heading mb-4">Our Mission</h2>
          <p className="text-body max-w-[600px] leading-relaxed">
            For centuries, the Saurath Sabha Gachhi tradition has brought families
            together through genealogy-verified introductions — rooted in dignity,
            free from dowry. Sabha Gachhi continues this work in a private,
            non-profit setting.
          </p>
          <p className="text-body max-w-[600px] leading-relaxed mt-4">
            We are not a dating service. We are a community platform that
            respects the depth of family heritage in finding a life partner.
          </p>
        </div>
      </section>

      <section id="how-it-works" className="page-section border-t border-t-border">
        <div className="container">
          <h2 className="text-heading mb-8">How It Works</h2>
          <ol className="flex flex-col gap-7">
            {[
              { title: 'Receive an Invitation', body: 'Access is extended through existing members of the Sabha community. There is no public sign-up.' },
              { title: 'Submit Family Genealogy', body: "Your family's panji record is submitted and verified through our established network of genealogists." },
              { title: 'Begin Introductions', body: 'Once verified, we facilitate introductions between compatible families through the Sabha network.' },
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

      <section className="page-section border-t border-t-border">
        <div className="container">
          <div className="quote-block">
            <h2 className="text-heading mb-3">Your Privacy Is Absolute</h2>
            <ul className="flex flex-col gap-2">
              {[
                'Invite-only — no public profiles or searchable database',
                'No personal data is sold or shared with third parties',
                'Non-profit — no advertising, no monetization of your information',
                'Genealogy records are handled with the same discretion as the traditional Sabha',
              ].map((item) => (
                <li key={item} className="text-body relative pl-5 leading-relaxed">
                  <span className="absolute left-0 top-[0.55em] w-[5px] h-[5px] rounded-full bg-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </>
  )
}

/**
 * Entry point for the bare "/status" route — no login system exists yet,
 * so this stands in for one: the family types in the private reference
 * they were given and we route them to their actual status page.
 */
function StatusLookup() {
  const navigate = useNavigate()
  const [reference, setReference] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = reference.trim()
    if (trimmed) {
      navigate(`/status/${trimmed}`)
    }
  }

  return (
    <section className="page-section">
      <div className="container max-w-[480px] text-center">
        <h1 className="text-heading text-primary mb-4">Check your registration status</h1>
        <p className="text-body mb-8 leading-relaxed">
          Enter the private reference that was shared with your family when you registered.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 items-center">
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="e.g. SG-482913"
            className="input w-full max-w-[320px]"
          />
          <button type="submit" className="btn-primary">View status</button>
        </form>
      </div>
    </section>
  )
}

function StatusRoute() {
  const navigate = useNavigate()
  const { reference } = useParams<{ reference: string }>()

  return (
    <StatusPage
      reference={reference ?? ''}
      onOpenMatchProposal={(matchId) => navigate(`/status/match/${matchId}`)}
      onReportConcern={() => navigate(`/concern?ref=${reference}`)}
    />
  )
}

function ProposalRoute() {
  const navigate = useNavigate()
  const { matchId } = useParams<{ matchId: string }>()
  return (
    <MatchProposalScreen
      matchId={matchId ?? ''}
      onBackToStatus={() => navigate(-1)}
    />
  )
}

function ConcernRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const reference = searchParams.get('ref') ?? ''

  return (
    <ReportConcernForm
      registrationId={reference}
      onSubmit={async (submission) => {
        await submitConcernReport({
          registration_reference_text: submission.registrationId,
          topic: submission.topic,
          description: submission.description,
          contact_back: submission.contactBack,
        })
      }}
      onBackToStatus={() => navigate(-1)}
    />
  )
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
  )
}