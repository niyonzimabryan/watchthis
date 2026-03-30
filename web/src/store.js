import { useState, useCallback, useRef } from 'react';
import * as api from './api';

const LOADING_MESSAGES = [
  'Reading your vibe...',
  'Scanning high-confidence picks...',
  'Locking in one recommendation...',
];

const MAX_HISTORY = 12;
const STORAGE_KEY = 'watchthis.history';
const ONBOARDING_KEY = 'watchthis.onboarded';
const SESSION_KEY = 'watchthis.session';
const VOTES_KEY = 'watchthis.votes';
const CAST_DEVICE_KEY = 'watchthis.cast_device';

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveHistory(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

function loadVotes() {
  try {
    return JSON.parse(localStorage.getItem(VOTES_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveVotes(votes) {
  localStorage.setItem(VOTES_KEY, JSON.stringify(votes));
}

function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function useAppStore() {
  const [screen, setScreen] = useState(
    localStorage.getItem(ONBOARDING_KEY) ? 'input' : 'onboarding'
  );
  const [moodInput, setMoodInput] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('any');
  const [selectedLength, setSelectedLength] = useState('any');
  const [currentResponse, setCurrentResponse] = useState(null);
  const [history, setHistory] = useState(loadHistory);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0]);
  const [showSlowAction, setShowSlowAction] = useState(false);
  const [error, setError] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [lastWasRoulette, setLastWasRoulette] = useState(false);
  const [votes, setVotes] = useState(loadVotes);
  const [castStatus, setCastStatus] = useState('idle'); // idle | scanning | casting | sent | error
  const [castDevice, setCastDevice] = useState(localStorage.getItem(CAST_DEVICE_KEY) || null);
  const [castDevices, setCastDevices] = useState([]); // for device picker
  const [castError, setCastError] = useState(null);

  const excludedRef = useRef([]);
  const contextKeyRef = useRef(null);
  const abortRef = useRef(null);
  const timerRef = useRef(null);
  const slowRef = useRef(null);

  const addToHistory = useCallback((response) => {
    setHistory((prev) => {
      const filtered = prev.filter((r) => r.requestId !== response.requestId);
      const next = [response, ...filtered].slice(0, MAX_HISTORY);
      saveHistory(next);
      return next;
    });
  }, []);

  const startLoadingUX = useCallback(() => {
    setIsLoading(true);
    setShowSlowAction(false);
    setLoadingMessage(LOADING_MESSAGES[0]);
    let idx = 0;
    clearInterval(timerRef.current);
    clearTimeout(slowRef.current);
    timerRef.current = setInterval(() => {
      idx = (idx + 1) % LOADING_MESSAGES.length;
      setLoadingMessage(LOADING_MESSAGES[idx]);
    }, 1200);
    slowRef.current = setTimeout(() => setShowSlowAction(true), 8000);
  }, []);

  const stopLoadingUX = useCallback(() => {
    setIsLoading(false);
    setShowSlowAction(false);
    clearInterval(timerRef.current);
    clearTimeout(slowRef.current);
  }, []);

  const makeContextKey = useCallback(
    (isRoulette, mood) => {
      if (isRoulette) return `roulette|${selectedFormat}|${selectedLength}`;
      return `mood|${(mood || '').toLowerCase()}|${selectedFormat}|${selectedLength}`;
    },
    [selectedFormat, selectedLength]
  );

  const resetContextIfNeeded = useCallback(
    (key) => {
      if (contextKeyRef.current !== key) {
        excludedRef.current = [];
        contextKeyRef.current = key;
      }
    },
    []
  );

  const performRequest = useCallback(
    async (requestFn) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      startLoadingUX();
      setError(null);

      try {
        const response = await requestFn(controller.signal);
        if (!excludedRef.current.includes(response.recommendation.tmdbId)) {
          excludedRef.current.push(response.recommendation.tmdbId);
        }
        setCurrentResponse(response);
        addToHistory(response);
        setError(null);
        setScreen('result');
      } catch (e) {
        if (e.name !== 'AbortError') {
          setError(e.message || 'Unable to fetch recommendation right now.');
        }
      } finally {
        stopLoadingUX();
      }
    },
    [startLoadingUX, stopLoadingUX, addToHistory]
  );

  const completeOnboarding = useCallback(() => {
    localStorage.setItem(ONBOARDING_KEY, '1');
    setScreen('input');
  }, []);

  const submitMood = useCallback(() => {
    const trimmed = moodInput.trim();
    if (!trimmed) {
      setError('Tell us your mood first so we can pick one great title.');
      return;
    }
    setLastWasRoulette(false);
    resetContextIfNeeded(makeContextKey(false, trimmed));

    performRequest((signal) =>
      api.recommend(
        {
          moodInput: trimmed,
          sessionId: getSessionId(),
          format: selectedFormat,
          length: selectedLength,
          excludedTmdbIds: excludedRef.current,
        },
        signal
      )
    );
  }, [moodInput, selectedFormat, selectedLength, performRequest, resetContextIfNeeded, makeContextKey]);

  const startRoulette = useCallback(() => {
    setLastWasRoulette(true);
    resetContextIfNeeded(makeContextKey(true, null));

    performRequest((signal) =>
      api.roulette(
        {
          sessionId: getSessionId(),
          format: selectedFormat,
          length: selectedLength,
          excludedTmdbIds: excludedRef.current,
        },
        signal
      )
    );
  }, [selectedFormat, selectedLength, performRequest, resetContextIfNeeded, makeContextKey]);

  const spinAgain = useCallback(() => {
    if (!currentResponse) return;

    if (!excludedRef.current.includes(currentResponse.recommendation.tmdbId)) {
      excludedRef.current.push(currentResponse.recommendation.tmdbId);
    }

    const base = {
      sessionId: getSessionId(),
      format: selectedFormat,
      length: selectedLength,
      rerollOf: currentResponse.requestId,
      excludedTmdbIds: excludedRef.current,
    };

    if (lastWasRoulette) {
      performRequest((signal) => api.roulette(base, signal));
    } else {
      performRequest((signal) =>
        api.recommend({ ...base, moodInput: moodInput.trim() }, signal)
      );
    }
  }, [currentResponse, lastWasRoulette, moodInput, selectedFormat, selectedLength, performRequest]);

  const cancelRequest = useCallback(() => {
    abortRef.current?.abort();
    stopLoadingUX();
    setError('Request canceled.');
  }, [stopLoadingUX]);

  const newMood = useCallback(() => {
    setScreen('input');
    setError(null);
  }, []);

  const openHistoryItem = useCallback((item) => {
    setCurrentResponse(item);
    setShowHistory(false);
    setError(null);
    setScreen('result');
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const showOnTV = useCallback(async (deviceName) => {
    if (!currentResponse) return;
    const rec = currentResponse.recommendation;

    setCastError(null);
    setCastStatus(deviceName || castDevice ? 'casting' : 'scanning');

    try {
      const result = await api.castToTV({
        title: rec.title,
        year: rec.year,
        mediaType: rec.mediaType,
        runtime: rec.runtime,
        posterUrl: rec.posterUrl,
        genres: rec.genres,
        pitch: currentResponse.pitch,
        confidence: currentResponse.confidence,
        voteAverage: rec.voteAverage,
        rtScore: rec.rtScore,
        metacritic: rec.metacritic,
        imdbRating: rec.imdbRating,
        streamingSources: (currentResponse.streamingSources || []).map(s => ({
          name: s.name,
          type: s.type,
          webUrl: s.webUrl,
        })),
      }, deviceName || castDevice);

      if (result.needsSelection) {
        setCastDevices(result.devices);
        setCastStatus('picking');
        return;
      }

      if (result.sent) {
        const name = result.device;
        setCastDevice(name);
        localStorage.setItem(CAST_DEVICE_KEY, name);
        setCastStatus('sent');
        setTimeout(() => setCastStatus('idle'), 2500);
      }
    } catch (e) {
      setCastError(e.message);
      setCastStatus('error');
      setTimeout(() => setCastStatus('idle'), 3000);
    }
  }, [currentResponse, castDevice]);

  const selectCastDevice = useCallback((deviceName) => {
    setCastDevices([]);
    showOnTV(deviceName);
  }, [showOnTV]);

  const submitVote = useCallback((requestId, voteValue, reason) => {
    if (voteValue === 0) {
      setVotes((prev) => {
        const next = { ...prev };
        delete next[requestId];
        saveVotes(next);
        return next;
      });
      return;
    }
    setVotes((prev) => {
      const next = { ...prev, [requestId]: voteValue };
      saveVotes(next);
      return next;
    });
    api.vote(requestId, voteValue, getSessionId(), reason).catch(() => {});
  }, []);

  return {
    screen,
    moodInput,
    setMoodInput,
    selectedFormat,
    setSelectedFormat,
    selectedLength,
    setSelectedLength,
    currentResponse,
    history,
    isLoading,
    loadingMessage,
    showSlowAction,
    error,
    showHistory,
    setShowHistory,
    completeOnboarding,
    submitMood,
    startRoulette,
    spinAgain,
    cancelRequest,
    newMood,
    openHistoryItem,
    clearHistory,
    votes,
    submitVote,
    castStatus,
    castDevice,
    castDevices,
    castError,
    showOnTV,
    selectCastDevice,
  };
}
