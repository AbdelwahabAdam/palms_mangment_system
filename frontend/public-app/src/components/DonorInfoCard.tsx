type DonorInfoCardProps = {
  donorName: string;
};

export function DonorInfoCard({ donorName }: DonorInfoCardProps) {
  return (
    <section
      aria-labelledby="donor-heading"
      className="rounded-2xl bg-gradient-to-br from-palm-700 to-palm-800 p-5 text-sand-50 shadow-sm sm:p-6"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-400">
        Sponsor
      </p>
      <h2 id="donor-heading" className="mt-2 font-display text-2xl font-semibold">
        {donorName}
      </h2>
      <p className="mt-3 text-sm text-sand-100/85">
        This palm is cared for through the generosity of this Lifemaker Foundation
        donor.
      </p>
    </section>
  );
}
