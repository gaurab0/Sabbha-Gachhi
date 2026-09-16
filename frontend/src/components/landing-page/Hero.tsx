import { Link } from "react-router-dom";

const heroProof = [
  {
    term: "Origin & History",
    detail:
      "Centuries of community assembly in the shade of Saurath\u2019s orchards",
  },
  {
    term: "Uncompromising Ethic",
    detail: "Strictly dowry-free introductions anchored in mutual respect",
  },
  {
    term: "Record Verification",
    detail:
      "Multi-generational genealogy authenticated by authorized Panjikars",
  },
];

export function Hero() {
  return (
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
            tradition — dowry-free, genealogy-verified matchmaking by invitation
            only.
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
            {heroProof.map((item) => (
              <div key={item.term} className="hero-proof-item">
                <dt>{item.term}</dt>
                <dd>{item.detail}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}
