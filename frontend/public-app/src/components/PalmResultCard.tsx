import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

import { formatAge, formatDate } from "@/lib/format";

export type PalmSearchResult = {
  palm_id: string;
  palm_code: string;
  donor_name: string;
  section_name: string;
  plantation_date: string | null;
  current_age: { years: number; months: number } | null;
  thumbnail_url: string | null;
};

type PalmResultCardProps = {
  item: PalmSearchResult;
  index?: number;
};

export function PalmResultCard({ item, index = 0 }: PalmResultCardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.article
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: reduceMotion ? 0 : index * 0.04 }}
      className="group overflow-hidden rounded-2xl bg-white/90 shadow-sm ring-1 ring-sand-200/80 transition hover:-translate-y-0.5 hover:shadow-md hover:ring-palm-500/30 motion-reduce:transform-none"
    >
      <Link
        to={`/palms/${encodeURIComponent(item.palm_code)}`}
        className="flex flex-col focus-visible:outline-none sm:flex-row"
        aria-label={`View palm ${item.palm_code} sponsored by ${item.donor_name}`}
      >
        <div className="relative aspect-[4/3] w-full shrink-0 overflow-hidden bg-palm-100 sm:aspect-auto sm:h-auto sm:w-40">
          {item.thumbnail_url ? (
            <img
              src={item.thumbnail_url}
              alt=""
              loading="lazy"
              decoding="async"
              className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03] motion-reduce:transition-none motion-reduce:group-hover:scale-100"
            />
          ) : (
            <div
              aria-hidden
              className="grid h-full min-h-28 place-items-center bg-gradient-to-br from-palm-100 to-sand-200 text-palm-700"
            >
              <svg viewBox="0 0 32 32" className="h-10 w-10 opacity-70" fill="currentColor">
                <path d="M16 3c.4 3.8-1.2 7.4-3.8 10.2 2.6-.4 5.1-1.7 7-3.7-.2 3.4-1.8 6.6-4.4 8.9 3.1-.6 5.9-2.4 7.8-5-.1 5.2-3.4 9.8-8.1 12.1C17 28.7 19.8 30 23 30c-4.2.2-8.3-1.4-11.2-4.3C9 28.6 5.6 30 2 30c3.5-1.4 6.2-4.2 7.5-7.7C6.3 19.8 4 15.8 4 11.2 7.6 14 12 15.2 16 14.5 14.2 11.2 13.8 7 16 3Z" />
              </svg>
            </div>
          )}
        </div>
        <div className="flex flex-1 flex-col justify-center gap-2 p-4 sm:p-5">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="font-display text-xl font-semibold text-palm-800">
              {item.palm_code}
            </h2>
            <span className="text-sm text-sand-800/70">{formatAge(item.current_age)}</span>
          </div>
          <p className="text-sm text-sand-900">
            <span className="font-medium text-palm-700">Donor</span>{" "}
            {item.donor_name}
          </p>
          <p className="text-sm text-sand-800/80">
            {item.section_name}
            {item.plantation_date
              ? ` · Planted ${formatDate(item.plantation_date)}`
              : null}
          </p>
        </div>
      </Link>
    </motion.article>
  );
}
