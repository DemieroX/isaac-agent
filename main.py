"""
ISAQ - Deterministic Dyno-Module Agent
Version 0.4.2
"""

import asyncio
import edge_tts
import os
import time
import random
import speech_recognition as sr
import winsound
import glob
import webbrowser
import re
import sys
import json
import warnings
import difflib
from datetime import datetime

# ============================================================================
# NLTK INTEGRATION
# ============================================================================
try:
    import nltk
    from nltk.corpus import wordnet
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================
warnings.filterwarnings("ignore", category=UserWarning, module='pygame.pkgdata')
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame

# ============================================================================
# CONFIGURATION
# ============================================================================
AGENT_NAME = "Isaac"
USER_NAME = "User"
WAKE_WORDS = ["computer", "isaac"]

# Tuning Parameters
MODULE_PRIORITY_MULTIPLIER = 1.5  # Boosts score for dynamic module matches
RECOGNITION_ACCURACY_CALIBRATION = 1.2  # Seconds to listen to room noise

BYPASS_WORDS = {"how", "who", "what", "when", "where", "why", "time", "date", "help", "joke"}
STOP_WORDS = {
    "the", "is", "at", "which", "on", "a", "an", "do", "does", "did",
    "my", "your", "to", "for", "with", "it", "of", "can",
    "please", "could", "would", "me", "i", "want", "now", "about",
    "very", "so", "like", "just", "really", "much", "some", "this",
    "that", "there", "if", "because", "right", "think", "know"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(BASE_DIR, "braindata")
GLOBAL_DATA_FILE = os.path.join(BRAIN_DIR, "basedata.json")

if not os.path.exists(BRAIN_DIR):
    os.makedirs(BRAIN_DIR)

# ============================================================================
# SIMPLE BRAIN - MODULE PRIORITY & FUZZY MATCHING
# ============================================================================
class SimpleBrain:
    def __init__(self):
        self.name = AGENT_NAME
        self.username = USER_NAME
        self.wake_words = WAKE_WORDS
        self.base_knowledge = []
        self.recent_responses = []
        self.load_knowledge()
    
    def load_knowledge(self):
        if not os.path.exists(GLOBAL_DATA_FILE):
            print(f"Warning: Base knowledge file not found at {GLOBAL_DATA_FILE}")
            return
        try:
            with open(GLOBAL_DATA_FILE, 'r', encoding='utf-8') as f:
                self.base_knowledge = json.load(f)
            # Tag base knowledge as non-priority
            for entry in self.base_knowledge:
                entry['_is_module'] = False
            print(f"Loaded {len(self.base_knowledge)} core knowledge entries")
        except Exception as e:
            print(f"Error loading knowledge: {e}")

    def get_available_modules(self):
        modules = {}
        for file in glob.glob(os.path.join(BRAIN_DIR, "*.json")):
            name = os.path.basename(file).replace(".json", "").lower()
            if name != "basedata":
                modules[name] = file
        return modules

    def load_module_data(self, module_path):
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for entry in data:
                        entry['_is_module'] = True # Tag as priority module
                    return data
                return []
        except Exception as e:
            print(f"Error loading module {module_path}: {e}")
            return []
    
    def clean_text(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in STOP_WORDS and w not in self.wake_words and len(w) > 1]
    
    def stem_word(self, word):
        if len(word) <= 3: return word
        for suffix in ['ing', 'ly', 'ed', 'es', 's', 'er']:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        return word

    def find_closest_command_word(self, user_word, knowledge_pool):
        valid_tokens = set()
        for entry in knowledge_pool:
            tokens = entry.get("tokens", [])
            if isinstance(tokens, str): valid_tokens.add(tokens.lower())
            else:
                for t in tokens: valid_tokens.add(t.lower())
        
        if HAS_NLTK:
            synsets = wordnet.synsets(user_word)
            for syn in synsets:
                for lemma in syn.lemmas():
                    name = lemma.name().lower().replace('_', ' ')
                    if name in valid_tokens: return name

        matches = difflib.get_close_matches(user_word, list(valid_tokens), n=1, cutoff=0.7)
        return matches[0] if matches else None
    
    def process_input(self, text):
        user_words = self.clean_text(text)
        if not user_words:
            return f"I'm sorry {self.username}, I didn't catch that."

        current_knowledge = self.base_knowledge.copy()
        available_modules = self.get_available_modules()
        
        # Check for module keywords in user text
        for mod_name, mod_path in available_modules.items():
            if mod_name in text.lower():
                mod_data = self.load_module_data(mod_path)
                current_knowledge.extend(mod_data)

        scored_entries = []
        for entry in current_knowledge:
            if not isinstance(entry, dict): continue
            entry_tokens = entry.get("tokens", [])
            if isinstance(entry_tokens, str): entry_tokens = [entry_tokens]
            
            matches = 0
            for user_word in user_words:
                user_stem = self.stem_word(user_word)
                for token in entry_tokens:
                    token_stem = self.stem_word(token)
                    if user_stem == token_stem:
                        matches += 1
                        break
            
            if matches > 0:
                # APPLY PRIORITY: Multiplier if the entry came from a dynamic module
                multiplier = MODULE_PRIORITY_MULTIPLIER if entry.get('_is_module') else 1.0
                score = (matches * entry.get("val", 1.0)) * multiplier
                scored_entries.append((score, matches, entry))
        
        if not scored_entries:
            for word in user_words:
                correction = self.find_closest_command_word(word, current_knowledge)
                if correction:
                    return self.process_input(text.lower().replace(word, correction))
            return "I'm not sure I understand. Could you rephrase that?"
        
        scored_entries.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_entry = scored_entries[0][2]
        
        # Avoid repeats
        if len(scored_entries) > 1:
            recent_uids = [e.get("uid") for e in self.recent_responses[-3:] if e.get("uid")]
            if best_entry.get("uid") in recent_uids:
                for _, _, entry in scored_entries[1:]:
                    if entry.get("uid") not in recent_uids:
                        best_entry = entry
                        break
        
        self.recent_responses.append(best_entry)
        if len(self.recent_responses) > 5: self.recent_responses.pop(0)
        
        response_text = best_entry.get("resp", "I'm not sure how to respond.")
        entry_tokens = best_entry.get("tokens", [])
        subject_words = [w for w in user_words if not any(self.stem_word(w) == self.stem_word(t) for t in entry_tokens)]
        subject = " ".join(subject_words) if subject_words else "that"
        
        response_text = response_text.replace("{subject}", subject).replace("{name}", self.name).replace("{username}", self.username)
        
        command = best_entry.get("cmd")
        return self.execute_command(response_text, command, subject) if command else response_text
    
    def execute_command(self, text, cmd, subject):
        if cmd.startswith("url:"):
            url = cmd.replace("url:", "").strip().replace("{subject}", subject.replace(" ", "+"))
            webbrowser.open(url)
            return f"{text} [Opening in browser]"
        if cmd.startswith("py:"):
            try:
                code = cmd.replace("py:", "").strip()
                result = eval(code, {"datetime": datetime, "subject": subject, "random": random, "time": time})
                return f"{text} {result}"
            except Exception as e: return f"{text} [Error: {e}]"
        return text

# ============================================================================
# SPEECH SYSTEM
# ============================================================================
class SpeechSystem:
    def __init__(self):
        pygame.mixer.init()
    async def speak(self, text):
        if not text.strip(): return
        filename = os.path.join(BASE_DIR, f"speech_{int(time.time() * 1000)}.mp3")
        try:
            await edge_tts.Communicate(text, "en-US-AndrewNeural").save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): await asyncio.sleep(0.1)
            pygame.mixer.music.unload()
            await asyncio.sleep(0.1)
            if os.path.exists(filename): os.remove(filename)
        except Exception as e: print(f"Speech error: {e}")
    def cleanup(self):
        for f in glob.glob(os.path.join(BASE_DIR, "speech_*.mp3")):
            try: os.remove(f)
            except: pass
    def shutdown(self): pygame.mixer.quit()

