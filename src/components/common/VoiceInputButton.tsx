import React, { useState, useEffect, useRef } from 'react';
import { Mic, AlertCircle } from 'lucide-react';

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  onTranscript,
  disabled = false
}) => {
  const [isListening, setIsListening] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
    };
  }, []);

  const showErrorToast = (msg: string) => {
    setErrorMessage(msg);
    setTimeout(() => {
      setErrorMessage((prev) => (prev === msg ? null : prev));
    }, 4000);
  };

  const toggleListening = () => {
    if (disabled) return;

    // Check Web Speech API availability
    const SpeechRecognitionAPI =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      showErrorToast('Voice input is not supported in this browser.');
      return;
    }

    if (isListening) {
      // Stop recording if currently active
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognitionAPI();
      recognitionRef.current = recognition;

      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = navigator.language || 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        setErrorMessage(null);
      };

      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        const transcriptText = finalTranscript || interimTranscript;
        if (transcriptText) {
          onTranscript(transcriptText);
        }
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        const err = event.error;
        if (err === 'not-allowed' || err === 'service-not-allowed') {
          showErrorToast('Microphone permission denied. Please allow microphone access.');
        } else if (err === 'no-speech') {
          showErrorToast('No speech detected. Please try speaking again.');
        } else if (err === 'audio-capture') {
          showErrorToast('No microphone found. Please check audio input hardware.');
        } else if (err !== 'aborted') {
          showErrorToast('Voice recognition error. Please try again.');
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } catch (err) {
      console.error('Speech recognition error:', err);
      setIsListening(false);
      showErrorToast('Unable to start voice input.');
    }
  };

  return (
    <div className="relative inline-flex items-center">
      {/* Error / Permission Toast Banner */}
      {errorMessage && (
        <div className="absolute right-0 -top-11 z-50 px-3 py-1.5 rounded-xl text-xs font-medium bg-rose-900/90 text-rose-200 border border-rose-700 shadow-2xl flex items-center space-x-1.5 whitespace-nowrap animate-in fade-in slide-in-from-bottom-2">
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Microphone Toggle Button */}
      <button
        type="button"
        onClick={toggleListening}
        disabled={disabled}
        className={`p-1.5 md:p-2 rounded-xl transition-all cursor-pointer flex items-center justify-center disabled:opacity-40 active:scale-95 ${
          isListening
            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40 shadow-[0_0_12px_rgba(244,63,94,0.4)] animate-pulse'
            : 'text-slate-400 dark:text-[#A3A3A3] hover:text-brand-600 dark:hover:text-[#8AB4F8] hover:bg-slate-800/60 dark:hover:bg-[#383838]'
        }`}
        title={isListening ? 'Listening... Click to stop recording' : 'Click to speak question'}
      >
        <Mic className={`w-4 h-4 md:w-5 md:h-5 ${isListening ? 'text-rose-400 animate-bounce' : ''}`} />
      </button>
    </div>
  );
};
