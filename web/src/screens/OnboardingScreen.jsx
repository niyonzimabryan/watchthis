import { motion } from 'framer-motion';
import PrimaryButton from '../components/PrimaryButton';

export default function OnboardingScreen({ onComplete }) {
  return (
    <div className="min-h-dvh bg-gradient-to-br from-bg-primary via-accent-teal/[0.15] to-accent-coral/[0.12] flex items-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md mx-auto px-8 py-12"
      >
        <h1 className="text-[34px] font-bold font-rounded text-ink-primary mb-4">
          WatchThis
        </h1>
        <p className="text-[20px] font-semibold font-rounded text-ink-secondary mb-3">
          Your social movie friend that picks one great thing to watch right
          now.
        </p>
        <p className="text-[17px] text-ink-secondary mb-8">
          No scrolling spiral. No 20-tab comparison. One confident pick, fast.
        </p>
        <PrimaryButton title="Let's pick something" pulse onClick={onComplete} />
      </motion.div>
    </div>
  );
}
