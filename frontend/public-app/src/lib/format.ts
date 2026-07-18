import type { PublicPalmProfile } from "@palms/shared";

type PublicAge = NonNullable<PublicPalmProfile["current_age"]>;

export function formatAge(age: PublicAge | null | undefined): string {
  if (!age) {
    return "Age unknown";
  }
  if (age.years === 0 && age.months === 0) {
    return "Newly planted";
  }
  const years = age.years > 0 ? `${age.years} yr${age.years === 1 ? "" : "s"}` : "";
  const months =
    age.months > 0 ? `${age.months} mo${age.months === 1 ? "" : "s"}` : "";
  return [years, months].filter(Boolean).join(" ");
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDecimal(
  value: string | number | null | undefined,
  options?: Intl.NumberFormatOptions,
): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return new Intl.NumberFormat("en-EG", {
    maximumFractionDigits: 2,
    ...options,
  }).format(numeric);
}

export function formatCurrency(value: string | number | null | undefined): string {
  return formatDecimal(value, {
    style: "currency",
    currency: "EGP",
    currencyDisplay: "symbol",
  });
}

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
