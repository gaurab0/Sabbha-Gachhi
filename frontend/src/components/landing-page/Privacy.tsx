const discretionPoints = [
  "Zero searchable databases or publicly indexed candidate listings",
  "No commercial advertising, monetization, or third-party data broker sharing",
  "Strict non-profit governance overseen by respected community trustees",
  "Genealogy records guarded with the solemn discretion of traditional Panjikars",
];

export function Privacy() {
  return (
    <section id="privacy" className="border-t border-border">
      <div className="container max-w-255 py-16 md:py-24">
        <p className="m-0 mb-5 flex items-center gap-3 font-sans text-[0.78rem] font-medium uppercase tracking-[0.14em] text-text/60">
          <span aria-hidden="true" className="inline-block h-px w-8 bg-secondary" />§ 04 —
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
          {discretionPoints.map((item) => (
            <li key={item} className="pl-1 leading-[1.65] text-text/85">
              {item}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
