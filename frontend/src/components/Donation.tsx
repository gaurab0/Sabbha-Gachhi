const supportPoints = [
  {
    title: "Support the panjikars",
    description:
      "Your support helps sustain the careful work of maintaining, reviewing, and preserving family lineage records.",
  },
  {
    title: "Keep registration free",
    description:
      "Families should be able to seek guidance without turning registration into a commercial service.",
  },
  {
    title: "Preserve the tradition",
    description:
      "Support helps carry the knowledge and practices surrounding the panji tradition into the future.",
  },
];

const contributionOptions = ["₹500", "₹1,000", "₹2,500", "₹5,000"];

export default function SupportPage() {
  return (
    <main>
      <section className="container py-16">
        <p className="text-caption text-text/60 tracking-wider mb-4">Support Sabha Gachhi</p>
        <h1 className="text-heading sm:text-display text-primary leading-tight mb-6">
          Help keep this work free for families.
        </h1>
        <p className="text-body max-w-[620px] leading-relaxed">
          Sabha Gachhi exists to support families seeking guidance through
          the panji tradition. Contributions help sustain the people and
          work behind that service, without turning it into a commercial
          platform.
        </p>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <p className="text-caption text-text/60 tracking-wider mb-4">Why support matters</p>
          <h2 className="text-heading text-primary leading-tight mb-6">
            Quiet work keeps a tradition alive
          </h2>
          <div className="max-w-[620px] text-body leading-relaxed">
            <p>
              Behind every registration and lineage review is careful human
              work. Panjikars preserve family records, review genealogical
              information, and help families understand what has been
              recorded across generations.
            </p>
            <p className="mt-5">
              Donations help cover the ordinary costs of this work and allow
              families to use Sabha Gachhi without registration fees or
              commercial matchmaking charges.
            </p>
            <p className="mt-5">
              There is no campaign target here. If you wish to contribute,
              you may give what is comfortable for your family.
            </p>
          </div>
          <div className="quote-block mt-10 max-w-[620px]">
            <p className="text-heading text-primary mb-3">
              “A tradition survives when its knowledge is cared for and passed
              on.”
            </p>
            <p className="text-body leading-relaxed">
              Your support helps make that care possible.
            </p>
          </div>
        </div>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <p className="text-caption text-text/60 tracking-wider mb-4">Where it goes</p>
          <h2 className="text-heading text-primary mb-8">
            Supporting the people behind the work
          </h2>
          <ol className="flex flex-col gap-7">
            {supportPoints.map((point, i) => (
              <li key={point.title} className="flex gap-5 items-start">
                <span className="step-number">{i + 1}</span>
                <div>
                  <h3 className="text-body font-semibold mb-1">{point.title}</h3>
                  <p className="text-body leading-relaxed">{point.description}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <div className="card max-w-[620px]">
            <p className="text-caption text-text/60 tracking-wider mb-4">Make a contribution</p>
            <h2 className="text-heading text-primary mb-4">Give what feels appropriate</h2>
            <p className="text-body leading-relaxed mb-8">
              This is a simple demonstration of the donation interface.
              Payment processing is intentionally not connected in this
              frontend-only implementation.
            </p>
            <p className="label">Suggested contribution</p>
            <div className="flex flex-wrap gap-3 mb-6">
              {contributionOptions.map((amount) => (
                <button key={amount} type="button" className="btn-outline">
                  {amount}
                </button>
              ))}
            </div>
            <div className="field">
              <label htmlFor="customAmount" className="label">
                Or enter another amount
              </label>
              <input
                id="customAmount"
                type="number"
                placeholder="Amount"
                className="input"
              />
            </div>
            <button type="button" className="btn-primary">
              Continue with contribution
            </button>
            <p className="field-hint mt-4">
              No payment is processed in this frontend demonstration.
            </p>
          </div>
        </div>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <h2 className="text-heading text-primary leading-tight max-w-[620px]">
            Thank you for helping this remain a service to families, rather
            than a business built around them.
          </h2>
        </div>
      </section>
    </main>
  );
}
