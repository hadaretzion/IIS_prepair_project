from fastapi import APIRouter, Response
import urllib.request
import urllib.parse
import logging

router = APIRouter(prefix="/api/tts", tags=["tts"])
logger = logging.getLogger(__name__)

@router.get("/speak")
def speak(text: str, lang: str = "en"):
    """Proxy to Google Translate TTS to avoid CORS issues in browser."""
    try:
        # Encode text
        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl={lang}&client=tw-ob"
        
        # Fake User-Agent to avoid immediate blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            audio_data = response.read()
            return Response(content=audio_data, media_type="audio/mpeg")
            
    except Exception as e:
        logger.error(f"TTS Proxy Error: {e}")
        return Response(status_code=500, content=str(e))
