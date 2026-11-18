import type { StaticImageData } from "next/image";
import fieldTrees from "../../public/images/field-trees.jpg";
import heroField from "../../public/images/hero-field.jpg";
import rowsAerial from "../../public/images/rows-aerial.jpg";

/** Unsplash photos (Unsplash License, free to use): credits are in public/images/CREDITS.md and the footer. */
export type Photo = { img: StaticImageData; credit: string; href: string; position: string };

export const PHOTOS: Photo[] = [
  { img: heroField, credit: "Max Raber", href: "https://unsplash.com/photos/FnxZF_i-iJM", position: "50% 42%" },
  { img: rowsAerial, credit: "Bernd Dittrich", href: "https://unsplash.com/photos/aS14a9_TEeg", position: "50% 38%" },
  { img: fieldTrees, credit: "Bernd Dittrich", href: "https://unsplash.com/photos/fnZ-FXWxl2c", position: "50% 50%" },
];

export const HOME_PHOTO = PHOTOS[0];

/** The same plot always gets the same photo (the card and the plot page agree): a small hash of its id picks one of the three. */
export function photoFor(id: string): Photo {
  let hash = 2166136261;
  for (const ch of id) hash = Math.imul(hash ^ ch.charCodeAt(0), 16777619) >>> 0;
  return PHOTOS[hash % PHOTOS.length];
}
