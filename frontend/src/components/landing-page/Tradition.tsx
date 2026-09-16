const traditionFaq = [
  {
    term: "What is the Sabha?",
    detail:
      "The historic gathering of Maithil families in Saurath where matches were arranged with the consent and verified backing of the community.",
  },
  {
    term: "What is the Panji?",
    detail:
      "A family\u2019s authentic genealogical record, kept, updated, and carefully cross-verified by traditional panjikars.",
  },
  {
    term: "What has changed?",
    detail:
      "Nothing essential. The same sacred rules of lineage and honor apply — carried thoughtfully onto a quieter, secure modern platform.",
  },
];

export function Tradition() {
  return (
    <section
      id="tradition"
      className="pt-[clamp(3rem,6vw,5rem)] pb-[clamp(3.5rem,7vw,5.5rem)]">
      <div className="container grid max-w-6xl items-start gap-[clamp(2.5rem,6vw,5rem)] max-md:grid-cols-1 max-md:gap-10 md:grid-cols-[1.3fr_1fr]">
        <div>
          <p className="m-0 mb-[1.15rem] flex items-center gap-3 font-sans text-[0.78rem] font-medium tracking-[0.14em] text-text/62 uppercase">
            <span
              aria-hidden="true"
              className="inline-block h-px w-8 bg-secondary"
            />
            § 01 — The Tradition
          </p>
          <h2 className="m-0 mb-[1.6rem] text-[clamp(1.9rem,3.2vw,2.5rem)] leading-[1.22] font-medium tracking-[-0.01em] text-balance">
            Before there were profiles,
            <br />
            there were panjis.
          </h2>
          <div>
            <p className="m-0 mb-5 text-[1.02rem] leading-[1.7] text-text/88 last:mb-0">
              Every family keeps its story in the panji — a handwritten registry
              maintained across generations by hereditary genealogists, the
              panjikars. Before any marriage, the record is consulted: which
              line is unbroken, which branch may join which.
            </p>
            <p className="m-0 mb-5 text-[1.02rem] leading-[1.7] text-text/88 last:mb-0">
              Saurath Sabha Gachhi was where that consultation became a
              congregation. Families gathering beneath the mango orchard, the
              gachhi, meeting panjikars face to face with the panji open before
              them.
            </p>
          </div>
        </div>
        <dl className="m-0 flex flex-col gap-[2.1rem]">
          {traditionFaq.map((item) => (
            <div
              key={item.term}
              className="border-t border-border pt-[1.15rem]">
              <dt className="font-sans text-[0.75rem] font-semibold tracking-widest text-text/75 uppercase">
                {item.term}
              </dt>
              <dd className="m-0 mt-[0.55rem] text-base leading-[1.65] text-text/88">
                {item.detail}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
