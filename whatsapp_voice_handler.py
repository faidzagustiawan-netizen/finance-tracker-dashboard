#!/usr/bin/env python3
"""
WhatsApp Voice Message Handler
Handles incoming voice messages, transcribes with Faster-Whisper, 
and processes as finance transactions
"""

import os
import requests
from audio_processor import AudioProcessor
from command_handler import FinanceCommandHandler

class WhatsAppVoiceHandler:
    def __init__(self, db_path="finance.db"):
        self.audio_processor = AudioProcessor(model_size="base")
        self.command_handler = FinanceCommandHandler(db_path)
        self.temp_audio_dir = "/tmp/whatsapp_audio"
        os.makedirs(self.temp_audio_dir, exist_ok=True)
    
    def handle_voice_message(self, media_url, media_id):
        """
        Handle incoming WhatsApp voice message
        1. Download audio from WhatsApp
        2. Transcribe dengan Faster-Whisper (Indonesian)
        3. Parse & process as transaction
        """
        try:
            print(f"🎙️ Processing voice message: {media_id}")
            
            # Download audio
            audio_path = self._download_audio(media_url, media_id)
            if not audio_path:
                return {"status": "error", "message": "Gagal download audio"}
            
            # Transcribe
            transcribed_text = self.audio_processor.process_audio_file(audio_path)
            if not transcribed_text:
                return {"status": "error", "message": "Gagal transcribe audio"}
            
            print(f"📝 Transcribed: {transcribed_text}")
            
            # Process as transaction
            result = self.command_handler.handle_message(transcribed_text, force=False)
            
            # Cleanup
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                "status": "success",
                "transcribed_text": transcribed_text,
                "processing_result": result
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _download_audio(self, media_url, media_id):
        """Download audio file from WhatsApp"""
        try:
            audio_path = f"{self.temp_audio_dir}/{media_id}.ogg"
            
            response = requests.get(media_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        media_url = sys.argv[1]
        media_id = sys.argv[2]
        
        handler = WhatsAppVoiceHandler()
        result = handler.handle_voice_message(media_url, media_id)
        
        print(f"\n📊 Result:")
        print(f"  Transcribed: {result.get('transcribed_text')}")
        print(f"  Processing: {result.get('processing_result')}")
    else:
        print("Usage: python3 whatsapp_voice_handler.py <media_url> <media_id>")
