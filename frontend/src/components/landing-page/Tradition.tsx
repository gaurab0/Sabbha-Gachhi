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
    <section id="tradition" className="tradition-section">
      <div className="container tradition-grid max-w-6xl">
        <div>
          <p className="section-eyebrow">
            <span aria-hidden="true" className="hero-eyebrow-rule" />§ 01 — The
            Tradition
          </p>
          <h2 className="tradition-title">
            Before there were profiles,
            <br />
            there were panjis.
          </h2>
          <div className="tradition-body">
            <p>
              Every family keeps its story in the panji — a handwritten registry
              maintained across generations by hereditary genealogists, the
              panjikars. Before any marriage, the record is consulted: which
              line is unbroken, which branch may join which.
            </p>
            <p>
              Saurath Sabha Gachhi was where that consultation became a
              congregation. Families gathering beneath the mango orchard, the
              gachhi, meeting panjikars face to face with the panji open before
              them.
            </p>
          </div>
        </div>
        <dl className="tradition-faq">
          {traditionFaq.map((item) => (
            <div key={item.term} className="tradition-faq-item">
              <dt>{item.term}</dt>
              <dd>{item.detail}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
