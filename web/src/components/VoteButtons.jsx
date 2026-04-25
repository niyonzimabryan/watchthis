import { useState } from 'react';

export default function VoteButtons({ currentVote, onVote }) {
  const [showReason, setShowReason] = useState(false);
  const [reason, setReason] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleVote = (value) => {
    if (value === 0) {
      onVote(0);
      setShowReason(false);
      setSubmitted(false);
      setReason('');
      return;
    }
    onVote(value);
    setShowReason(true);
    setSubmitted(false);
  };

  const handleSubmitReason = () => {
    if (reason.trim()) {
      onVote(currentVote, reason.trim());
      setSubmitted(true);
      setShowReason(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-[13px] font-medium text-ink-secondary">
          Was this a good pick?
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => handleVote(currentVote === 1 ? 0 : 1)}
            className={`p-2 rounded-full transition-colors cursor-pointer ${
              currentVote === 1
                ? 'bg-success-mint/20 text-success-mint'
                : 'text-ink-secondary/50 hover:text-success-mint hover:bg-success-mint/10'
            }`}
            aria-label="Upvote"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill={currentVote === 1 ? 'currentColor' : 'none'}
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-5 h-5"
            >
              <path d="M7 10v12" />
              <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
            </svg>
          </button>
          <button
            onClick={() => handleVote(currentVote === -1 ? 0 : -1)}
            className={`p-2 rounded-full transition-colors cursor-pointer ${
              currentVote === -1
                ? 'bg-warning-rose/20 text-warning-rose'
                : 'text-ink-secondary/50 hover:text-warning-rose hover:bg-warning-rose/10'
            }`}
            aria-label="Downvote"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill={currentVote === -1 ? 'currentColor' : 'none'}
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-5 h-5"
            >
              <path d="M17 14V2" />
              <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" />
            </svg>
          </button>
        </div>
      </div>

      {showReason && currentVote !== 0 && !submitted && (
        <div className="flex gap-2 items-end">
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmitReason()}
            placeholder={currentVote === 1 ? 'What made it great?' : 'What was off?'}
            maxLength={280}
            className="flex-1 px-3 py-2 text-[13px] text-ink-primary bg-bg-primary border border-ink-secondary/15 rounded-[12px] focus:outline-none focus:border-accent-teal/50 transition-colors placeholder:text-ink-secondary/40"
          />
          <button
            onClick={handleSubmitReason}
            disabled={!reason.trim()}
            className="px-3 py-2 text-[13px] font-medium text-accent-teal cursor-pointer hover:underline disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send
          </button>
          <button
            onClick={() => setShowReason(false)}
            className="px-2 py-2 text-[13px] text-ink-secondary/50 cursor-pointer hover:text-ink-secondary"
          >
            Skip
          </button>
        </div>
      )}

      {submitted && (
        <p className="text-[13px] text-ink-secondary/60">Thanks for the feedback!</p>
      )}
    </div>
  );
}
