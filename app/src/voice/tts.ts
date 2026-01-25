/** Text-to-speech with ElevenLabs (high quality) and Web Speech API fallback. */

let speechQueue: string[] = [];
let isSpeakingInternal = false;
let onSpeakingChangeCallback: ((speaking: boolean) => void) | null = null;
let preferredVoice: SpeechSynthesisVoice | null = null;
let currentAudio: HTMLAudioElement | null = null;
let currentLanguage: 'english' | 'hebrew' = 'english';

export function setTtsLanguage(lang: 'english' | 'hebrew') {
  currentLanguage = lang;
  console.log('[TTS] Language set to:', lang);
}

// ElevenLabs configuration
const ELEVENLABS_API_URL = 'https://api.elevenlabs.io/v1/text-to-speech';

// Voice IDs for different languages
// English: "Adam" - deep, natural male voice
const ELEVENLABS_VOICE_ENGLISH = 'pNInz6obpgDQGcFmaJgB';
// Hebrew: Use "Bella" - known for best multilingual/non-English support
const ELEVENLABS_VOICE_HEBREW = 'EXAVITQu4vr4xnSDxMaL';  // Bella - excellent multilingual

// Models
const ELEVENLABS_MODEL_ENGLISH = 'eleven_monolingual_v1';
const ELEVENLABS_MODEL_MULTILINGUAL = 'eleven_turbo_v2_5';  // Best for non-English languages

function getVoiceId(): string {
  return currentLanguage === 'hebrew' ? ELEVENLABS_VOICE_HEBREW : ELEVENLABS_VOICE_ENGLISH;
}

function getModelId(): string {
  return currentLanguage === 'hebrew' ? ELEVENLABS_MODEL_MULTILINGUAL : ELEVENLABS_MODEL_ENGLISH;
}

// Get API key from environment variable (set via VITE_ELEVENLABS_API_KEY in .env)
function getElevenLabsApiKey(): string | null {
  return import.meta.env.VITE_ELEVENLABS_API_KEY || null;
}

export function hasElevenLabsKey(): boolean {
  return !!getElevenLabsApiKey();
}

async function speakWithElevenLabs(text: string): Promise<boolean> {
  const apiKey = getElevenLabsApiKey();
  if (!apiKey) return false;

  const voiceId = getVoiceId();
  const modelId = getModelId();
  
  // Debug logging
  console.log('[TTS] Language:', currentLanguage);
  console.log('[TTS] Voice ID:', voiceId);
  console.log('[TTS] Model:', modelId);
  console.log('[TTS] Text to speak:', text.substring(0, 100) + '...');
  
  try {
    const response = await fetch(`${ELEVENLABS_API_URL}/${voiceId}`, {
      method: 'POST',
      headers: {
        'xi-api-key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        model_id: modelId,
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
        },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.warn('ElevenLabs API error:', response.status, errorText);
      return false;
    }

    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    
    return new Promise((resolve) => {
      currentAudio = new Audio(audioUrl);
      
      currentAudio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        currentAudio = null;
        resolve(true);
      };
      
      currentAudio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        currentAudio = null;
        resolve(false);
      };
      
      currentAudio.play().catch(() => {
        resolve(false);
      });
    });
  } catch (error) {
    console.warn('ElevenLabs TTS failed:', error);
    return false;
  }
}

// Find the most natural-sounding English voice for fallback
function findBestVoice(): SpeechSynthesisVoice | null {
  if (!('speechSynthesis' in window)) return null;
  
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;
  
  const priorityPatterns = [
    /Google US English/i,
    /Google UK English Male/i,
    /Microsoft (Guy|Ryan|Christopher|Mark|David)/i,
    /Microsoft (Aria|Jenny|Sara|Emma)/i,
    /Samantha/i,
    /Daniel/i,
    /en-US/i,
    /en-GB/i,
  ];
  
  for (const pattern of priorityPatterns) {
    const match = voices.find(v => pattern.test(v.name) && v.lang.startsWith('en'));
    if (match) return match;
  }
  
  return voices.find(v => v.lang.startsWith('en')) || voices[0] || null;
}

