import { useEffect, useMemo, useRef, useState } from "react";

import { postJson } from "../../lib/api";

function buildInitialMessages() {
  return [
    {
      role: "assistant",
      text: "I can help you figure out where to relocate, explain why a zone was recommended, or run what-if scenarios with a different zone, day, or time.",
    },
  ];
}

function createRecognition() {
  if (typeof window === "undefined") {
    return null;
  }
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    return null;
  }
  const recognition = new Recognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";
  return recognition;
}

function getRecognitionErrorMessage(errorCode) {
  switch (errorCode) {
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone access is blocked. Allow microphone permission in your browser settings and try again.";
    case "audio-capture":
      return "No microphone was detected. Check that your mic is connected and available to the browser.";
    case "network":
      return "Voice input hit a network problem. Try again in Chrome or Edge on a stable connection.";
    case "no-speech":
      return "I did not hear any speech. Try again and start talking right after the mic turns on.";
    case "aborted":
      return "";
    default:
      return "Voice input could not be captured. You can still type your question.";
  }
}

function pickPreferredVoice(voices) {
  if (!Array.isArray(voices) || voices.length === 0) {
    return null;
  }

  const preferredPatterns = [
    /aria/i,
    /jenny/i,
    /guy/i,
    /sara/i,
    /google us english/i,
    /microsoft.*english/i,
    /english.*natural/i,
  ];

  for (const pattern of preferredPatterns) {
    const match = voices.find((voice) => pattern.test(voice.name || ""));
    if (match) {
      return match;
    }
  }

  return voices.find((voice) => /^en[-_]/i.test(voice.lang || "")) || voices[0];
}

