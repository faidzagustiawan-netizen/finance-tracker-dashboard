#!/usr/bin/env python3
"""
Audio Processing Module - Faster-Whisper with Indonesian Language Support
Converts audio files to text using faster-whisper (local, offline)
"""

from faster_whisper import WhisperModel
import os
import tempfile

class AudioProcessor:
    def __init__(self, model_size="base"):
        """
        Initialize Faster-Whisper model
        model_size: tiny, base, small, medium, large
        base = ~140MB, good balance for Indonesian
        """
        print(f"🔄 Loading Whisper model ({model_size})...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("✅ Model loaded")
    
    def transcribe(self, audio_path, language="id"):
        """
        Transcribe audio file to text
        language: "id" for Indonesian, "en" for English
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"🎙️ Transcribing audio ({language})...")
        
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=True,
            verbose=False
        )
        
        # Combine all segments
        text = " ".join([segment.text for segment in segments])
        
        print(f"✅ Transcribed: {text[:100]}...")
        
        return {
            "text": text,
            "language": language,
            "duration": info.duration
        }
    
    def process_audio_file(self, file_path):
        """
        Process audio file and return transcribed text
        Supports: mp3, wav, ogg, m4a, flac
        """
        try:
            result = self.transcribe(file_path, language="id")
            return result["text"]
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        processor = AudioProcessor(model_size="base")
        text = processor.process_audio_file(audio_file)
        if text:
            print(f"\n📝 Result: {text}")
    else:
        print("Usage: python3 audio_processor.py <audio_file>")
        print("Supported formats: mp3, wav, ogg, m4a, flac")
