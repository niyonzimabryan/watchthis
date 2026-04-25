import { useState } from 'react';

export default function PosterView({ posterUrl, title }) {
  const [loaded, setLoaded] = useState(false);
  const [errored, setErrored] = useState(false);

  const initials = title
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase() || 'WT';

  const showPlaceholder = !posterUrl || errored;

  return (
    <div className="relative w-full aspect-[2/3] rounded-[20px] overflow-hidden">
      {/* Gradient background (always rendered, visible as placeholder or behind loading) */}
      <div className="absolute inset-0 bg-gradient-to-br from-accent-teal/90 via-accent-coral/90 to-accent-gold/75 flex flex-col items-center justify-center gap-3">
        <span className="text-[34px] font-bold text-white font-rounded">
          {initials}
        </span>
        <span className="text-[13px] font-medium text-white/85">
          WatchThis
        </span>
      </div>

      {/* Actual poster image */}
      {posterUrl && !errored && (
        <img
          src={posterUrl}
          alt={title}
          onLoad={() => setLoaded(true)}
          onError={() => setErrored(true)}
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            loaded ? 'opacity-100' : 'opacity-0'
          }`}
        />
      )}

      {/* Shimmer while loading */}
      {posterUrl && !loaded && !errored && (
        <div className="absolute inset-0 shimmer" />
      )}
    </div>
  );
}
