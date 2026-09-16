const methodStages = [
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
];

export function HowItWorks() {
  return (
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
          {methodStages.map((step) => (
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
  );
}
