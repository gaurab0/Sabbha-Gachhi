export function Quotes() {
  return (
    <section className="border-t border-border">
      <div className="max-w-255 mx-auto text-center py-20 md:py-28">
        <blockquote className="m-0 flex flex-col items-center gap-4">
          <p className="m-0 italic text-balance text-[clamp(1.5rem,3.4vw,2.1rem)] leading-[1.45] text-text/90">
            &ldquo;We are not a dating service. We are a family record, opened
            carefully, for one purpose.&rdquo;
          </p>
          <footer className="text-[0.78rem] font-medium uppercase tracking-[0.14em] text-text/55">
            — The Sabha Charter
          </footer>
        </blockquote>
      </div>
    </section>
  );
}
