"""
ISAAC Voice Interpreter
Version 0.5.0 - Voice Interface Example

Voice-activated interface for ISAAC Core.
Platform-specific: Requires Windows for winsound module.
"""

import asyncio
import edge_tts
import os
import time
import glob
import sys
import warnings

# Windows-specific imports
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False
    print("Warning: winsound not available (Windows only). Beeps disabled.")

import speech_recognition as sr

# Suppress pygame welcome message
warnings.filterwarnings("ignore", category=UserWarning, module='pygame.pkgdata')
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame

# Import ISAAC Core
from isaac_core import IsaacCore

# ============================================================================
# CONFIGURATION
# ============================================================================
class VoiceConfig:
    """Voice interface configuration"""
    WAKE_WORDS = ["computer", "isaac"]
    
    # TTS Voice
    TTS_VOICE = "en-US-AndrewNeural"
    
    # Speech recognition settings
    ENERGY_THRESHOLD = 300
    PAUSE_THRESHOLD = 1.0
    PHRASE_THRESHOLD = 0.2
    NON_SPEAKING_DURATION = 0.5
    
    # Timeout settings
    AMBIENT_CALIBRATION = 1.5
    WAKE_WORD_TIME_LIMIT = 10
    COMMAND_TIMEOUT = 8
    COMMAND_TIME_LIMIT = 15
    
    # Audio
    BEEP_FREQUENCY = 600
    BEEP_DURATION = 100

# ============================================================================
# SPEECH SYSTEM
# ============================================================================
class SpeechSystem:
    """Handles text-to-speech and audio playback"""
    
    def __init__(self, base_dir):
        self.base_dir = base_dir
        pygame.mixer.init()
    
    async def speak(self, text):
        """Convert text to speech and play it"""
        if not text.strip():
            return
        
        filename = os.path.join(self.base_dir, f"speech_{int(time.time() * 1000)}.mp3")
        
        try:
            await edge_tts.Communicate(text, VoiceConfig.TTS_VOICE).save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            pygame.mixer.music.unload()
            await asyncio.sleep(0.2)
            
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            print(f"Speech error: {e}")
    
    def cleanup(self):
        """Remove temporary speech files"""
        for f in glob.glob(os.path.join(self.base_dir, "speech_*.mp3")):
            try:
                os.remove(f)
            except:
                pass
    
    def shutdown(self):
        """Clean shutdown"""
        pygame.mixer.quit()

# ============================================================================
# VOICE RECOGNIZER
# ============================================================================
class VoiceRecognizer:
    """Handles voice input and wake word detection"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Configure recognizer
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = VoiceConfig.ENERGY_THRESHOLD
        self.recognizer.pause_threshold = VoiceConfig.PAUSE_THRESHOLD
        self.recognizer.phrase_threshold = VoiceConfig.PHRASE_THRESHOLD
        self.recognizer.non_speaking_duration = VoiceConfig.NON_SPEAKING_DURATION
    
    def calibrate(self, source):
        """Calibrate for ambient noise"""
        self.recognizer.adjust_for_ambient_noise(
            source, 
            duration=VoiceConfig.AMBIENT_CALIBRATION
        )
    
    def listen_for_wake_word(self, source):
        """Listen for wake word"""
        audio = self.recognizer.listen(
            source, 
            timeout=None, 
            phrase_time_limit=VoiceConfig.WAKE_WORD_TIME_LIMIT
        )
        text = self.recognizer.recognize_google(audio).lower()
        
        return any(wake in text for wake in VoiceConfig.WAKE_WORDS)
    
    def listen_for_command(self, source):
        """Listen for command after wake word detected"""
        audio = self.recognizer.listen(
            source,
            timeout=VoiceConfig.COMMAND_TIMEOUT,
            phrase_time_limit=VoiceConfig.COMMAND_TIME_LIMIT
        )
        return self.recognizer.recognize_google(audio)

# ============================================================================
# UI BANNER
# ============================================================================
def print_banner(stats):
    """Display ASCII art banner and system status"""
    module_list = ', '.join(stats['module_names']) if stats['module_names'] else 'None'
    
    banner = f"""

8888888 .d8888b.        d8888        d8888  .d8888b. 
  888  d88P  Y88b      d88888       d88888 d88P  Y88b
  888  Y88b.          d88P888      d88P888 888    888
  888   "Y888b.      d88P 888     d88P 888 888       
  888      "Y88b.   d88P  888    d88P  888 888       
  888        "888  d88P   888   d88P   888 888    888
  888  Y88b  d88P d8888888888  d8888888888 Y88b  d88P
8888888 "Y8888P" d88P     888 d88P     888  "Y8888P" 

    * Text-To-Speech Voice Interpreter

    Core Knowledge: {stats['core_knowledge_count']} entries
    Bridge Keywords: {stats['bridge_keywords']} available
    Available Modules: {stats['available_modules']} ({module_list})
    Currently Loaded: {stats['loaded_modules']} active
    Wake Words: {', '.join(VoiceConfig.WAKE_WORDS)}
    
    Ready for voice commands...
"""
    print(banner)

# ============================================================================
# MAIN APPLICATION
# ============================================================================
async def main():
    """Main voice interpreter loop"""
    
    # Setup
    base_dir = os.path.dirname(os.path.abspath(__file__))
    brain_dir = os.path.join(base_dir, "braindata")
    
    # Initialize ISAAC Core
    isaac = IsaacCore(brain_dir)
    
    # Initialize voice systems
    speech = SpeechSystem(base_dir)
    voice = VoiceRecognizer()
    
    # Cleanup old files
    speech.cleanup()
    
    # Display banner
    stats = isaac.get_stats()
    print_banner(stats)
    
    # Startup message
    await speech.speak(f"{isaac.name} online. Core knowledge and dynamic modules ready.")
    
    print("\n[SYSTEM] Listening for wake word...")
    
    # Main loop
    while True:
        with voice.microphone as source:
            try:
                # Calibrate for ambient noise
                voice.calibrate(source)
                
                # Listen for wake word
                if voice.listen_for_wake_word(source):
                    # Play acknowledgment beep
                    if HAS_WINSOUND:
                        winsound.Beep(
                            VoiceConfig.BEEP_FREQUENCY, 
                            VoiceConfig.BEEP_DURATION
                        )
                    
                    # Listen for command
                    command_text = voice.listen_for_command(source)
                    
                    print(f"\n[USER]: {command_text}")
                    
                    # Process with ISAAC Core
                    response = isaac.process(command_text)
                    print(f"[{isaac.name.upper()}]: {response}\n")
                    
                    # Speak response
                    await speech.speak(response)
                    
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutting down ISAAC Voice Interpreter...")
        sys.exit(0)