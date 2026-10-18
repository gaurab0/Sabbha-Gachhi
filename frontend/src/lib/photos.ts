// Central registry for the photographs in public/images (see
// scripts/optimize_images.py for how the -480w/-768w/-1024w variants are built).

export type PhotoKey = "heroMandap" | "hastamelap" | "saptapadi" | "havan";

export interface PhotoDef {
  /** Base name under /images (no size suffix, no extension). */
  base: string;
  /** Responsive widths actually generated for this photo. */
  widths: number[];
  /** Intrinsic dimensions of the full-size asset (for width/height hints). */
  width: number;
  height: number;
  alt: string;
}

export const PHOTOS: Record<PhotoKey, PhotoDef> = {
  heroMandap: {
    base: "hero-mandap",
    widths: [480, 768, 1024],
    width: 1024,
    height: 682,
    alt: "A decorated wedding mandap beneath the mango trees at Saurath",
  },
  hastamelap: {
    base: "hastamelap-union",
    widths: [480, 768, 1024],
    width: 1024,
    height: 682,
    alt: "A hastamelap — the joining of hands in a Maithil wedding",
  },
  saptapadi: {
    base: "saptapadi-kalash",
    widths: [480, 682],
    width: 682,
    height: 1024,
    alt: "A kalash and sacred vessels set out for the saptapadi rites",
  },
  havan: {
    base: "sacred-havan-fire",
    widths: [480, 768, 1024],
    width: 1024,
    height: 683,
    alt: "The sacred havan fire tended during wedding rituals",
  },
};

export function photoSrc(photo: PhotoDef): string {
  return `/images/${photo.base}.webp`;
}

export function photoSrcSet(photo: PhotoDef): string {
  return photo.widths
    .map((w) => `/images/${photo.base}-${w}w.webp ${w}w`)
    .join(", ");
}
