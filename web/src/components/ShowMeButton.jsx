import { motion, AnimatePresence } from 'framer-motion';

const TV_ICON = (
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
    <rect x="2" y="7" width="20" height="15" rx="2" ry="2" />
    <polyline points="17 2 12 7 7 2" />
  </svg>
);

const CHECK_ICON = (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="w-5 h-5"
  >
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const SPINNER = (
  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
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
);

const STATUS_TEXT = {
  idle: 'Show Me',
  scanning: 'Finding TV...',
  casting: 'Casting...',
  sent: 'On your TV!',
  error: 'Try again',
  picking: 'Pick your TV',
};

export default function ShowMeButton({ store }) {
  const { castStatus, castDevices, castError, showOnTV, selectCastDevice } = store;
  const isBusy = castStatus === 'scanning' || castStatus === 'casting';
  const isSent = castStatus === 'sent';
  const isPicking = castStatus === 'picking';
  const isError = castStatus === 'error';

  return (
    <div className="relative">
      {/* Device picker dropdown */}
      <AnimatePresence>
        {isPicking && castDevices.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="absolute bottom-full mb-2 left-0 right-0 bg-bg-card rounded-2xl border border-ink-secondary/10 shadow-lg overflow-hidden z-20"
          >
            <p className="px-4 pt-3 pb-1 text-[13px] font-medium text-ink-secondary">
              Select your TV
            </p>
            {castDevices.map((d) => (
              <button
                key={d.uuid || d.name}
                onClick={() => selectCastDevice(d.name)}
                className="w-full text-left px-4 py-3 text-[15px] text-ink-primary hover:bg-ink-secondary/5 transition-colors cursor-pointer flex items-center gap-3"
              >
                {TV_ICON}
                <span className="truncate">{d.name}</span>
                <span className="text-[12px] text-ink-secondary ml-auto">{d.ip}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* The button */}
      <motion.button
        onClick={() => showOnTV()}
        disabled={isBusy}
        whileTap={!isBusy ? { scale: 0.97 } : {}}
        className={`
          showme-btn w-full min-h-[52px] px-5 rounded-[14px] font-semibold text-[17px]
          flex items-center justify-center gap-2.5 transition-all cursor-pointer select-none
          text-white relative overflow-hidden
          ${isBusy ? 'opacity-70 cursor-wait' : ''}
          ${isSent ? 'showme-sent' : ''}
          ${isError ? 'showme-error' : ''}
        `}
      >
        {isBusy ? SPINNER : isSent ? CHECK_ICON : TV_ICON}
        <span>{STATUS_TEXT[castStatus] || 'Show Me'}</span>
      </motion.button>

      {/* Error message */}
      <AnimatePresence>
        {isError && castError && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-[13px] text-warning-rose mt-2 text-center"
          >
            {castError}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
