export default function ConfidenceBadge({ confidence }) {
  const pct = Math.round(confidence * 100);
  return (
    <span className="inline-flex items-center gap-2 px-3 py-2 bg-success-mint/14 rounded-full">
      <span className="w-2 h-2 rounded-full bg-success-mint" />
      <span className="text-[13px] font-medium text-ink-primary">
        {pct}% match
      </span>
    </span>
  );
}
