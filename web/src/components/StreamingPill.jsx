const ICONS = {
  free: '\uD83C\uDF81',
  rent: '\uD83D\uDCB2',
  buy: '\uD83D\uDCB2',
  info: '\u2139\uFE0F',
};

export default function StreamingPill({ name, type, webUrl }) {
  const icon = ICONS[type?.toLowerCase()] || '\u25B6\uFE0F';

  const pill = (
    <span className="inline-flex items-center gap-1.5 px-3 py-2 bg-accent-teal text-bg-card text-[13px] font-medium rounded-full whitespace-nowrap cursor-pointer hover:bg-accent-teal/90 transition-colors">
      <span className="text-xs">{icon}</span>
      {name}
    </span>
  );

  if (webUrl) {
    return (
      <a href={webUrl} target="_blank" rel="noopener noreferrer">
        {pill}
      </a>
    );
  }

  return pill;
}
