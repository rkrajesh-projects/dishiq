import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Square,
  AlertCircle,
  HelpCircle,
  RotateCcw,
  CheckCircle2,
} from 'lucide-react';
import { askCookingCompanion } from '../../api/cooking';
import { CompanionMessage, CompanionChatResponse } from '../../types/cooking';
import { useVoiceInteraction } from '../../hooks/useVoiceInteraction';

interface CookingCompanionCardProps {
  sessionId: string;
  recipeName: string;
  currentStepIndex: number;
  totalSteps: number;
  currentInstruction?: string | null;
}

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  responseMode?: 'llm' | 'deterministic_fallback';
  provider?: string | null;
  suggestedActions?: string[];
  disclaimer?: string;
  timestamp: string;
}

export const CookingCompanionCard: React.FC<CookingCompanionCardProps> = ({
  sessionId,
  recipeName,
  currentStepIndex,
  totalSteps,
  currentInstruction,
}) => {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
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
  } = useVoiceInteraction();

  // Populate input when speech recognition produces text
  useEffect(() => {
    if (transcript) {
      setInputValue(transcript);
    }
  }, [transcript]);

  // Initial welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `Hello! I am your DishIQ Kitchen Companion for **${recipeName}**.\n\nYou are on **Step ${
            currentStepIndex + 1
          } of ${totalSteps}**:\n*${
            currentInstruction || 'Follow the step instructions.'
          }*\n\nAsk me anything about cooking techniques, checking doneness, ingredient substitutions, or missed steps!`,
          responseMode: 'deterministic_fallback',
          suggestedActions: [
            'What should I do in this step?',
            'How do I know when it\'s done?',
            'Can I substitute an ingredient?',
            'What should I prepare next?',
          ],
          disclaimer:
            'AI suggestions are supplementary. Stored recipe instructions remain authoritative.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }
  }, [recipeName, currentStepIndex, totalSteps, currentInstruction]);

  // Scroll to bottom on new messages (safely handling environments without scrollIntoView)
  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  const handleSendMessage = async (textToSend?: string) => {
    const rawText = textToSend !== undefined ? textToSend : inputValue;
    const cleanText = rawText.trim();
    if (!cleanText || isLoading) return;

    if (isListening) {
      stopListening();
    }
    clearTranscript();

    const userMsgId = `user-${Date.now()}`;
    const userDisplayMsg: DisplayMessage = {
      id: userMsgId,
      role: 'user',
      content: cleanText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userDisplayMsg]);
    setInputValue('');
    setError(null);
    setIsLoading(true);

    try {
      const historyPayload: CompanionMessage[] = messages
        .filter((m) => m.id !== 'welcome')
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const res: CompanionChatResponse = await askCookingCompanion({
        cooking_session_id: sessionId,
        message: cleanText,
        step_index: currentStepIndex,
        conversation_history: historyPayload,
      });

      const assistantMsg: DisplayMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.reply,
        responseMode: res.response_mode,
        provider: res.provider,
        suggestedActions: res.suggested_actions,
        disclaimer: res.disclaimer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Read aloud if TTS is enabled
      if (speechEnabled) {
        speak(res.reply);
      }
    } catch (err: any) {
      const errMsg =
        err?.response?.data?.detail ||
        'Could not connect to the cooking companion. Please try again.';
      setError(errMsg);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleChipClick = (chipText: string) => {
    handleSendMessage(chipText);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage();
  };

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 shadow-sm flex flex-col h-[650px] overflow-hidden"
      data-testid="cooking-companion-panel"
      role="region"
      aria-label="AI Cooking Companion"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100 bg-[#FAF8F3] flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-800 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-emerald-700" />
          </div>
          <div>
            <h2 className="text-xs font-black text-gray-900 flex items-center gap-1.5">
              <span>AI Cooking Companion</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100/70 text-emerald-900">
                Step {currentStepIndex + 1}
              </span>
            </h2>
            <p className="text-[10px] text-gray-500 font-medium">
              Context-aware culinary guidance
            </p>
          </div>
        </div>

        {/* Voice TTS & Stop Controls */}
        <div className="flex items-center gap-1.5">
          {isSpeaking && (
            <button
              type="button"
              onClick={stopSpeaking}
              className="p-1.5 rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 transition-colors text-xs flex items-center gap-1"
              title="Stop speaking"
              aria-label="Stop reading aloud"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span className="text-[10px] font-bold">Stop</span>
            </button>
          )}

          {isSpeechSynthesisSupported && (
            <button
              type="button"
              onClick={toggleSpeechEnabled}
              className={`p-1.5 rounded-lg text-xs transition-colors flex items-center gap-1 ${
                speechEnabled
                  ? 'bg-emerald-700 text-white shadow-xs'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={speechEnabled ? 'Voice output enabled' : 'Voice output muted'}
              aria-label={speechEnabled ? 'Disable spoken answers' : 'Enable spoken answers'}
            >
              {speechEnabled ? (
                <Volume2 className="w-3.5 h-3.5" />
              ) : (
                <VolumeX className="w-3.5 h-3.5" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Authoritative Recipe Instruction Context Banner */}
      <div className="px-4 py-2.5 bg-emerald-50/50 border-b border-emerald-100/60 text-xs flex items-start gap-2">
        <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
        <div className="flex-1 text-[11px] leading-relaxed">
          <span className="font-bold text-emerald-950 uppercase tracking-wider text-[9px] block">
            Original Recipe Step {currentStepIndex + 1} (Authoritative):
          </span>
          <p className="text-gray-700 line-clamp-2">
            {currentInstruction || 'Follow recipe step instruction.'}
          </p>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/30">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            {/* Role Header & Badges */}
            <div className="flex items-center gap-1.5 mb-1 text-[10px] text-gray-500">
              {msg.role === 'user' ? (
                <span className="font-bold text-gray-700">You</span>
              ) : (
                <>
                  <span className="font-extrabold text-emerald-900 bg-emerald-100/80 px-2 py-0.2 rounded-full">
                    AI Suggestion
                  </span>
                  <span className="text-gray-400">
                    {msg.responseMode === 'llm'
                      ? `AI (${msg.provider || 'Live'})`
                      : 'Deterministic Guide'}
                  </span>
                </>
              )}
              <span>•</span>
              <span>{msg.timestamp}</span>
            </div>

            {/* Bubble */}
            <div
              className={`p-3.5 rounded-2xl max-w-[90%] text-xs leading-relaxed shadow-2xs ${
                msg.role === 'user'
                  ? 'bg-emerald-700 text-white rounded-br-xs font-medium'
                  : 'bg-white border border-gray-100 text-gray-800 rounded-bl-xs'
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>

              {/* Disclaimer for assistant */}
              {msg.role === 'assistant' && msg.disclaimer && (
                <p className="mt-2.5 pt-2 border-t border-gray-100 text-[9px] text-gray-400 italic">
                  {msg.disclaimer}
                </p>
              )}
            </div>

            {/* Suggested quick action chips attached to assistant turn */}
            {msg.role === 'assistant' &&
              msg.suggestedActions &&
              msg.suggestedActions.length > 0 &&
              msg.id === messages[messages.length - 1]?.id && (
                <div className="mt-2 flex flex-wrap gap-1.5 max-w-[95%]">
                  {msg.suggestedActions.map((action, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => handleChipClick(action)}
                      className="text-[11px] font-semibold bg-white border border-emerald-200 text-emerald-800 hover:bg-emerald-50 px-2.5 py-1 rounded-full transition-all text-left shadow-2xs"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              )}
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-gray-500 bg-white p-3 rounded-2xl border border-gray-100 w-fit">
            <Sparkles className="w-3.5 h-3.5 animate-spin text-emerald-600" />
            <span>Consulting culinary knowledge...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Voice Listening Banner */}
      {isListening && (
        <div className="px-4 py-2 bg-emerald-100 text-emerald-900 border-t border-emerald-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-ping shrink-0" />
            <span className="font-bold text-[11px]">
              Listening... Speak your question now.
            </span>
          </div>
          <button
            type="button"
            onClick={stopListening}
            className="text-[10px] font-extrabold underline hover:text-emerald-950"
          >
            Done Speaking
          </button>
        </div>
      )}

      {/* Error Banners */}
      {(error || speechError) && (
        <div className="px-4 py-2 bg-rose-50 border-t border-rose-100 text-rose-800 text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-600" />
            <span className="text-[11px]">{error || speechError}</span>
          </div>
          <button
            type="button"
            onClick={() => {
              setError(null);
            }}
            className="text-[10px] font-bold text-rose-600 hover:text-rose-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input Bar */}
      <form
        onSubmit={handleFormSubmit}
        className="p-3 border-t border-gray-100 bg-white flex items-center gap-2"
      >
        <div className="relative flex-1">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={
              isListening ? 'Listening to your voice...' : 'Ask about this step, ingredients, or doneness...'
            }
            maxLength={1000}
            disabled={isLoading}
            className="w-full text-xs py-2.5 pl-3.5 pr-8 rounded-xl border border-gray-200 bg-gray-50/50 focus:bg-white focus:outline-hidden focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 transition-all text-gray-900 placeholder:text-gray-400"
            aria-label="Ask the cooking companion a question"
          />
          {inputValue && (
            <button
              type="button"
              onClick={() => setInputValue('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs font-bold"
              aria-label="Clear input"
            >
              ×
            </button>
          )}
        </div>

        {/* Microphone Button (Optional Voice Recognition) */}
        {isSpeechRecognitionSupported && (
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            className={`p-2.5 rounded-xl border transition-all flex items-center justify-center shrink-0 ${
              isListening
                ? 'bg-rose-50 border-rose-300 text-rose-700 animate-pulse'
                : 'bg-gray-50 hover:bg-gray-100 border-gray-200 text-gray-700'
            }`}
            title={isListening ? 'Stop listening' : 'Speak your question (Voice Input)'}
            aria-label={isListening ? 'Stop recording voice' : 'Start voice input'}
          >
            {isListening ? (
              <MicOff className="w-4 h-4 text-rose-600" />
            ) : (
              <Mic className="w-4 h-4 text-gray-600" />
            )}
          </button>
        )}

        {/* Send Button */}
        <button
          type="submit"
          disabled={!inputValue.trim() || isLoading}
          className="p-2.5 rounded-xl bg-emerald-700 hover:bg-emerald-800 disabled:bg-gray-200 disabled:cursor-not-allowed text-white transition-all shrink-0 flex items-center justify-center shadow-xs"
          title="Send message"
          aria-label="Send cooking question"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
