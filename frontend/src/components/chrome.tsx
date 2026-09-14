import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'

export function Navbar() {
  return (
    <header className="border-b border-b-border py-4 sm:py-5">
      <div className="container flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <Link to="/" className="text-body font-semibold tracking-tight text-primary no-underline">
          Sabha Gachhi
        </Link>
        <nav aria-label="Primary navigation" className="flex items-center gap-x-5 gap-y-2 flex-wrap">
          <NavLink to="/about" className="nav-link">About</NavLink>
          <NavLink to="/mela" className="nav-link">Mela</NavLink>
          <NavLink to="/support" className="nav-link">Support</NavLink>
          <Link to="/status" className="btn-outline">
            Log In
          </Link>
          <Link to="/register" className="btn-primary whitespace-nowrap">
            Request an Invitation
          </Link>
        </nav>
      </div>
    </header>
  )
}

export function Footer() {
  return (
    <footer className="border-t border-t-border py-8 mt-4">
      <div className="container text-center text-caption text-text/50 tracking-wider">
        <nav aria-label="Footer navigation" className="flex items-center justify-center gap-x-5 gap-y-2 flex-wrap mb-4">
          <Link to="/about" className="nav-link">About</Link>
          <Link to="/mela" className="nav-link">Saurath Mela</Link>
          <Link to="/support" className="nav-link">Support</Link>
          <Link to="/panjikar" className="nav-link">Panjikar sign-in</Link>
        </nav>
        <div>Sabha Gachhi &middot; Non-profit &middot; By invitation only</div>
      </div>
    </footer>
  )
}

export function Page({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <main className="container py-12">
      <h1 className="text-heading mb-6">{title}</h1>
      {children}
    </main>
  )
}
