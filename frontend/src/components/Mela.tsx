const melaDetails = [
  {
    label: "What",
    value:
      "Saurath Mela is a traditional gathering where Maithil families come together around the panji system and the customs of marriage.",
  },
  {
    label: "Where",
    value: "Saurath Sabha Gachhi, Madhubani, Bihar",
  },
  {
    label: "When",
    value:
      "Traditionally held annually during the Hindu month of Ashadh. Dates vary each year according to the calendar.",
  },
];

const thingsToKnow = [
  "Families traditionally attend together and consult panjikars regarding lineage and marriage eligibility.",
  "The gathering is rooted in the panji tradition, where genealogical records have been maintained and consulted across generations.",
  "There is no requirement to register online in order to attend the mela in person.",
  "Families are encouraged to take their time, ask questions, and follow their own family customs.",
];

export default function SaurathMelaPage() {
  return (
    <main>
      <section className="container py-16">
        <p className="text-caption text-text/60 tracking-wider mb-4">An annual tradition</p>
        <h1 className="text-heading sm:text-display text-primary leading-tight mb-6">
          The Saurath Mela
        </h1>
        <p className="text-body max-w-[620px] leading-relaxed">
          For generations, families have gathered at Saurath Sabha Gachhi
          to meet, consult the panjikars, and continue a tradition rooted
          in Maithil genealogy and community.
        </p>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <p className="text-caption text-text/60 tracking-wider mb-4">About the gathering</p>
          <h2 className="text-heading text-primary leading-tight mb-6">
            A place where families have gathered for generations
          </h2>
          <div className="max-w-[620px] text-body leading-relaxed">
            <p>
              Saurath, near Madhubani in Bihar, is traditionally associated
              with the annual Sabha Gachhi gathering of Maithil families.
              The mela has long been connected with the panjikars and the
              careful keeping and consultation of genealogical records.
            </p>
            <p className="mt-5">
              Families who continue to observe this tradition may visit in
              person, meet with panjikars, and discuss family lineage and
              marriage customs in the manner followed by their families.
            </p>
            <p className="mt-5">
              The gathering is not a marketplace for matches. It is a
              community tradition, and for many families it remains a quiet
              opportunity to reconnect with a practice carried across
              generations.
            </p>
          </div>
          <div className="quote-block mt-10 max-w-[620px]">
            <p className="text-heading text-primary mb-3">
              “The panji is not simply a record of names. It carries the
              memory of families across generations.”
            </p>
            <p className="text-body leading-relaxed">
              The mela and panji tradition have historically placed importance
              on knowing one's lineage before marriage.
            </p>
          </div>
        </div>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <p className="text-caption text-text/60 tracking-wider mb-4">Planning a visit</p>
          <h2 className="text-heading text-primary mb-8">The essentials</h2>
          <dl className="flex flex-col gap-7 max-w-[620px]">
            {melaDetails.map((detail) => (
              <div key={detail.label}>
                <dt className="text-caption text-text/60 tracking-wider mb-2">{detail.label}</dt>
                <dd className="text-body leading-relaxed">{detail.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <p className="text-caption text-text/60 tracking-wider mb-4">For families attending</p>
          <h2 className="text-heading text-primary mb-4">What to expect</h2>
          <p className="text-body max-w-[620px] leading-relaxed mb-8">
            The mela can be busy, but families need not approach it as a
            hurried process. Take the time to speak with the appropriate
            panjikar and understand the information being discussed.
          </p>
          <ol className="flex flex-col gap-7">
            {thingsToKnow.map((item, i) => (
              <li key={item} className="flex gap-5 items-start">
                <span className="step-number">{i + 1}</span>
                <p className="text-body leading-relaxed">{item}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-t border-border py-16">
        <div className="container">
          <p className="text-caption text-text/60 tracking-wider mb-4">A living tradition</p>
          <h2 className="text-heading text-primary leading-tight mb-4">
            Come with patience, curiosity, and respect
          </h2>
          <p className="text-body max-w-[620px] leading-relaxed">
            Every family approaches marriage and genealogy differently. The
            mela is a place to listen, consult, and preserve a tradition in a
            way that remains meaningful to families today.
          </p>
        </div>
      </section>
    </main>
  );
}
