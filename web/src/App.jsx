import { useAppStore } from './store';
import OnboardingScreen from './screens/OnboardingScreen';
import MoodInputScreen from './screens/MoodInputScreen';
import ResultScreen from './screens/ResultScreen';
import HistorySheet from './screens/HistorySheet';

export default function App() {
  const store = useAppStore();

  return (
    <>
      {store.screen === 'onboarding' && (
        <OnboardingScreen onComplete={store.completeOnboarding} />
      )}
      {store.screen === 'input' && <MoodInputScreen store={store} />}
      {store.screen === 'result' && <ResultScreen store={store} />}

      <HistorySheet store={store} />
    </>
  );
}
