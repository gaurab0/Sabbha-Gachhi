const corePrinciples = [
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
];

export function Standards() {
  return (
    <section id="about" className="border-t border-border">
      <div className="container grid max-w-255 items-start gap-12 py-16 md:grid-cols-[0.8fr_1.4fr] md:gap-16 md:py-24 lg:gap-20">
        <div>
          <p className="m-0 mb-5 flex items-center gap-3 text-[0.78rem] font-medium uppercase tracking-[0.14em] text-text/60">
            <span aria-hidden="true" className="inline-block h-px w-8 bg-secondary" />§ 03 — Core
            Standards
          </p>
          <h2 className="m-0 font-medium tracking-[-0.01em] text-primary text-[clamp(1.8rem,3vw,2.4rem)] leading-[1.2]">
            Our Unbending
            <br />
            Principles
          </h2>
        </div>
        <div className="flex flex-col">
          {corePrinciples.map((item, i, arr) => (
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
  );
}
