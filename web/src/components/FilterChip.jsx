export default function FilterChip({ label, isSelected, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-2 min-h-[44px] rounded-[14px] text-[13px] font-medium border transition-colors cursor-pointer select-none ${
        isSelected
          ? 'bg-accent-teal text-bg-card border-accent-teal'
          : 'bg-bg-card text-ink-primary border-ink-secondary/[0.18] hover:border-ink-secondary/40'
      }`}
    >
      {label}
    </button>
  );
}
