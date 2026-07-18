import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

import { HeroSection } from "@/components/HeroSection";

export function AboutPage() {
  const reduceMotion = useReducedMotion();

  return (
    <>
      <HeroSection
        compact
        title="Growing hope, one palm at a time."
        subtitle="Lifemaker Foundation connects donors with living date palms — transparent, traceable, and rooted in community care."
      />

      <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="prose-none space-y-6 text-base leading-relaxed text-sand-800"
        >
          <p>
            Lifemaker Foundation partners with growers and sponsors to sustain date
            palm orchards. Every palm in this discovery experience carries a unique
            code so donors and the public can follow its health, harvest, and
            lineage.
          </p>
          <p>
            This public site is intentionally simple: search for a donor or palm,
            open the profile, and explore photos, harvest totals, disease history,
            and related trees — without needing an account.
          </p>
        </motion.div>

        <div className="mt-10">
          <Link
            to="/search"
            className="inline-flex rounded-lg bg-palm-700 px-5 py-2.5 text-sm font-semibold text-sand-50 transition hover:bg-palm-600"
          >
            Search palms
          </Link>
        </div>
      </div>
    </>
  );
}
