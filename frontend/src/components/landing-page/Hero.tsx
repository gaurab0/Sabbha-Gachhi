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
    <section className="pt-[clamp(3.5rem,7vw,5.25rem)] pb-[clamp(3rem,6vw,4.5rem)]">
      <div className="container">
        <div className="mx-auto max-w-175 text-center">
          <p className="m-0 mb-[1.4rem] flex items-center justify-center gap-[0.9rem] font-sans text-[0.78rem] font-medium tracking-[0.14em] text-text/62 uppercase max-sm:gap-2 max-sm:text-[0.68rem] max-sm:tracking-widest max-sm:[&>span]:hidden">
            <span
              aria-hidden="true"
              className="inline-block h-px w-8 bg-secondary"
            />
            Saurath Sabha Gachhi Panji Tradition
            <span
              aria-hidden="true"
              className="inline-block h-px w-8 bg-secondary"
            />
          </p>
          <h1 className="m-0 mb-[1.3rem] text-[clamp(2.4rem,5vw,3.3rem)] leading-[1.16] font-medium tracking-[-0.01em] text-balance max-sm:text-3xl">
            Continuing a Tradition of
            <br />
            <em className="font-medium">Dignified Matchmaking</em>
          </h1>
          <p className="m-0 mx-auto mb-[2.1rem] max-w-150 text-body leading-[1.65] text-text/82">
            A private, non-profit platform preserving the seven-century panji
            tradition — dowry-free, genealogy-verified matchmaking by invitation
            only.
          </p>
          <div className="mb-14 flex flex-wrap items-center justify-center gap-[0.8rem] max-sm:flex-col max-sm:items-stretch">
            <Link to="/register" className="btn-primary font-sans">
              Request an Invitation
            </Link>
            <Link
              to="/about"
              className="inline-flex min-h-11 cursor-pointer items-center justify-center rounded-md border border-border bg-transparent px-6 py-3 font-sans text-body font-medium text-text no-underline transition-[border-color,background-color] duration-160 hover:border-[color-mix(in_srgb,var(--color-text)_40%,var(--color-border))] hover:bg-[color-mix(in_srgb,var(--color-border)_22%,transparent)]">
              Read Our Charter
            </Link>
          </div>
          <dl className="m-0 grid grid-cols-3 gap-8 border-y border-border py-[1.8rem] text-left max-sm:grid-cols-1 max-sm:gap-[1.4rem]">
            {heroProof.map((item, i) => (
              <div
                key={item.term}
                className={
                  i === 0
                    ? ""
                    : "max-sm:border-t max-sm:border-border max-sm:pt-[1.4rem] sm:border-l sm:border-border sm:pl-8"
                }>
                <dt className="font-sans text-[0.72rem] font-medium tracking-[0.12em] text-text/[0.55] uppercase">
                  {item.term}
                </dt>
                <dd className="m-0 mt-[0.45rem] text-[1.02rem] leading-normal">
                  {item.detail}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}
