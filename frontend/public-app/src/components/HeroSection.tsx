import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

type HeroSectionProps = {
  title?: ReactNode;
  subtitle?: ReactNode;
  children?: ReactNode;
  compact?: boolean;
};

export function HeroSection({
  title = (
    <>
      Trace every palm back to the people who made it grow.
    </>
  ),
  subtitle = (
    <>
      Search Lifemaker Foundation palms by donor name or palm code. See harvest,
      health, and the story behind each tree.
    </>
  ),
  children,
  compact = false,
}: HeroSectionProps) {
  const reduceMotion = useReducedMotion();

  return (
    <section
      className={
        compact
          ? "relative overflow-hidden border-b border-sand-200/60"
          : "relative min-h-[min(92dvh,860px)] overflow-hidden"
      }
      aria-labelledby="hero-heading"
    >
      <div
        aria-hidden
        className="absolute inset-0 bg-[linear-gradient(160deg,#1b372a_0%,#2f5f48_38%,#6b8f5a_68%,#c49a2e_100%)]"
      />
      <div
        aria-hidden
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23f8f4ec' fill-opacity='0.12'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
        }}
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-sand-50 to-transparent"
      />

      <div
        className={
          compact
            ? "relative mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16"
            : "relative mx-auto flex min-h-[min(92dvh,860px)] max-w-6xl flex-col justify-end px-4 pb-16 pt-24 sm:px-6 sm:pb-24"
        }
      >
        <motion.p
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-3 font-display text-3xl font-semibold tracking-tight text-gold-400 sm:text-4xl md:text-5xl"
        >
          Lifemaker Foundation
        </motion.p>
        <motion.h1
          id="hero-heading"
          initial={reduceMotion ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: reduceMotion ? 0 : 0.08 }}
          className="max-w-3xl font-display text-2xl font-medium leading-tight text-sand-50 sm:text-3xl md:text-4xl"
        >
          {title}
        </motion.h1>
        <motion.p
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: reduceMotion ? 0 : 0.16 }}
          className="mt-4 max-w-xl text-base text-sand-100/90 sm:text-lg"
        >
          {subtitle}
        </motion.p>
        {children ? (
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: reduceMotion ? 0 : 0.24 }}
            className="mt-8 max-w-2xl"
          >
            {children}
          </motion.div>
        ) : null}
      </div>
    </section>
  );
}
