"""
ISAAC - Deterministic Dyno-Module Agent
Version 0.5.0
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
MODULE_PRIORITY_BOOST = 3.0  # Dynamic modules get 3x priority
UNIQUE_WORD_BONUS = 1.8      # Bonus for words that uniquely match one entry
RECOGNITION_ACCURACY_CALIBRATION = 1.2

# ZORK-inspired action verbs (VERB-NOUN parsing)
ACTION_VERBS = {
    "open", "close", "search", "find", "look", "get", "take", 
    "show", "display", "play", "stop", "start", "run", "execute",
    "tell", "say", "speak", "explain", "describe", "define"
}

BYPASS_WORDS = {"how", "who", "what", "when", "where", "why", "time", "date", "help", "joke"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(BASE_DIR, "braindata")
GLOBAL_DATA_FILE = os.path.join(BRAIN_DIR, "basedata.json")
BRIDGE_DATA_FILE = os.path.join(BRAIN_DIR, "bridgedata.json")

if not os.path.exists(BRAIN_DIR):
    os.makedirs(BRAIN_DIR)

# ============================================================================
# BRAIN ENGINE
# Inspired by: Google Assistant, Alexa, and ZORK's text parser
# ============================================================================
class SystemBrain:
    """
    - Token-based matching (like ZORK)
    - Priority scoring (like Alexa)
    - Bridge-based module loading (like Google Assistant skills)
    """
    
    def __init__(self):
        self.name = AGENT_NAME
        self.username = USER_NAME
        self.wake_words = WAKE_WORDS
        
        # Knowledge storage
        self.core_knowledge = []      # Base commands
        self.module_bridge = {}       # Module keyword mappings
        self.loaded_modules = {}      # Cached module data
        
        # Anti-repetition
        self.recent_command_ids = []
        
        self.load_core_knowledge()
        self.load_bridge_data()
    
    def load_core_knowledge(self):
        """Load base knowledge from basedata.json"""
        if not os.path.exists(GLOBAL_DATA_FILE):
            print(f"Warning: Base knowledge file not found")
            return
        
        try:
            with open(GLOBAL_DATA_FILE, 'r', encoding='utf-8') as f:
                self.core_knowledge = json.load(f)
        except Exception as e:
            print(f"Error loading core knowledge: {e}")
    
    def load_bridge_data(self):
        """
        Load bridgedata.json which maps keywords to module files
        Format: [{"keywords": ["csharp", "c#"], "module": "csharp_module.json"}, ...]
        """
        if not os.path.exists(BRIDGE_DATA_FILE):
            print("No bridge data found - modules disabled")
            return
        
        try:
            with open(BRIDGE_DATA_FILE, 'r', encoding='utf-8') as f:
                bridges = json.load(f)
            
            # Track available modules
            available_modules = set()
            
            for bridge in bridges:
                keywords = bridge.get("keywords", [])
                module_file = bridge.get("module", "")
                
                if module_file:
                    # Check if module file actually exists
                    module_path = os.path.join(BRAIN_DIR, module_file)
                    if os.path.exists(module_path):
                        available_modules.add(module_file)
                    
                    for keyword in keywords:
                        self.module_bridge[keyword.lower()] = module_file
        except Exception as e:
            print(f"Error loading bridge data: {e}")
    
    def load_module(self, module_filename):
        """Load a specific module file and cache it"""
        if module_filename in self.loaded_modules:
            return self.loaded_modules[module_filename]
        
        module_path = os.path.join(BRAIN_DIR, module_filename)
        if not os.path.exists(module_path):
            return []
        
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.loaded_modules[module_filename] = data
                return data
        except Exception as e:
            print(f"Error loading module {module_filename}: {e}")
        
        return []
    
    def tokenize(self, text):
        """
        Enhanced ZORK-style tokenization with verb detection
        Returns: (tokens, action_verb)
        """
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Identify action verb (first verb found)
        action_verb = None
        for word in words:
            if word in ACTION_VERBS:
                action_verb = word
                break
        
        # Remove stop words, wake words, and single letters
        meaningful = [
            w for w in words 
            if w not in self.wake_words 
            and len(w) > 1
        ]
        
        return meaningful, action_verb
    
    def stem(self, word):
        """Simple stemming for matching variations"""
        if len(word) <= 3:
            return word
        
        for suffix in ['ing', 'ly', 'ed', 'es', 's', 'er', 'est']:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        
        return word
    
    def extract_subject(self, user_tokens, matched_tokens):
        if not matched_tokens or not user_tokens:
            return "that"
        
        # Find the position of the last matched token in user input
        last_match_index = -1
        for token in matched_tokens:
            token_stem = self.stem(token)
            for i, user_word in enumerate(user_tokens):
                if self.stem(user_word) == token_stem:
                    last_match_index = max(last_match_index, i)
        
        # Subject = words AFTER the highest-value matched token
        if last_match_index >= 0 and last_match_index < len(user_tokens) - 1:
            subject_words = user_tokens[last_match_index + 1:]
            return " ".join(subject_words)
        
        return "that"
    
    def score_entry(self, user_tokens, entry, is_module=False, action_verb=None, word_usage_map=None):
        # Scoring: Matches × priority × module_boost × verb_bonus × unique_word_bonus
        entry_tokens = entry.get("tokens", [])
        if isinstance(entry_tokens, str):
            entry_tokens = [entry_tokens]
        
        matches = 0
        matched_token_list = []
        verb_bonus = 0
        unique_bonus = 1.0
        
        if action_verb:
            for token in entry_tokens:
                if self.stem(action_verb) == self.stem(token):
                    verb_bonus = 0.5
                    break
        
        for user_word in user_tokens:
            user_stem = self.stem(user_word)
            
            for token in entry_tokens:
                token_stem = self.stem(token)
                
                if user_stem == token_stem:
                    matches += 1
                    matched_token_list.append(token)
                    
                    # Check if this word uniquely matches only this entry
                    if word_usage_map and word_usage_map.get(user_word) == 1:
                        unique_bonus = UNIQUE_WORD_BONUS
                    break
        
        if matches == 0:
            return 0, []
        
        priority = entry.get("val", 1.0)
        module_boost = MODULE_PRIORITY_BOOST if is_module else 1.0
        
        score = matches * priority * module_boost * (1.0 + verb_bonus) * unique_bonus
        
        return score, matched_token_list
    
    def fuzzy_match(self, word, valid_tokens):
        # Find close matches using difflib and NLTK synonyms

        # First: NLTK synonyms
        if HAS_NLTK:
            synsets = wordnet.synsets(word)
            for syn in synsets:
                for lemma in syn.lemmas():
                    synonym = lemma.name().lower().replace('_', ' ')
                    if synonym in valid_tokens:
                        return synonym
        
        # Fall back to fuzzy-matching
        matches = difflib.get_close_matches(word, valid_tokens, n=1, cutoff=0.75)
        return matches[0] if matches else None
    
    def process_input(self, text):
        """
        Enhanced processing with unique word detection:
        1. Tokenize and identify action verbs
        2. Load relevant dynamic modules (priority boost)
        3. Build word usage map for unique word detection
        4. Score entries (modules get 3x, unique words get 1.8x)
        5. Pick best match and format response
        """
        
        user_tokens, action_verb = self.tokenize(text)
        original_text_lower = text.lower()
        
        if not user_tokens:
            return f"I'm sorry {self.username}, I didn't catch that."
        
        # Step 2: Build knowledge pool (Core always included(static), modules prioritized(dynamic))
        knowledge_pool = []
        
        for entry in self.core_knowledge:
            knowledge_pool.append((entry, False))
        
        modules_loaded = set()
        for keyword, module_file in self.module_bridge.items():
            if keyword in original_text_lower:
                module_data = self.load_module(module_file)
                if module_data and module_file not in modules_loaded:
                    modules_loaded.add(module_file)
                    for entry in module_data:
                        knowledge_pool.append((entry, True))
        
        # Step 3: Build word usage map (Amount of entries each word matches with)
        word_usage_map = {}
        for user_word in user_tokens:
            user_stem = self.stem(user_word)
            usage_count = 0
            
            for entry, _ in knowledge_pool:
                entry_tokens = entry.get("tokens", [])
                if isinstance(entry_tokens, str):
                    entry_tokens = [entry_tokens]
                
                for token in entry_tokens:
                    if user_stem == self.stem(token):
                        usage_count += 1
                        break
            
            word_usage_map[user_word] = usage_count
        
        # Step 4: Score entries with word awareness
        scored_entries = []
        
        for entry, is_module in knowledge_pool:
            score, matched_tokens = self.score_entry(user_tokens, entry, is_module, action_verb, word_usage_map)
            
            if score > 0:
                scored_entries.append({
                    'score': score,
                    'entry': entry,
                    'matched_tokens': matched_tokens,
                    'is_module': is_module
                })
        
        # Step 5: No matches? Try fuzzy matching
        if not scored_entries:
            # Build list of all valid tokens
            all_valid_tokens = set()
            for entry, _ in knowledge_pool:
                tokens = entry.get("tokens", [])
                if isinstance(tokens, str):
                    all_valid_tokens.add(tokens.lower())
                else:
                    for t in tokens:
                        all_valid_tokens.add(t.lower())
            
            # Try to find corrections
            for word in user_tokens:
                correction = self.fuzzy_match(word, all_valid_tokens)
                if correction:
                    corrected_text = text.lower().replace(word, correction)
                    return self.process_input(corrected_text)
            
            return "I'm not sure I understand. Could you rephrase that?"
        
        # Step 6: Sort by score (highest first)
        scored_entries.sort(key=lambda x: x['score'], reverse=True)
        
        # Step 7: Pick best match (avoid recent repeats)
        best = scored_entries[0]
        
        if len(scored_entries) > 1:
            for candidate in scored_entries:
                entry_id = str(candidate['entry'])  # Use entire entry as ID
                
                if entry_id not in self.recent_command_ids:
                    best = candidate
                    break
        
        # Track this command
        entry_id = str(best['entry'])
        self.recent_command_ids.append(entry_id)
        if len(self.recent_command_ids) > 5:
            self.recent_command_ids.pop(0)
        
        # Step 8: Extract subject (AFTER matched tokens)
        subject = self.extract_subject(user_tokens, best['matched_tokens'])
        
        # Step 9: Format response
        response_text = best['entry'].get("resp", "I'm not sure how to respond.")
        response_text = response_text.replace("{subject}", subject)
        response_text = response_text.replace("{name}", self.name)
        response_text = response_text.replace("{username}", self.username)
        
        # Step 10: Execute command if present
        command = best['entry'].get("cmd")
        if command:
            return self.execute_command(response_text, command, subject)
        
        return response_text
    
    def execute_command(self, text, cmd, subject):
        """Execute URL or Python commands"""
        if not cmd:
            return text
        
        # URL commands
        if cmd.startswith("url:"):
            url = cmd.replace("url:", "").strip()
            url = url.replace("{subject}", subject.replace(" ", "+"))
            
            if "{subject}" in cmd and subject == "that":
                return "Please specify what you want me to search for."
            
            webbrowser.open(url)
            return f"{text} [Opening in browser]"
        
        # Python evaluation
        if cmd.startswith("py:"):
            try:
                code = cmd.replace("py:", "").strip()
                result = eval(code, {
                    "datetime": datetime,
                    "subject": subject,
                    "random": random,
                    "time": time
                })
                return f"{text} {result}"
            except Exception as e:
                return f"{text} [Error: {e}]"
        
        return text
    
    def get_module_stats(self):
        # Module statistic for start banner
        # Count unique module files in bridge
        available_modules = set(self.module_bridge.values())
        
        # Verify they actually exist
        existing_modules = []
        for module_file in available_modules:
            module_path = os.path.join(BRAIN_DIR, module_file)
            if os.path.exists(module_path):
                existing_modules.append(module_file)
        
        return {
            'bridge_keywords': len(self.module_bridge),
            'loaded_modules': len(self.loaded_modules),
            'available_modules': len(existing_modules),
            'module_names': existing_modules
        }

# ============================================================================
# SPEECH SYSTEM
# ============================================================================
class SpeechSystem:
    def __init__(self):
        pygame.mixer.init()
    
    async def speak(self, text):
        if not text.strip():
            return
        
        filename = os.path.join(BASE_DIR, f"speech_{int(time.time() * 1000)}.mp3")
        
        try:
            await edge_tts.Communicate(text, "en-US-AndrewNeural").save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            pygame.mixer.music.unload()
            await asyncio.sleep(0.2)  # Increased delay for better cleanup
            
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            print(f"Speech error: {e}")
    
    def cleanup(self):
        for f in glob.glob(os.path.join(BASE_DIR, "speech_*.mp3")):
            try:
                os.remove(f)
            except:
                pass
    
    def shutdown(self):
        pygame.mixer.quit()

# ============================================================================
# UI BANNER
# ============================================================================
def print_banner(core_count, module_stats):
    # Display ASCII art banner & status
    module_list = ', '.join(module_stats['module_names']) if module_stats['module_names'] else 'None'
    
    banner = f"""