function RelocationCopilot({
  appContext,
  onApplyRecommendation,
  onRequestCurrentLocation,
}) {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState(buildInitialMessages);
  const [summary, setSummary] = useState("");
  const [sessionParameters, setSessionParameters] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [listening, setListening] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [recognitionStatus, setRecognitionStatus] = useState("Mic ready");
  const recognitionRef = useRef(null);
  const preferredVoiceRef = useRef(null);

  const speechSupported = typeof window !== "undefined" && "speechSynthesis" in window;
  const recognitionSupported = typeof window !== "undefined" && !!(window.SpeechRecognition || window.webkitSpeechRecognition);

  useEffect(() => {
    if (!recognitionSupported) {
      return undefined;
    }

    const recognition = createRecognition();
    recognitionRef.current = recognition;
    if (!recognition) {
      return undefined;
    }

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();
      if (transcript) {
        setInput((current) => (current ? `${current} ${transcript}`.trim() : transcript));
        setRecognitionStatus("Speech captured");
      }
    };

    recognition.onstart = () => {
      setListening(true);
      setRecognitionStatus("Listening...");
      setError("");
    };

    recognition.onerror = (event) => {
      setListening(false);
      const message = getRecognitionErrorMessage(event.error);
      setRecognitionStatus("Mic unavailable");
      if (message) {
        setError(message);
      }
    };

    recognition.onend = () => {
      setListening(false);
      setRecognitionStatus((current) => (current === "Listening..." ? "Mic ready" : current));
    };

    return () => {
      recognition.stop();
    };
  }, [recognitionSupported]);

  useEffect(() => {
    if (!speechSupported) {
      return undefined;
    }

    const loadVoices = () => {
      preferredVoiceRef.current = pickPreferredVoice(window.speechSynthesis.getVoices());
    };

    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);

    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
    };
  }, [speechSupported]);

  useEffect(() => {
    if (!speechSupported || !voiceEnabled || !isOpen || !hasInteracted || messages.length === 0) {
      return;
    }

    const latest = messages[messages.length - 1];
    if (latest.role !== "assistant") {
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(latest.text);
    utterance.voice = preferredVoiceRef.current;
    utterance.rate = 1.02;
    utterance.pitch = 1.04;
    utterance.volume = 1;
    window.speechSynthesis.speak(utterance);

    return () => {
      window.speechSynthesis.cancel();
    };
  }, [hasInteracted, isOpen, messages, speechSupported, voiceEnabled]);

  const statusText = useMemo(() => {
    if (loading) {
      return "Thinking through your relocation options...";
    }
    if (listening) {
      return "Listening...";
    }
    if (recognitionSupported) {
      return recognitionStatus;
    }
    return "Ask where to relocate, why a zone was recommended, or try a what-if scenario.";
  }, [listening, loading, recognitionStatus, recognitionSupported]);

  function resetSession() {
    setMessages(buildInitialMessages());
    setSummary("");
    setSessionParameters(null);
    setInput("");
    setError("");
    setLoading(false);
    setListening(false);
    setHasInteracted(false);
    setRecognitionStatus("Mic ready");
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (speechSupported) {
      window.speechSynthesis.cancel();
    }
  }

  function toggleOpen() {
    if (isOpen) {
      resetSession();
      setIsOpen(false);
      return;
    }
    setIsOpen(true);
  }

  function toggleListening() {
    if (!recognitionRef.current) {
      setError("Voice input is not supported in this browser.");
      return;
    }

    setError("");
    if (listening) {
      recognitionRef.current.stop();
      setListening(false);
      setRecognitionStatus("Mic ready");
      return;
    }

    setHasInteracted(true);
    setRecognitionStatus("Starting microphone...");
    if (speechSupported) {
      window.speechSynthesis.cancel();
    }
    try {
      recognitionRef.current.start();
    } catch (recognitionError) {
      setListening(false);
      setRecognitionStatus("Mic unavailable");
      setError(
        "The browser could not start voice input. If you're using Chrome or Edge, check microphone permission and try again.",
      );
    }
  }

  async function sendMessage(event) {
    event?.preventDefault();
    const message = input.trim();
    if (!message || loading) {
      return;
    }

    setError("");
    setLoading(true);
    setHasInteracted(true);
    if (speechSupported) {
      window.speechSynthesis.cancel();
    }
    if (recognitionRef.current && listening) {
      recognitionRef.current.stop();
      setListening(false);
      setRecognitionStatus("Mic ready");
    }
    setMessages((current) => [...current, { role: "user", text: message }]);
    setInput("");

    try {
      let requestContext = appContext;
      if (
        (!appContext.latitude || !appContext.longitude)
        && /(current location|my location|device location|where i am|from here|right here)/i.test(message)
        && onRequestCurrentLocation
      ) {
        requestContext = await onRequestCurrentLocation();
      }

      const response = await postJson("/api/copilot/chat", {
        message,
        summary,
        app_context: requestContext,
        session_parameters: sessionParameters,
      });

      setMessages((current) => [...current, { role: "assistant", text: response.reply }]);
      setSummary(response.summary || "");
      setSessionParameters(response.parameters || null);

      if (response.action === "function" && response.results) {
        onApplyRecommendation?.(response.results, response.parameters);
      }
    } catch (requestError) {
      setError(requestError.message || "The copilot could not respond right now.");
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: "I ran into a problem reaching the copilot service. Please try again in a moment.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel copilot-panel">
      <div className="copilot-header">
        <div>
          <p className="eyebrow">Voice Copilot</p>
          <h2>Talk To The Relocator</h2>
        </div>
        <button type="button" className="secondary-button copilot-close-button" onClick={toggleOpen}>
          {isOpen ? "Close chat" : "Open chat"}
        </button>
      </div>

      {isOpen ? (
        <>
          <p className="copilot-status">{statusText}</p>

          <div className="copilot-transcript">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`copilot-message ${message.role}`}>
                <span className="copilot-role">{message.role === "assistant" ? "Copilot" : "You"}</span>
                <p>{message.text}</p>
              </div>
            ))}
          </div>

          <form className="copilot-form" onSubmit={sendMessage}>
            <label>
              Chat or speak
              <textarea
                rows="3"
                value={input}
                onChange={(event) => {
                  if (speechSupported) {
                    window.speechSynthesis.cancel();
                  }
                  setInput(event.target.value);
                }}
                onFocus={() => {
                  if (speechSupported) {
                    window.speechSynthesis.cancel();
                  }
                }}
                placeholder="Try: Where should I relocate right now? or What if I was in East New York on Monday at 5 PM?"
              />
            </label>
            <div className="copilot-actions">
              <button type="submit" disabled={loading}>
                {loading ? "Working..." : "Send"}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={toggleListening}
                disabled={!recognitionSupported || loading}
              >
                {listening ? "Stop mic" : "Start mic"}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setVoiceEnabled((current) => !current)}
                disabled={!speechSupported}
              >
                {voiceEnabled ? "Voice replies on" : "Voice replies off"}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  onRequestCurrentLocation?.().catch(() => {});
                }}
                disabled={loading}
              >
                Use device location
              </button>
              <button type="button" className="secondary-button" onClick={resetSession}>
                Reset session
              </button>
            </div>
          </form>

          {error && <p className="helper-text">{error}</p>}
          {!recognitionSupported && (
            <p className="helper-text">Voice input is not supported in this browser, but typed chat will still work.</p>
          )}
          {recognitionSupported && (
            <p className="helper-text">
              Voice input works best in Chrome or Edge on `http://localhost`, with microphone permission allowed for this site.
            </p>
          )}
          {!speechSupported && (
            <p className="helper-text">Voice playback is not supported in this browser, so replies will stay text-only.</p>
          )}
        </>
      ) : (
        <p className="helper-text">Closing the copilot resets the session summary and conversation memory.</p>
      )}
    </section>
  );
}

export default RelocationCopilot;
