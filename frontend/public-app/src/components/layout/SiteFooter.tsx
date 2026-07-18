import { Link } from "react-router-dom";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-sand-200/80 bg-palm-800 text-sand-50">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <div>
          <p className="font-display text-2xl font-semibold tracking-tight">
            Lifemaker Foundation
          </p>
          <p className="mt-2 max-w-md text-sm text-sand-100/80">
            Sustaining date palms and the communities who care for them — one
            sponsored tree at a time.
          </p>
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          <Link className="underline-offset-4 hover:underline" to="/search">
            Search palms
          </Link>
          <Link className="underline-offset-4 hover:underline" to="/about">
            About
          </Link>
        </div>
      </div>
    </footer>
  );
}
