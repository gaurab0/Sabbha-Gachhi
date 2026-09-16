import { useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * Entry point for the bare "/status" route — no login system exists yet,
 * so this stands in for one: the family types in the private reference
 * they were given and we route them to their actual status page.
 */
export function StatusLookup() {
  const navigate = useNavigate();
  const [reference, setReference] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = reference.trim();
    if (trimmed) {
      navigate(`/status/${trimmed}`);
    }
  };

  return (
    <section className="page-section">
      <div className="container max-w-120 text-center">
        <h1 className="text-heading text-primary mb-4">
          Check your registration status
        </h1>
        <p className="text-body mb-8 leading-relaxed">
          Enter the private reference that was shared with your family when you
          registered.
        </p>
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 items-center">
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="e.g. SG-482913"
            className="input w-full max-w-[320px]"
          />
          <button type="submit" className="btn-primary">
            View status
          </button>
        </form>
      </div>
    </section>
  );
}
