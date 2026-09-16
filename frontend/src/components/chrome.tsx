import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

export function Navbar() {
  return (
    <header className="bg-bg border-b border-b-border">
      <p className="announcement-bar">
        A private community initiative preserving Mithila&apos;s Panji tradition
        &middot; By referral &amp; genealogy verification only
      </p>
      <div className="container container--wide site-header">
        <Link to="/" className="site-brand">
          Sabha Gachhi
        </Link>
        <nav aria-label="Primary navigation" className="site-nav">
          <NavLink to="/about" className="nav-link">
            About
          </NavLink>
          <NavLink to="/mela" className="nav-link">
            Mela
          </NavLink>
          <NavLink to="/support" className="nav-link">
            Support
          </NavLink>
          <Link to="/status" className="btn-outline btn-sm whitespace-nowrap">
            Sign In
          </Link>
          <Link to="/register" className="btn-primary btn-sm whitespace-nowrap">
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