function initVoice() {
  preferredVoice = findBestVoice();
  if (preferredVoice) {
    console.log('Fallback TTS voice:', preferredVoice.name);
  }
  // Log all available voices for debugging
  const voices = window.speechSynthesis.getVoices();
  console.log('[TTS] Voices loaded:', voices.length);
  const hebrewVoices = voices.filter(v => v.lang.startsWith('he') || v.lang.includes('IL'));
  if (hebrewVoices.length > 0) {
    console.log('[TTS] Hebrew voices available:', hebrewVoices.map(v => `${v.name} (${v.lang})`).join(', '));
  } else {
    console.log('[TTS] No Hebrew voices found in system');
  }
}

// Ensure voices are loaded before speaking
async function ensureVoicesLoaded(): Promise<SpeechSynthesisVoice[]> {
  return new Promise((resolve) => {
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
      resolve(voices);
      return;
    }
    // Wait for voices to load
    const checkVoices = () => {
      const v = window.speechSynthesis.getVoices();
      if (v.length > 0) {
        resolve(v);
      } else {
        setTimeout(checkVoices, 100);
      }
    };
    checkVoices();
  });
}

// Google Translate TTS fallback for languages without native voices
async function speakWithGoogleTTS(text: string, lang: string): Promise<boolean> {
  try {
    // Google Translate TTS has a character limit, split if needed
    const maxChars = 200;
    const chunks: string[] = [];
    let remaining = text;
    
    while (remaining.length > 0) {
      if (remaining.length <= maxChars) {
        chunks.push(remaining);
        break;
      }
      // Find a good break point
      let breakPoint = remaining.lastIndexOf(' ', maxChars);
      if (breakPoint === -1) breakPoint = maxChars;
      chunks.push(remaining.substring(0, breakPoint));
      remaining = remaining.substring(breakPoint).trim();
    }
    
    for (const chunk of chunks) {
      const encodedText = encodeURIComponent(chunk);
      // Use our backend proxy to avoid CORB/CORS issues
      const url = `/api/tts/speak?text=${encodedText}&lang=${lang}`;
      
      console.log('[TTS] Using Backend Proxy TTS for:', lang);
      
      await new Promise<void>((resolve, reject) => {
        const audio = new Audio(url);
        currentAudio = audio;
        audio.onended = () => {
          currentAudio = null;
          resolve();
        };
        audio.onerror = (e) => {
          console.error('[TTS] Proxy TTS error:', e);
          currentAudio = null;
          reject(e);
        };
        // Need user interaction first usually, but in interview context user already clicked buttons
        audio.play().catch(reject);
      });
    }
    return true;
  } catch (error) {
    console.warn('[TTS] Proxy TTS failed:', error);
    return false;
  }
}

if ('speechSynthesis' in window) {
  if (window.speechSynthesis.getVoices().length > 0) {
    initVoice();
  }
  window.speechSynthesis.onvoiceschanged = initVoice;
}

function notifySpeakingChange(speaking: boolean) {
  isSpeakingInternal = speaking;
  if (onSpeakingChangeCallback) {
    onSpeakingChangeCallback(speaking);
  }
}

