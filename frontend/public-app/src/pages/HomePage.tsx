import { Link } from "react-router-dom";

import { HeroSection } from "@/components/HeroSection";
import { SearchBar } from "@/components/SearchBar";

export function HomePage() {
  return (
    <>
      <HeroSection>
        <SearchBar autoFocus />
      </HeroSection>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20" aria-labelledby="how-heading">
        <h2 id="how-heading" className="font-display text-3xl font-semibold text-palm-800">
          How discovery works
        </h2>
        <p className="mt-3 max-w-2xl text-sand-800/80">
          Find a sponsored palm, open its living profile, and follow harvest and
          health updates over time.
        </p>
        <ol className="mt-10 grid gap-8 sm:grid-cols-3">
          {[
            {
              step: "01",
              title: "Search",
              body: "Type a donor name or palm code. Suggestions help you zero in quickly.",
            },
            {
              step: "02",
              title: "Explore",
              body: "Open the palm profile for photos, age, harvest totals, and location.",
            },
            {
              step: "03",
              title: "Follow",
              body: "Review disease history and related palms to see the full growing story.",
            },
          ].map((item) => (
            <li key={item.step}>
              <p className="text-sm font-semibold tracking-[0.2em] text-gold-600">
                {item.step}
              </p>
              <h3 className="mt-2 font-display text-xl font-semibold text-palm-800">
                {item.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-sand-800/80">{item.body}</p>
            </li>
          ))}
        </ol>
        <div className="mt-12">
          <Link
            to="/about"
            className="inline-flex rounded-lg bg-palm-700 px-5 py-2.5 text-sm font-semibold text-sand-50 transition hover:bg-palm-600"
          >
            Learn about Lifemaker
          </Link>
        </div>
      </section>
    </>
  );
}
