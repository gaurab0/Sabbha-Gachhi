import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

export function Navbar() {
  return (
    <header className="bg-bg border-b border-b-border">
      <p className="m-0 border-b border-border px-(--space-inline) py-[0.55rem] text-center font-sans text-[0.78rem] tracking-[0.01em] text-text/62">
        A private community initiative preserving Mithila&apos;s Panji tradition
        &middot; By referral &amp; genealogy verification only
      </p>
      <div className="container container--wide flex items-center justify-between gap-6 py-[0.85rem] max-sm:flex-wrap max-sm:gap-3">
        <Link
          to="/"
          className="whitespace-nowrap text-[1.2rem] font-bold tracking-[-0.01em] text-primary no-underline hover:text-primary-hover">
          Sabha Gachhi
        </Link>
        <nav
          aria-label="Primary navigation"
          className="flex flex-wrap items-center gap-[1.4rem] max-sm:gap-[0.9rem]">
          <NavLink to="/about" className="nav-link max-sm:hidden">
            About
          </NavLink>
          <NavLink to="/mela" className="nav-link max-sm:hidden">
            Mela
          </NavLink>
          <NavLink to="/support" className="nav-link max-sm:hidden">
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
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-t-border py-8">
      <div className="container flex max-w-255 flex-wrap items-center justify-center gap-x-8 gap-y-3 text-center md:justify-between md:text-left">
        <p className="m-0 text-[0.83rem] text-text/50">
          Sabha Gachhi &middot; Saurath Panji Tradition &middot; Non-Profit
          Community Trust
        </p>
        <nav
          aria-label="Footer navigation"
          className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
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
