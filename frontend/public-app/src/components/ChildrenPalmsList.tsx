import { Link } from "react-router-dom";

type ChildPalm = {
  id: string;
  code: string;
  relationship_type: string;
};

type ChildrenPalmsListProps = {
  childrenPalms: ChildPalm[];
};

export function ChildrenPalmsList({ childrenPalms }: ChildrenPalmsListProps) {
  return (
    <section
      aria-labelledby="children-heading"
      className="rounded-2xl bg-white/90 p-5 shadow-sm ring-1 ring-sand-200/80 sm:p-6"
    >
      <h2 id="children-heading" className="font-display text-xl font-semibold text-palm-800">
        Related palms
      </h2>
      {childrenPalms.length === 0 ? (
        <p className="mt-4 text-sm text-sand-800/75">No related palms listed.</p>
      ) : (
        <ul className="mt-4 divide-y divide-sand-200/80">
          {childrenPalms.map((child) => (
            <li key={child.id} className="flex items-center justify-between gap-3 py-3">
              <div>
                <Link
                  to={`/palms/${encodeURIComponent(child.code)}`}
                  className="font-medium text-palm-700 underline-offset-2 hover:underline"
                >
                  {child.code}
                </Link>
                <p className="text-xs capitalize text-sand-800/65">
                  {child.relationship_type.replaceAll("_", " ")}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
