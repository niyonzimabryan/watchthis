export default function PrimaryButton({
  title,
  style = 'filled',
  isLoading = false,
  isEnabled = true,
  pulse = false,
  onClick,
}) {
  const disabled = !isEnabled || isLoading;

  const base =
    'w-full min-h-[52px] px-4 rounded-[14px] font-semibold text-[17px] flex items-center justify-center gap-2 transition-opacity cursor-pointer select-none';

  const filled =
    'bg-gradient-to-r from-accent-teal to-accent-coral text-white';

  const outline =
    'bg-bg-card text-accent-teal border border-accent-teal/35';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${style === 'filled' ? filled : outline} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${pulse && !disabled ? 'pulse-cta' : ''}`}
    >
      {isLoading && (
        <svg
          className="animate-spin h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            className="opacity-25"
          />
          <path
            d="M4 12a8 8 0 018-8"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </svg>
      )}
      {title}
    </button>
  );
}
