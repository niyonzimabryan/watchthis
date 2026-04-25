import { motion, AnimatePresence } from 'framer-motion';

export default function HistorySheet({ store }) {
  return (
    <AnimatePresence>
      {store.showHistory && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => store.setShowHistory(false)}
            className="fixed inset-0 bg-black/30 z-40"
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 400, damping: 35 }}
            className="fixed inset-x-0 bottom-0 z-50 bg-bg-card rounded-t-[24px] max-h-[70dvh] flex flex-col"
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 rounded-full bg-ink-secondary/20" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-ink-secondary/[0.08]">
              <button
                onClick={() => store.setShowHistory(false)}
                className="text-[17px] text-accent-teal cursor-pointer hover:underline"
              >
                Close
              </button>
              <h3 className="text-[17px] font-semibold text-ink-primary">
                Recent Picks
              </h3>
              {store.history.length > 0 ? (
                <button
                  onClick={store.clearHistory}
                  className="text-[17px] text-warning-rose cursor-pointer hover:underline"
                >
                  Clear
                </button>
              ) : (
                <span className="w-12" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {store.history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-ink-secondary">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    className="w-12 h-12 mb-3 opacity-40"
                  >
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                    <path d="M3 3v5h5" />
                    <path d="M12 7v5l4 2" />
                  </svg>
                  <p className="text-[17px] font-semibold">No history yet</p>
                  <p className="text-[13px] mt-1">
                    Your recent picks will show up here.
                  </p>
                </div>
              ) : (
                <ul>
                  {store.history.map((item) => {
                    const rec = item.recommendation;
                    const meta = [
                      rec.mediaType?.toUpperCase(),
                      rec.year,
                      rec.runtime ? `${rec.runtime}m` : null,
                    ]
                      .filter(Boolean)
                      .join(' \u2022 ');

                    const itemVote = store.votes[item.requestId];

                    return (
                      <li key={item.requestId}>
                        <button
                          onClick={() => store.openHistoryItem(item)}
                          className="w-full text-left px-4 py-3 hover:bg-ink-secondary/[0.04] transition-colors cursor-pointer border-b border-ink-secondary/[0.06]"
                        >
                          <div className="flex items-center gap-2">
                            <p className="text-[17px] font-semibold text-ink-primary truncate flex-1">
                              {rec.title}
                            </p>
                            {itemVote === 1 && (
                              <span className="text-success-mint text-sm" title="Upvoted">&#128077;</span>
                            )}
                            {itemVote === -1 && (
                              <span className="text-warning-rose text-sm" title="Downvoted">&#128078;</span>
                            )}
                          </div>
                          <p className="text-[13px] font-medium text-ink-secondary">
                            {meta}
                          </p>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
