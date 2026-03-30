import { motion } from 'framer-motion';
import PosterView from '../components/PosterView';
import ConfidenceBadge from '../components/ConfidenceBadge';
import StreamingPill from '../components/StreamingPill';
import PrimaryButton from '../components/PrimaryButton';
import ShowMeButton from '../components/ShowMeButton';
import VoteButtons from '../components/VoteButtons';
import ErrorCard from '../components/ErrorCard';

export default function ResultScreen({ store }) {
  const response = store.currentResponse;
  if (!response) return null;

  const rec = response.recommendation;
  const meta = [
    rec.mediaType?.toUpperCase(),
    rec.year,
    rec.runtime ? `${rec.runtime}m` : null,
  ]
    .filter(Boolean)
    .join(' \u2022 ');

  return (
    <div className="min-h-dvh bg-bg-primary">
      {/* Header bar */}
      <div className="sticky top-0 z-10 bg-bg-primary/80 backdrop-blur-md border-b border-ink-secondary/[0.08]">
        <div className="max-w-md mx-auto px-4 h-14 flex items-center justify-between">
          <h2 className="text-[17px] font-semibold text-ink-primary">
            Your Pick
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
        {/* Result card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="p-4 bg-bg-card rounded-[20px] space-y-4"
        >
          <PosterView posterUrl={rec.posterUrl} title={rec.title} />

          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-[28px] font-bold font-rounded text-ink-primary truncate">
                {rec.title}
              </h3>
              <p className="text-[13px] font-medium text-ink-secondary">
                {meta}
              </p>
            </div>
            <ConfidenceBadge confidence={response.confidence} />
          </div>

          <p className="text-[17px] text-ink-primary leading-relaxed">
            {response.pitch}
          </p>

          {/* Vote buttons */}
          <VoteButtons
            currentVote={store.votes[response.requestId] || 0}
            onVote={(v, reason) => store.submitVote(response.requestId, v, reason)}
          />

          {/* Streaming sources */}
          <div>
            <p className="text-[17px] font-semibold text-ink-primary mb-2">
              Where to watch
            </p>
            {response.streamingSources?.length > 0 ? (
              <div className="flex gap-2 overflow-x-auto hide-scrollbar pb-1">
                {response.streamingSources.map((s, i) => (
                  <StreamingPill
                    key={s.sourceId || `${s.name}-${i}`}
                    name={s.name}
                    type={s.type}
                    webUrl={s.webUrl}
                  />
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-ink-secondary">
                Find where to watch
              </p>
            )}
          </div>
        </motion.div>

        {/* Loading on reroll */}
        {store.isLoading && (
          <div className="p-4 bg-bg-card rounded-[20px]">
            <p className="text-[17px] font-semibold text-ink-primary mb-3">
              {store.loadingMessage}
            </p>
            <div className="h-3.5 bg-ink-secondary/12 rounded-full shimmer" />
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

        {/* Error on reroll */}
        {!store.isLoading && store.error && (
          <ErrorCard message={store.error} onRetry={store.spinAgain} />
        )}

        {/* Actions */}
        <div className="space-y-3">
          <ShowMeButton store={store} />
          <PrimaryButton
            title="Spin Again"
            isLoading={store.isLoading}
            onClick={store.spinAgain}
          />
          <PrimaryButton
            title="New Mood"
            style="outline"
            isEnabled={!store.isLoading}
            onClick={store.newMood}
          />
        </div>
      </div>
    </div>
  );
}
