/** Speech-to-text using Web Speech Recognition API. */

type RecognitionCallback = (transcript: string) => void;
type ErrorCallback = (error: string) => void;

let recognition: any = null;

if ('webkitSpeechRecognition' in window) {
  const SpeechRecognition = (window as any).webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
}

export function setRecognitionLanguage(lang: 'english' | 'hebrew') {
  if (recognition) {
    recognition.lang = lang === 'hebrew' ? 'he-IL' : 'en-US';
  }
}

export function startRecognition(
  onTranscript: RecognitionCallback,
  onError?: ErrorCallback
): () => void {
  if (!recognition) {
    if (onError) {
      onError('Speech recognition not supported. Please use text input instead.');
    }
    return () => {}; // No-op stop function
  }

  let finalTranscript = '';

  recognition.onresult = (event: any) => {
    let interimTranscript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript + ' ';
      } else {
        interimTranscript += transcript;
      }
    }
    onTranscript(finalTranscript + interimTranscript);
  };

  recognition.onerror = (event: any) => {
    if (onError) {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        onError('Microphone access is blocked. Please allow mic permission for this site and refresh.');
        return;
      }
      onError(`Recognition error: ${event.error}`);
    }
  };

  recognition.onend = () => {
    // Restart if needed
    // recognition.start();
  };

  const start = () => {
    try {
      recognition.start();
    } catch (err: any) {
      if (onError) {
        onError(`Recognition error: ${err?.message || 'Unable to start recognition'}`);
      }
    }
  };

  if (navigator.mediaDevices?.getUserMedia) {
    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        stream.getTracks().forEach((track) => track.stop());
        start();
      })
      .catch((err) => {
        if (onError) {
          const reason =
            err?.name === 'NotAllowedError' || err?.name === 'SecurityError'
              ? 'Microphone access is blocked. Please allow mic permission for this site and refresh.'
              : `Microphone error: ${err?.message || 'Unable to access microphone'}`;
          onError(reason);
        }
      });
  } else {
    start();
  }

  return () => {
    if (recognition) {
      recognition.stop();
    }
  };
}

export function stopRecognition(): void {
  if (recognition) {
    recognition.stop();
  }
}

export function isSupported(): boolean {
  return recognition !== null;
}

export async function requestMicPermission(): Promise<'granted' | 'denied' | 'prompt' | 'unknown'> {
  if (!navigator.mediaDevices?.getUserMedia) {
    return 'unknown';
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
    return 'granted';
  } catch (err: any) {
    if (err?.name === 'NotAllowedError' || err?.name === 'SecurityError') {
      return 'denied';
    }
    if (err?.name === 'NotFoundError') {
      return 'denied';
    }
    return 'unknown';
  }
}
