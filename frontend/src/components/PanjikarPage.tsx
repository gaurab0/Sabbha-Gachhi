import { Link, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import { REGISTRATIONS, UNDER_REVIEW } from '../lib/data'

function DashboardHome() {
  return (
    <section>
      <p className="text-caption text-text/60 tracking-wider mb-2">Panjikar workspace</p>
      <h1 className="text-heading text-primary mb-4">Sabha workbench</h1>
      <p className="text-body max-w-[600px] leading-relaxed">
        Review registrations, lineage records, and introductions using local
        demonstration data. No records are sent anywhere from this frontend.
      </p>
      <div className="grid gap-4 sm:grid-cols-3 mt-8">
        <Link to="registrations" className="card card-link">
          <strong className="text-primary">{REGISTRATIONS.length}</strong>
          <span className="block text-caption mt-2">Registrations</span>
        </Link>
        <Link to="lineage" className="card card-link">
          <strong className="text-primary">1</strong>
          <span className="block text-caption mt-2">Open lineage review</span>
        </Link>
        <Link to="shortlist" className="card card-link">
          <strong className="text-primary">2</strong>
          <span className="block text-caption mt-2">Shortlist candidates</span>
        </Link>
      </div>
    </section>
  )
}

function Registrations() {
  return (
    <section>
      <h1 className="text-heading text-primary mb-6">Registrations</h1>
      <div className="flex flex-col gap-3 max-w-[880px]">
        {REGISTRATIONS.map((registration) => (
          <Link
            key={registration.id}
            to={`/panjikar/registrations/${registration.id}`}
            className="card card-link"
          >
            <div className="flex flex-wrap justify-between gap-2">
              <strong className="text-primary">{registration.candidate}</strong>
              <span className="badge">{registration.status}</span>
            </div>
            <p className="text-caption mt-2">{registration.id} · {registration.village}</p>
          </Link>
        ))}
      </div>
    </section>
  )
}

function RegistrationDetail() {
  const registration = REGISTRATIONS[0]
  return (
    <section>
      <Link to="/panjikar/registrations" className="text-link text-caption">Back to registrations</Link>
      <div className="flex items-center gap-3 flex-wrap mt-4 mb-6">
        <h1 className="text-heading text-primary">{registration.candidate}</h1>
        <span className="badge">{registration.status}</span>
      </div>
      <div className="card max-w-[600px]">
        <dl>
          <div className="kv-row">
            <dt>Reference</dt>
            <dd>{registration.id}</dd>
          </div>
          <div className="kv-row">
            <dt>Guardian</dt>
            <dd>{registration.guardian}</dd>
          </div>
          <div className="kv-row">
            <dt>Village</dt>
            <dd>{registration.village}</dd>
          </div>
          <div className="kv-row">
            <dt>Side</dt>
            <dd>{registration.side}</dd>
          </div>
          <div className="kv-row">
            <dt>Age</dt>
            <dd>{registration.age}</dd>
          </div>
          <div className="kv-row">
            <dt>Gotra</dt>
            <dd>{registration.gotra}</dd>
          </div>
          <div className="kv-row">
            <dt>Education</dt>
            <dd>{registration.education}</dd>
          </div>
          {registration.note && (
            <div className="kv-row">
              <dt>Note</dt>
              <dd className="font-normal opacity-70">{registration.note}</dd>
            </div>
          )}
        </dl>
      </div>
    </section>
  )
}

function LineageReview() {
  return (
    <section>
      <h1 className="text-heading text-primary mb-6">Lineage review</h1>
      <div className="card max-w-[680px]">
        <p className="text-caption text-text/60">Open review</p>
        <h2 className="text-body font-semibold mt-2">{UNDER_REVIEW.registrant.candidate}</h2>
        <div className="grid gap-8 md:grid-cols-2 mt-6">
          <div>
            <h3 className="text-caption font-semibold border-b border-border pb-2 mb-2">Candidate family</h3>
            <dl>
              {UNDER_REVIEW.brideSide.map((entry) => (
                <div key={entry.relation} className="kv-row">
                  <dt>{entry.relation}</dt>
                  <dd>{entry.name}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div>
            <h3 className="text-caption font-semibold border-b border-border pb-2 mb-2">Existing household</h3>
            <dl>
              {UNDER_REVIEW.existingHousehold.map((entry) => (
                <div key={entry.relation} className="kv-row">
                  <dt>{entry.relation}</dt>
                  <dd>{entry.name}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </section>
  )
}

function Shortlist() {
  return (
    <section>
      <h1 className="text-heading text-primary mb-6">Shortlist</h1>
      <p className="text-body max-w-[600px] leading-relaxed">
        Candidates below are mock records selected for a future introduction review.
      </p>
      <ul className="mt-6 flex flex-col gap-3 max-w-[880px]">
        {REGISTRATIONS.filter((registration) => registration.status === 'verified').map((registration) => (
          <li key={registration.id} className="card">
            <strong className="text-primary">{registration.candidate}</strong>
            <span className="block text-caption mt-2">{registration.education} · {registration.gotra}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function PanjikarPage() {
  return (
    <main className="container container--wide py-12">
      <nav className="flex flex-wrap gap-5 border-b border-border pb-4 mb-10">
        <NavLink to="/panjikar" end className="nav-link">Dashboard</NavLink>
        <NavLink to="/panjikar/registrations" className="nav-link">Registrations</NavLink>
        <NavLink to="/panjikar/lineage" className="nav-link">Lineage</NavLink>
        <NavLink to="/panjikar/shortlist" className="nav-link">Shortlist</NavLink>
      </nav>
      <Routes>
        <Route index element={<DashboardHome />} />
        <Route path="registrations" element={<Registrations />} />
        <Route path="registrations/:id" element={<RegistrationDetail />} />
        <Route path="lineage" element={<LineageReview />} />
        <Route path="shortlist" element={<Shortlist />} />
      </Routes>
      <Outlet />
    </main>
  )
}