# ============================================================================
# UI BANNER
# ============================================================================
def print_banner(module_count, extra_modules):
    """Display ASCII art banner and status"""
    banner = rf"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║                 --.-- .-.   .    .--.                    ║
║                   |  (   ) / \  :    :                   ║
║                   |   `-. /___\ |    |                   ║
║                   |  (   )     \:  ( ;                   ║
║                 --'-- `-'       ``--`-                   ║
║                                                          ║
║          Deterministic Dyno-Module Agent v4.2.3          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

    Core Knowledge: {module_count} entries
    Dynamic Modules: {len(extra_modules)} detected ({', '.join(extra_modules.keys()) if extra_modules else 'None'})
    Wake Words: {', '.join(WAKE_WORDS)}
    
    Ready for voice commands...
"""
    print(banner)

# ============================================================================
# MAIN APPLICATION
# ============================================================================
async def main():
    brain = SimpleBrain()
    speech = SpeechSystem()
    recognizer = sr.Recognizer()
    
    # Enhanced Speech Tuning
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 4000 
    
    microphone = sr.Microphone()
    speech.cleanup()
    
    # Restored Banner Functionality
    print_banner(len(brain.base_knowledge), brain.get_available_modules())
    await speech.speak(f"{brain.name} online. Core knowledge and dynamic modules ready.")
    
    while True:
        with microphone as source:
            try:
                # Improved calibration
                recognizer.adjust_for_ambient_noise(source, duration=RECOGNITION_ACCURACY_CALIBRATION)
                
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=6)
                raw_text = recognizer.recognize_google(audio).lower()
                
                if any(wake in raw_text for wake in WAKE_WORDS):
                    winsound.Beep(600, 80)
                    # Listening for the command with slightly longer limits
                    command_audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
                    command_text = recognizer.recognize_google(command_audio)
                    
                    print(f"\n[USER]: {command_text}")
                    response = brain.process_input(command_text)
                    print(f"[{brain.name.upper()}]: {response}\n")
                    await speech.speak(response)
                    
            except (sr.WaitTimeoutError, sr.UnknownValueError): continue
            except Exception as e:
                print(f"Error: {e}")
                continue

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: sys.exit(0)