import { useState } from "react";
import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { ListIcon, XIcon } from "@phosphor-icons/react";
import { useAuth } from "../context/useAuth";

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);
  const { isAuthenticated, logout } = useAuth();

  return (
    <header className="bg-bg border-b border-b-border shadow-xs sticky top-0 z-40 backdrop-blur-xs bg-bg/95">
      <div className="container container--wide flex items-center justify-between gap-4 py-3">
        <Link
          to="/"
          className="font-serif whitespace-nowrap text-[1.25rem] font-medium tracking-[-0.01em] text-primary no-underline hover:text-primary-hover shrink-0">
          <em>Sabha Gachhi</em>
        </Link>
        <nav
          aria-label="Primary navigation"
          className="hidden md:flex items-center gap-5 lg:gap-7 font-sans">
          <NavLink to="/about" className="nav-link">
            About
          </NavLink>
          <NavLink to="/mela" className="nav-link">
            Mela
          </NavLink>
          <NavLink to="/support" className="nav-link">
            Support
          </NavLink>
          <NavLink to="/status-check" className="nav-link">
            Check Status
          </NavLink>
          <div className="flex items-center gap-2.5 ml-1 shrink-0">
            {isAuthenticated ? (
              <button
                type="button"
                className="btn-outline min-h-[2.25rem] whitespace-nowrap px-4 py-1.5 text-xs tracking-wide"
                onClick={logout}>
                Sign Out
              </button>
            ) : (
              <>
                <Link
                  to="/login"
                  className="btn-outline min-h-[2.25rem] whitespace-nowrap px-4 py-1.5 text-xs tracking-wide">
                  Log In
                </Link>
                <Link
                  to="/register"
                  className="btn-primary min-h-[2.25rem] whitespace-nowrap px-4 py-1.5 text-xs tracking-wide">
                  Request Invite
                </Link>
              </>
            )}
          </div>
        </nav>
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className="inline-flex cursor-pointer items-center justify-center rounded-md border border-border p-2 text-text md:hidden">
          {menuOpen ? <XIcon size={20} /> : <ListIcon size={20} />}
        </button>
      </div>
      {menuOpen && (
        <nav
          id="mobile-menu"
          aria-label="Mobile navigation"
          className="border-t border-border shadow-xs font-sans md:hidden bg-bg">
          <div className="container container--wide flex flex-col gap-1 py-3">
            <NavLink to="/about" onClick={closeMenu} className="nav-link py-2 text-base">
              About
            </NavLink>
            <NavLink to="/mela" onClick={closeMenu} className="nav-link py-2 text-base">
              Mela
            </NavLink>
            <NavLink to="/support" onClick={closeMenu} className="nav-link py-2 text-base">
              Support
            </NavLink>
            <NavLink to="/status-check" onClick={closeMenu} className="nav-link py-2 text-base">
              Check Status
            </NavLink>
            <div className="mt-3 flex flex-col gap-2 border-t border-border/60 pt-3 pb-1">
              {isAuthenticated ? (
                <button
                  type="button"
                  className="btn-outline min-h-[2.5rem] w-full px-4 py-2 text-sm justify-center"
                  onClick={() => {
                    logout();
                    closeMenu();
                  }}>
                  Sign Out
                </button>
              ) : (
                <>
                  <Link
                    to="/login"
                    onClick={closeMenu}
                    className="btn-outline min-h-[2.5rem] w-full px-4 py-2 text-sm justify-center">
                    Log In
                  </Link>
                  <Link
                    to="/register"
                    onClick={closeMenu}
                    className="btn-primary min-h-[2.5rem] w-full px-4 py-2 text-sm justify-center">
                    Request Invite
                  </Link>
                </>
              )}
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}

export function Footer() {
  const { isStaff } = useAuth();
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
          <Link to="/status-check" className="nav-link">
            Check Status
          </Link>
          {isStaff && (
            <Link key="panjikar" to="/panjikar" className="nav-link">
              Panjikar sign-in
            </Link>
          )}
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