async function processQueue() {
  if (isSpeakingInternal || speechQueue.length === 0) {
    if (speechQueue.length === 0 && !isSpeakingInternal) {
      notifySpeakingChange(false);
    }
    return;
  }

  const text = speechQueue.shift();
  if (!text) return;

  notifySpeakingChange(true);

  // For Hebrew, use browser TTS directly (ElevenLabs doesn't support Hebrew well)
  // For English, try ElevenLabs first (high quality voices)
  if (currentLanguage !== 'hebrew' && hasElevenLabsKey()) {
    const success = await speakWithElevenLabs(text);
    if (success) {
      isSpeakingInternal = false;
      setTimeout(() => {
        processQueue();
      }, 300);
      return;
    }
    // Fall through to Web Speech API if ElevenLabs fails
    console.log('ElevenLabs failed, falling back to browser TTS');
  }

  // Use Web Speech API (works great for Hebrew on Windows)
  if ('speechSynthesis' in window) {
    // Cancel any pending speech first
    window.speechSynthesis.cancel();
    
    // Ensure voices are loaded
    const voices = await ensureVoicesLoaded();
    console.log('[TTS] Voices ready:', voices.length, 'Language:', currentLanguage);
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Use the best available voice for the language
    if (currentLanguage === 'hebrew') {
       utterance.lang = 'he-IL';
       // Find Hebrew voice - try multiple patterns
       const heVoice = voices.find(v => v.lang.startsWith('he')) || 
                       voices.find(v => v.lang.includes('IL')) ||
                       voices.find(v => v.name.toLowerCase().includes('hebrew'));
       if (heVoice) {
         utterance.voice = heVoice;
         console.log('[TTS] Using Hebrew voice:', heVoice.name, heVoice.lang);
       } else {
         // No Hebrew voice installed - use Google Translate TTS
         console.log('[TTS] No Hebrew voice found, using Google Translate TTS');
         const success = await speakWithGoogleTTS(text, 'he');
         isSpeakingInternal = false;
         setTimeout(() => {
           processQueue();
         }, 300);
         return;
       }
    } else {
       if (preferredVoice) {
         utterance.voice = preferredVoice;
       }
       utterance.lang = 'en-US';
    }
    
    console.log('[TTS] Speaking text:', text.substring(0, 50) + '...');
    
    utterance.rate = 0.95;  // Slightly slower for more natural pacing
    utterance.pitch = 1.0;
    
    // Chrome bug workaround: speech synthesis can pause indefinitely
    // Resume it periodically
    const resumeInterval = setInterval(() => {
      if (window.speechSynthesis.paused) {
        console.log('[TTS] Resuming paused speech');
        window.speechSynthesis.resume();
      }
    }, 1000);
    
    utterance.onstart = () => {
      console.log('[TTS] Speech started');
    };
    
    utterance.onend = () => {
      console.log('[TTS] Speech ended');
      clearInterval(resumeInterval);
      isSpeakingInternal = false;
      setTimeout(() => {
        processQueue();
      }, 300);
    };

    utterance.onerror = (event) => {
      console.error('[TTS] Speech error:', event.error);
      clearInterval(resumeInterval);
      isSpeakingInternal = false;
      processQueue();
    };

    try {
      // Ensure we're not paused
      window.speechSynthesis.resume();
      window.speechSynthesis.speak(utterance);
      console.log('[TTS] speak() called, pending:', window.speechSynthesis.pending, 'speaking:', window.speechSynthesis.speaking);
    } catch (e) {
      console.error('[TTS] Error calling speak:', e);
      clearInterval(resumeInterval);
      isSpeakingInternal = false;
      processQueue();
    }
  } else {
    console.warn('Speech synthesis not supported');
    isSpeakingInternal = false;
    processQueue();
  }
}

export function speak(text: string): void {
  if (!text || text.trim() === '') return;
  speechQueue.push(text);
  processQueue();
}

export function speakSequential(texts: string[]): void {
  if (texts.length === 0) return;
  speechQueue.push(...texts);
  processQueue();
}

export function stopSpeaking(): void {
  // Stop ElevenLabs audio if playing
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  // Stop Web Speech API
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  speechQueue = [];
  isSpeakingInternal = false;
  notifySpeakingChange(false);
}

export function onSpeakingChange(callback: (speaking: boolean) => void): () => void {
  onSpeakingChangeCallback = callback;
  return () => {
    onSpeakingChangeCallback = null;
  };
}

export function isSpeaking(): boolean {
  return isSpeakingInternal || speechQueue.length > 0;
}

export function isSupported(): boolean {
  return 'speechSynthesis' in window;
}
