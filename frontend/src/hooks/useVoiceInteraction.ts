import { useState, useEffect, useRef, useCallback } from 'react';

// Window declaration for cross-browser Web Speech API
declare global {
  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }
}

export interface UseVoiceInteractionReturn {
  // Speech Recognition (Speech-to-Text)
  isListening: boolean;
  transcript: string;
  startListening: () => void;
  stopListening: () => void;
  clearTranscript: () => void;
  speechError: string | null;
  isSpeechRecognitionSupported: boolean;

  // Speech Synthesis (Text-to-Speech)
  speechEnabled: boolean;
  toggleSpeechEnabled: () => void;
  isSpeaking: boolean;
  speak: (text: string) => void;
  stopSpeaking: () => void;
  isSpeechSynthesisSupported: boolean;
}

export function useVoiceInteraction(): UseVoiceInteractionReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [speechError, setSpeechError] = useState<string | null>(null);

  const [speechEnabled, setSpeechEnabled] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const recognitionRef = useRef<any>(null);

  const isSpeechRecognitionSupported =
    typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

  const isSpeechSynthesisSupported =
    typeof window !== 'undefined' && 'speechSynthesis' in window;

  // Initialize SpeechRecognition instance if supported
  useEffect(() => {
    if (!isSpeechRecognitionSupported) return;

    try {
      const SpeechRecognitionConstructor =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognitionConstructor();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        setSpeechError(null);
      };

      recognition.onresult = (event: any) => {
        let currentText = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          currentText += event.results[i][0].transcript;
        }
        setTranscript(currentText);
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        const errType = event.error || 'unknown';
        if (errType === 'not-allowed' || errType === 'permission-denied') {
          setSpeechError('Microphone permission was denied. Please allow microphone access or type your question.');
        } else if (errType === 'no-speech') {
          setSpeechError('No speech was detected. Please try again or type your question.');
        } else if (errType !== 'aborted') {
          setSpeechError(`Voice input error (${errType}). Please use text input.`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } catch {
      // Graceful fallback for restricted environments
      recognitionRef.current = null;
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // Ignore
        }
      }
    };
  }, [isSpeechRecognitionSupported]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      if (!isSpeechRecognitionSupported) {
        setSpeechError('Speech recognition is not supported in this browser. Please type your question.');
      }
      return;
    }
    setSpeechError(null);
    setTranscript('');
    try {
      recognitionRef.current.start();
    } catch (err: any) {
      // If already started, stop and restart
      try {
        recognitionRef.current.stop();
        recognitionRef.current.start();
      } catch {
        setSpeechError('Could not start microphone. Please type your message.');
      }
    }
  }, [isSpeechRecognitionSupported]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch {
      // Ignore
    }
    setIsListening(false);
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript('');
  }, []);

  const toggleSpeechEnabled = useCallback(() => {
    setSpeechEnabled((prev) => {
      const next = !prev;
      if (!next && isSpeechSynthesisSupported && window.speechSynthesis) {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
      }
      return next;
    });
  }, [isSpeechSynthesisSupported]);

  const stopSpeaking = useCallback(() => {
    if (isSpeechSynthesisSupported && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // Ignore
      }
    }
    setIsSpeaking(false);
  }, [isSpeechSynthesisSupported]);

  const speak = useCallback(
    (rawText: string) => {
      if (!speechEnabled || !isSpeechSynthesisSupported || !window.speechSynthesis) return;

      // Clean markdown tags (*, #, _, `, etc.) for smooth natural voice speech
      const cleanText = rawText
        .replace(/[*#_`~>[\]]/g, '')
        .replace(/\n+/g, ' ')
        .trim();

      if (!cleanText) return;

      try {
        window.speechSynthesis.cancel(); // Stop any pending speech
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);

        window.speechSynthesis.speak(utterance);
      } catch {
        setIsSpeaking(false);
      }
    },
    [speechEnabled, isSpeechSynthesisSupported]
  );

  // Cancel any running speech synthesis when unmounting
  useEffect(() => {
    return () => {
      if (isSpeechSynthesisSupported && window.speechSynthesis) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // Ignore
        }
      }
    };
  }, [isSpeechSynthesisSupported]);

  return {
    isListening,
    transcript,
    startListening,
    stopListening,
    clearTranscript,
    speechError,
    isSpeechRecognitionSupported,
    speechEnabled,
    toggleSpeechEnabled,
    isSpeaking,
    speak,
    stopSpeaking,
    isSpeechSynthesisSupported,
  };
}
