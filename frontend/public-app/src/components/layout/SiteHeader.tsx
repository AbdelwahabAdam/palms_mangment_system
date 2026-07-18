import { Link, NavLink } from "react-router-dom";

import { cn } from "@/lib/format";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/search", label: "Search", end: false },
  { to: "/about", label: "About", end: false },
] as const;

export function SiteHeader() {
  return (
    <header className="relative z-20 border-b border-sand-200/70 bg-sand-50/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link
          to="/"
          className="group flex items-center gap-3 rounded-sm focus-visible:outline-none"
          aria-label="Lifemaker Foundation home"
        >
          <span
            aria-hidden
            className="grid h-10 w-10 place-items-center rounded-full bg-palm-700 text-gold-400 shadow-sm ring-1 ring-palm-600/40"
          >
            <svg viewBox="0 0 32 32" className="h-5 w-5" fill="currentColor">
              <path d="M16 3c.4 3.8-1.2 7.4-3.8 10.2 2.6-.4 5.1-1.7 7-3.7-.2 3.4-1.8 6.6-4.4 8.9 3.1-.6 5.9-2.4 7.8-5-.1 5.2-3.4 9.8-8.1 12.1C17 28.7 19.8 30 23 30c-4.2.2-8.3-1.4-11.2-4.3C9 28.6 5.6 30 2 30c3.5-1.4 6.2-4.2 7.5-7.7C6.3 19.8 4 15.8 4 11.2 7.6 14 12 15.2 16 14.5 14.2 11.2 13.8 7 16 3Z" />
            </svg>
          </span>
          <span className="leading-tight">
            <span className="block font-display text-lg font-semibold tracking-tight text-palm-800 group-hover:text-palm-700 sm:text-xl">
              Lifemaker
            </span>
            <span className="block text-[0.7rem] font-medium uppercase tracking-[0.18em] text-gold-600">
              Foundation
            </span>
          </span>
        </Link>

        <nav aria-label="Primary" className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                cn(
                  "rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors sm:px-3",
                  isActive
                    ? "bg-palm-100 text-palm-800"
                    : "text-sand-800/80 hover:bg-sand-100 hover:text-palm-800",
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
