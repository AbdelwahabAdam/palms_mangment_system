import { formatCurrency, formatDecimal } from "@/lib/format";

type HarvestSummaryCardProps = {
  totalAmount: string;
  totalRevenue: string;
  recordsCount: number;
};

export function HarvestSummaryCard({
  totalAmount,
  totalRevenue,
  recordsCount,
}: HarvestSummaryCardProps) {
  return (
    <section
      aria-labelledby="harvest-heading"
      className="rounded-2xl bg-white/90 p-5 shadow-sm ring-1 ring-sand-200/80 sm:p-6"
    >
      <h2 id="harvest-heading" className="font-display text-xl font-semibold text-palm-800">
        Harvest & revenue
      </h2>
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-sand-800/60">Total harvest</p>
          <p className="mt-1 font-display text-2xl font-semibold text-sand-900">
            {formatDecimal(totalAmount)}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider text-sand-800/60">Total revenue</p>
          <p className="mt-1 font-display text-2xl font-semibold text-gold-600">
            {formatCurrency(totalRevenue)}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider text-sand-800/60">Records</p>
          <p className="mt-1 font-display text-2xl font-semibold text-sand-900">
            {recordsCount}
          </p>
        </div>
      </div>
    </section>
  );
}
