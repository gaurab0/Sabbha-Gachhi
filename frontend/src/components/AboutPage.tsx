import { Link } from 'react-router-dom'
import { PhotoFrame } from './PhotoFrame'
import { PHOTOS, photoSrc, photoSrcSet } from '../lib/photos'

export default function AboutPage() {
  return (
    <main className="container py-16">
      <p className="text-caption text-text/60 tracking-wider mb-4">Our mission</p>
      <h1 className="text-heading sm:text-display text-primary leading-tight mb-6">
        A dignified continuation of the panji tradition
      </h1>
      <div className="max-w-[620px] text-body leading-relaxed">
        <p>
          Sabha Gachhi is a private, non-profit community platform preserving
          genealogy-verified, dowry-free introductions through the Saurath Sabha
          Gachhi tradition.
        </p>
        <p className="mt-5">
          We are not a dating service. Families remain at the centre, with
          panjikars guiding the careful work of reviewing lineage and making
          introductions with discretion.
        </p>
      </div>
      <div className="mt-12 grid gap-5 sm:grid-cols-2">
        <PhotoFrame
          src={photoSrc(PHOTOS.hastamelap)}
          srcSet={photoSrcSet(PHOTOS.hastamelap)}
          alt={PHOTOS.hastamelap.alt}
          width={PHOTOS.hastamelap.width}
          height={PHOTOS.hastamelap.height}
          aspectRatio="4/3"
          sizes="(max-width: 640px) 100vw, 300px"
          caption="The hastamelap — two families joined in trust."
        />
        <PhotoFrame
          src={photoSrc(PHOTOS.havan)}
          srcSet={photoSrcSet(PHOTOS.havan)}
          alt={PHOTOS.havan.alt}
          width={PHOTOS.havan.width}
          height={PHOTOS.havan.height}
          aspectRatio="4/3"
          sizes="(max-width: 640px) 100vw, 300px"
          caption="Ritual and consent anchor every introduction."
        />
      </div>
      <div className="mt-10 flex flex-wrap gap-4">
        <Link to="/mela" className="btn-outline">Learn about Saurath Mela</Link>
        <Link to="/register" className="btn-primary">Request an Invitation</Link>
      </div>
    </main>
  )
}
