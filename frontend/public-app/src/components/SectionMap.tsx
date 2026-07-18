type SectionMapProps = {
  name: string;
  locationName: string | null;
  imageUrl: string | null;
};

export function SectionMap({ name, locationName, imageUrl }: SectionMapProps) {
  return (
    <section
      aria-labelledby="section-heading"
      className="overflow-hidden rounded-2xl bg-white/90 shadow-sm ring-1 ring-sand-200/80"
    >
      <div className="relative aspect-[16/9] bg-sand-200">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={`Section ${name}`}
            loading="lazy"
            decoding="async"
            className="h-full w-full object-cover"
          />
        ) : (
          <div
            aria-hidden
            className="absolute inset-0 bg-[radial-gradient(circle_at_30%_40%,#d5eadc,transparent_55%),linear-gradient(135deg,#e2d0b0,#3d7a5c55)]"
          />
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-palm-900/80 to-transparent p-5 pt-16 text-sand-50">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-400">
            Section
          </p>
          <h2 id="section-heading" className="font-display text-2xl font-semibold">
            {name}
          </h2>
          {locationName ? (
            <p className="mt-1 text-sm text-sand-100/85">{locationName}</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
