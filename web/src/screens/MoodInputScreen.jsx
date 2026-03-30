import FilterChip from '../components/FilterChip';
import PrimaryButton from '../components/PrimaryButton';
import ErrorCard from '../components/ErrorCard';

const FORMAT_OPTIONS = [
  { value: 'tv', label: 'TV' },
  { value: 'movie', label: 'Movie' },
  { value: 'any', label: 'Any' },
];

const LENGTH_OPTIONS = [
  { value: 'quick', label: 'Short' },
  { value: 'long', label: 'Long' },
  { value: 'any', label: 'Any' },
];

export default function MoodInputScreen({ store }) {
  return (
    <div className="min-h-dvh bg-bg-primary">
      {/* Header bar */}
      <div className="sticky top-0 z-10 bg-bg-primary/80 backdrop-blur-md border-b border-ink-secondary/[0.08]">
        <div className="max-w-md mx-auto px-4 h-14 flex items-center justify-between">
          <h2 className="text-[17px] font-semibold text-ink-primary">
            Pick For Tonight
          </h2>
          <button
            onClick={() => store.setShowHistory(true)}
            className="text-accent-teal hover:text-accent-teal/80 transition-colors cursor-pointer p-2"
            aria-label="Open history"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-5 h-5"
            >
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
              <path d="M12 7v5l4 2" />
            </svg>
          </button>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 pt-4 pb-8 space-y-6">
        {/* Header text */}
        <div>
          <h1 className="text-[28px] font-bold font-rounded text-ink-primary mb-2">
            What are you in the mood for?
          </h1>
          <p className="text-[17px] text-ink-secondary">
            Describe your vibe in one sentence. We will return one
            recommendation.
          </p>
        </div>

        {/* Mood card */}
        <div className="p-4 bg-bg-card rounded-[20px]">
          <p className="text-[17px] font-semibold text-ink-primary mb-3">
            Mood
          </p>
          <textarea
            value={store.moodInput}
            onChange={(e) => store.setMoodInput(e.target.value)}
            placeholder="e.g. Something feel-good but not cheesy..."
            maxLength={500}
            rows={4}
            className="w-full p-2 text-[17px] text-ink-primary bg-bg-card border border-ink-secondary/15 rounded-[20px] resize-none focus:outline-none focus:border-accent-teal/50 transition-colors placeholder:text-ink-secondary/40"
          />
        </div>

        {/* Filters — sleek inline toggles */}
        <div className="flex items-center justify-center gap-0.5 flex-wrap">
          {FORMAT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => store.setSelectedFormat(opt.value)}
              className={`px-3 py-1 rounded-full text-[12px] font-medium transition-all cursor-pointer select-none ${
                store.selectedFormat === opt.value
                  ? 'bg-ink-primary text-bg-primary'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {opt.label}
            </button>
          ))}
          <span className="text-ink-secondary/20 mx-0.5 text-[12px]">/</span>
          {LENGTH_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => store.setSelectedLength(opt.value)}
              className={`px-3 py-1 rounded-full text-[12px] font-medium transition-all cursor-pointer select-none ${
                store.selectedLength === opt.value
                  ? 'bg-ink-primary text-bg-primary'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Action buttons */}
        <div className="space-y-3">
          <PrimaryButton
            title="Pick For Me"
            pulse
            isLoading={store.isLoading}
            onClick={store.submitMood}
          />
          <PrimaryButton
            title="Roulette"
            style="outline"
            isLoading={store.isLoading}
            onClick={store.startRoulette}
          />
        </div>

        {/* Loading state */}
        {store.isLoading && (
          <div className="p-4 bg-bg-card rounded-[20px]">
            <p className="text-[17px] font-semibold text-ink-primary mb-3">
              {store.loadingMessage}
            </p>
            <div className="h-3 bg-ink-secondary/12 rounded-full shimmer" />
            {store.showSlowAction && (
              <button
                onClick={store.cancelRequest}
                className="mt-3 text-[13px] font-medium text-accent-teal cursor-pointer hover:underline"
              >
                Go back
              </button>
            )}
          </div>
        )}

        {/* Error */}
        {!store.isLoading && store.error && (
          <ErrorCard message={store.error} onRetry={store.submitMood} />
        )}
      </div>
    </div>
  );
}
