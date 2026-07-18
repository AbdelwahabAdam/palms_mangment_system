import type { PublicPalmProfile } from "@palms/shared";
import PhotoSwipeLightbox from "photoswipe/lightbox";
import { useEffect, useId, useRef } from "react";

import "photoswipe/style.css";

type PalmImage = PublicPalmProfile["images"][number];

type PalmImageGalleryProps = {
  images: PalmImage[];
  palmCode: string;
};

export function PalmImageGallery({ images, palmCode }: PalmImageGalleryProps) {
  const galleryId = useId().replace(/:/g, "");
  const galleryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!images.length || !galleryRef.current) {
      return;
    }

    const lightbox = new PhotoSwipeLightbox({
      gallery: `#gallery-${galleryId}`,
      children: "a",
      pswpModule: () => import("photoswipe"),
      padding: { top: 24, bottom: 24, left: 16, right: 16 },
    });
    lightbox.init();

    return () => {
      lightbox.destroy();
    };
  }, [galleryId, images]);

  if (images.length === 0) {
    return (
      <div
        className="grid min-h-56 place-items-center rounded-2xl bg-sand-100 text-sm text-sand-800/70 ring-1 ring-sand-200"
        role="img"
        aria-label={`No photos available for palm ${palmCode}`}
      >
        No photos available for this palm yet.
      </div>
    );
  }

  const [hero, ...rest] = images;

  return (
    <div
      id={`gallery-${galleryId}`}
      ref={galleryRef}
      className="grid gap-3 sm:grid-cols-3"
      aria-label={`Photo gallery for palm ${palmCode}`}
    >
      {hero ? (
        <a
          href={hero.full_url}
          data-pswp-src={hero.full_url}
          data-pswp-width="1600"
          data-pswp-height="1200"
          className="group relative block overflow-hidden rounded-2xl focus-visible:outline-none sm:col-span-2 sm:row-span-2"
          aria-label={`Open photo 1 of ${images.length}`}
        >
          <img
            src={hero.medium_url || hero.webp_url || hero.thumbnail_url}
            alt={`Palm ${palmCode} photo 1`}
            loading="eager"
            decoding="async"
            className="aspect-[4/3] h-full w-full object-cover transition duration-500 group-hover:scale-[1.02] motion-reduce:transition-none sm:aspect-auto sm:min-h-72"
          />
        </a>
      ) : null}
      {rest.map((image, index) => (
        <a
          key={image.id}
          href={image.full_url}
          data-pswp-src={image.full_url}
          data-pswp-width="1600"
          data-pswp-height="1200"
          className="group relative block overflow-hidden rounded-2xl focus-visible:outline-none"
          aria-label={`Open photo ${index + 2} of ${images.length}`}
        >
          <img
            src={image.thumbnail_url || image.webp_url || image.medium_url}
            alt={`Palm ${palmCode} photo ${index + 2}`}
            loading="lazy"
            decoding="async"
            className="aspect-[4/3] w-full object-cover transition duration-500 group-hover:scale-[1.03] motion-reduce:transition-none"
          />
        </a>
      ))}
    </div>
  );
}
