import { Link } from "react-router-dom";

export function Cta() {
  return (
    <section className="border-t border-border">
      <div className="container max-w-160 text-center py-16 md:py-24">
        <h2 className="m-0 mb-4 font-medium tracking-[-0.01em] text-primary text-[clamp(1.7rem,3vw,2.2rem)] leading-tight">
          Continuing Lineage with Dignity
        </h2>
        <p className="m-0 mb-8 leading-[1.7] text-text/75">
          If your family upholds the dowry-free tradition and holds verified
          panji roots, request an introduction through a verified community
          sponsor.
        </p>
        <Link to="/register" className="btn-primary font-sans">
          Request an Invitation
        </Link>
      </div>
    </section>
  );
}
