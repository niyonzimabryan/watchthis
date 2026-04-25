export default function ErrorCard({ message, onRetry }) {
  return (
    <div className="p-4 bg-bg-card rounded-[20px] border border-warning-rose/25">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-warning-rose text-lg">&#9888;</span>
        <span className="text-[17px] font-semibold text-ink-primary">
          Something went wrong
        </span>
      </div>
      <p className="text-[17px] text-ink-secondary mb-3">{message}</p>
      <button
        onClick={onRetry}
        className="text-[17px] font-semibold text-accent-teal cursor-pointer hover:underline"
      >
        Try Again
      </button>
    </div>
  );
}
