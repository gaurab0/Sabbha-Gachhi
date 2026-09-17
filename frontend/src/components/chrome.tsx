import { useState } from "react";
import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { ListIcon, XIcon } from "@phosphor-icons/react";

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);

  return (
    <header className="bg-bg border-b border-b-border shadow-xs">
      {/* <p className="m-0 border-b border-border px-(--space-inline) py-[0.55rem] text-center font-sans text-[0.78rem] tracking-[0.01em] text-text/62 max-sm:hidden">
        A private community initiative preserving Mithila&apos;s Panji tradition
        &middot; By referral &amp; genealogy verification only
      </p> */}
      <div className="container container--wide flex items-center justify-between gap-6 py-[0.85rem]">
        <Link
          to="/"
          className="font-serif whitespace-nowrap text-[1.2rem] font-medium tracking-[-0.01em] text-primary no-underline hover:text-primary-hover">
          <em>Sabha Gachhi</em>
        </Link>
        <nav
          aria-label="Primary navigation"
          className="flex flex-wrap items-center gap-[1.4rem] font-sans max-sm:hidden">
          <NavLink to="/about" className="nav-link">
            About
          </NavLink>
          <NavLink to="/mela" className="nav-link">
            Mela
          </NavLink>
          <NavLink to="/support" className="nav-link">
            Support
          </NavLink>
          <Link
            to="/status"
            className="btn-outline min-h-[2.35rem] whitespace-nowrap px-[1.15rem] py-2 text-sm">
            Sign In
          </Link>
          <Link
            to="/register"
            className="btn-primary min-h-[2.35rem] whitespace-nowrap px-[1.15rem] py-2 text-sm">
            Request Invite
          </Link>
        </nav>
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className="inline-flex cursor-pointer items-center justify-center rounded-md border border-border p-2 text-text sm:hidden">
          {menuOpen ? <XIcon size={20} /> : <ListIcon size={20} />}
        </button>
      </div>
      {menuOpen && (
        <nav
          id="mobile-menu"
          aria-label="Mobile navigation"
          className="border-t border-border shadow-xs font-sans sm:hidden">
          <div className="container container--wide flex flex-col gap-1 py-3">
            <NavLink
              to="/about"
              onClick={closeMenu}
              className="nav-link py-2 text-base">
              About
            </NavLink>
            <NavLink
              to="/mela"
              onClick={closeMenu}
              className="nav-link py-2 text-base">
              Mela
            </NavLink>
            <NavLink
              to="/support"
              onClick={closeMenu}
              className="nav-link py-2 text-base">
              Support
            </NavLink>
            <div className="mt-2 flex flex-col gap-2 pb-1">
              <Link
                to="/status"
                onClick={closeMenu}
                className="btn-outline min-h-[2.35rem] w-full px-[1.15rem] py-2 text-sm">
                Sign In
              </Link>
              <Link
                to="/register"
                onClick={closeMenu}
                className="btn-primary min-h-[2.35rem] w-full px-[1.15rem] py-2 text-sm">
                Request Invite
              </Link>
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-t-border py-8">
      <div className="container flex max-w-255 flex-wrap items-center justify-center gap-x-8 gap-y-3 text-center max-md:flex-col max-md:gap-4 md:justify-between md:text-left">
        <p className="m-0 font-sans text-[0.83rem] text-text/50">
          Sabha Gachhi &middot; Saurath Panji Tradition &middot; Non-Profit
          Community Trust
        </p>
        <nav
          aria-label="Footer navigation"
          className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 font-sans">
          <Link to="/about" className="nav-link">
            About
          </Link>
          <Link to="/mela" className="nav-link">
            Saurath Mela
          </Link>
          <Link to="/support" className="nav-link">
            Support
          </Link>
          <Link to="/panjikar" className="nav-link">
            Panjikar sign-in
          </Link>
        </nav>
      </div>
    </footer>
  );
}

export function Page({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <main className="container py-12">
      <h1 className="text-heading mb-6">{title}</h1>
      {children}
    </main>
  );
}
