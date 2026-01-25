/** Text-to-speech using Web Speech API. */

let speechQueue: string[] = [];
let isSpeaking = false;

function processQueue() {
  if (isSpeaking || speechQueue.length === 0) {
    return;
  }

  const text = speechQueue.shift();
  if (!text) return;

  isSpeaking = true;

  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    
    utterance.onend = () => {
      isSpeaking = false;
      // Process next item in queue after a brief pause
      setTimeout(() => {
        processQueue();
      }, 300);
    };

    utterance.onerror = () => {
      isSpeaking = false;
      processQueue();
    };

    window.speechSynthesis.speak(utterance);
  } else {
    console.warn('Speech synthesis not supported');
    isSpeaking = false;
    processQueue();
  }
}

export function speak(text: string): void {
  if (!text || text.trim() === '') return;
  
  speechQueue.push(text);
  processQueue();
}

export function speakSequential(texts: string[]): void {
  speechQueue.push(...texts);
  processQueue();
}

export function stopSpeaking(): void {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  speechQueue = [];
  isSpeaking = false;
}
