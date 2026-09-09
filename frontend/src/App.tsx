function App() {
  return (
    <>
      <header className="border-b border-b-border py-5">
        <div className="container flex items-center justify-between">
          <a href="#" className="text-body font-semibold text-primary no-underline">
            Sabha Gachhi
          </a>
          <nav className="flex items-center gap-6">
            <a href="#about" className="nav-link">About</a>
            <a href="#how-it-works" className="nav-link">How It Works</a>
            <a href="#login" className="btn-outline">Log In</a>
            <a href="#signup" className="btn-primary">Sign Up</a>
          </nav>
        </div>
      </header>

      <section className="px-5 pt-[5.5rem] pb-16 text-center sm:px-8 sm:pt-24 sm:pb-20">
        <p className="text-caption text-text/60 tracking-wider mb-4">
          Saurath Sabha Gachhi Panji Tradition
        </p>
        <h1 className="text-heading sm:text-display text-primary leading-tight mb-5">
          Continuing a Tradition of<br className="hidden sm:inline" /> Dignified Matchmaking
        </h1>
        <p className="text-body max-w-[540px] mx-auto mb-10 leading-relaxed">
          A private, non-profit platform preserving the panji tradition —
          dowry-free, genealogy-verified matchmaking by invitation only.
        </p>
        <a href="#request" className="btn-primary">Request an Invitation</a>
      </section>

      <section id="about" className="border-t border-t-border py-16">
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

      <section id="how-it-works" className="border-t border-t-border py-16">
        <div className="container">
          <h2 className="text-heading mb-8">How It Works</h2>
          <ol className="flex flex-col gap-7">
            {[
              {
                title: 'Receive an Invitation',
                body: 'Access is extended through existing members of the Sabha community. There is no public sign-up.',
              },
              {
                title: 'Submit Family Genealogy',
                body: "Your family's panji record is submitted and verified through our established network of genealogists.",
              },
              {
                title: 'Begin Introductions',
                body: 'Once verified, we facilitate introductions between compatible families through the Sabha network.',
              },
            ].map((step, i) => (
              <li key={step.title} className="flex gap-5 items-start">
                <span className="shrink-0 grid place-items-center w-8 h-8 rounded-full border border-primary text-caption font-semibold text-primary">
                  {i + 1}
                </span>
                <div>
                  <h3 className="text-body font-semibold mb-1">{step.title}</h3>
                  <p className="text-body leading-relaxed">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-t border-t-border py-16">
        <div className="container">
          <div className="border-l-2 border-l-accent py-6 pl-7 pr-5">
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

      <footer className="border-t border-t-border py-8 mt-4">
        <div className="container text-center text-caption text-text/50 tracking-wider">
          Sabha Gachhi &middot; Non-profit &middot; By invitation only
        </div>
      </footer>
    </>
  )
}

export default App