8888888 .d8888b.        d8888        d8888  .d8888b. 
  888  d88P  Y88b      d88888       d88888 d88P  Y88b
  888  Y88b.          d88P888      d88P888 888    888
  888   "Y888b.      d88P 888     d88P 888 888       
  888      "Y88b.   d88P  888    d88P  888 888       
  888        "888  d88P   888   d88P   888 888    888
  888  Y88b  d88P d8888888888  d8888888888 Y88b  d88P
8888888 "Y8888P" d88P     888 d88P     888  "Y8888P" 

    * Deterministic Dyno-Module Agent v0.5.0

    Core Knowledge: {core_count} entries
    Bridge Keywords: {module_stats['bridge_keywords']} available
    Available Modules: {module_stats['available_modules']} ({module_list})
    Currently Loaded: {module_stats['loaded_modules']} active
    Wake Words: {', '.join(WAKE_WORDS)}
    
    Ready for voice commands...
"""
    print(banner)

# ============================================================================
# MAIN APPLICATION
# ============================================================================
async def main():
    brain = SystemBrain()
    speech = SpeechSystem()
    recognizer = sr.Recognizer()
    
    # Speech recognition settings
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 300  # Sensitivity
    recognizer.pause_threshold = 1.0   # Seconds of pause before processing
    recognizer.phrase_threshold = 0.2   # Audio density before considering speech
    recognizer.non_speaking_duration = 0.5  # How long to wait for pause
    
    microphone = sr.Microphone()
    speech.cleanup()
    
    # Display banner
    print_banner(len(brain.core_knowledge), brain.get_module_stats())
    await speech.speak(f"{brain.name} online. Core knowledge and dynamic modules ready.")
    
    print("\n[SYSTEM] Listening microphone...")
    
    # Main loop
    while True:
        with microphone as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=1.5)
                
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
                raw_text = recognizer.recognize_google(audio).lower()
                
                if any(wake in raw_text for wake in WAKE_WORDS):
                    winsound.Beep(600, 100)
                    
                    command_audio = recognizer.listen(
                        source, 
                        timeout=8,
                        phrase_time_limit=15
                    )
                    command_text = recognizer.recognize_google(command_audio)
                    
                    print(f"\n[USER]: {command_text}")
                    response = brain.process_input(command_text)
                    print(f"[{brain.name.upper()}]: {response}\n")
                    await speech.speak(response)
                    
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
