import { type ImgHTMLAttributes } from "react";

interface PhotoFrameProps extends ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string;
  srcSet?: string;
  sizes?: string;
  width?: number;
  height?: number;
  aspectRatio?: string;
  caption?: string;
  priority?: boolean;
  objectPosition?: string;
  className?: string;
}

export function PhotoFrame({
  src,
  alt,
  srcSet,
  sizes = "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 600px",
  width,
  height,
  aspectRatio = "3/2",
  caption,
  priority = false,
  objectPosition = "center",
  className = "",
  ...rest
}: PhotoFrameProps) {
  return (
    <figure className={`photo-frame-wrapper m-0 ${className}`}>
      <div
        className="photo-frame relative w-full overflow-hidden rounded-lg border border-border bg-bg shadow-xs transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-md"
        style={{ aspectRatio }}>
        {/* Subtle decorative inner hairline */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-10 rounded-lg ring-1 ring-inset ring-black/5"
        />
        <img
          src={src}
          srcSet={srcSet}
          sizes={sizes}
          alt={alt}
          width={width}
          height={height}
          loading={priority ? "eager" : "lazy"}
          decoding={priority ? "sync" : "async"}
          // fetchPriority for React 19 / modern browsers
          {...(priority ? { fetchPriority: "high" } : {})}
          style={{ objectPosition }}
          className="photo-frame__img block h-full w-full object-cover transition-transform duration-500 ease-out hover:scale-[1.015]"
          {...rest}
        />
      </div>
      {caption && (
        <figcaption className="photo-frame__caption mt-2.5 font-serif text-[0.84rem] italic leading-normal text-text/65">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}
