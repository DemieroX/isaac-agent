"""
ISAAC Core - Deterministic Dyno-Module Agent
Version 0.5.0 - Core Engine

Platform-independent text processing engine for ISAAC.
Can be used standalone or integrated into other applications.
"""

import os
import re
import json
import difflib
import webbrowser
import random
import time
from datetime import datetime

# ============================================================================
# OPTIONAL NLTK SUPPORT
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
# CONFIGURATION
# ============================================================================
class Config:
    """Configuration constants for ISAAC"""
    AGENT_NAME = "Isaac"
    USER_NAME = "User"
    
    # Scoring parameters
    MODULE_PRIORITY_BOOST = 3.0
    UNIQUE_WORD_BONUS = 1.8
    
    # Action verbs for VERB-NOUN parsing
    ACTION_VERBS = {
        "open", "close", "search", "find", "look", "get", "take", 
        "show", "display", "play", "stop", "start", "run", "execute",
        "tell", "say", "speak", "explain", "describe", "define"
    }
    
    # Words that trigger parsing even for short queries
    BYPASS_WORDS = {
        "how", "who", "what", "when", "where", "why", 
        "time", "date", "help", "joke"
    }

# ============================================================================
# ISAAC CORE ENGINE
# ============================================================================
class IsaacCore:
    """
    Core text processing engine for ISAAC.
    Handles knowledge loading, text parsing, and response generation.
    
    Usage:
        isaac = IsaacCore(brain_dir="./braindata")
        response = isaac.process("what is the time")
        print(response)
    """
    
    def __init__(self, brain_dir, agent_name=None, user_name=None):
        """
        Initialize ISAAC core engine.
        
        Args:
            brain_dir: Path to directory containing knowledge files
            agent_name: Name of the agent (default: "Isaac")
            user_name: Name of the user (default: "User")
        """
        self.brain_dir = brain_dir
        self.name = agent_name or Config.AGENT_NAME
        self.username = user_name or Config.USER_NAME
        
        # Knowledge storage
        self.core_knowledge = []
        self.module_bridge = {}
        self.loaded_modules = {}
        
        # Anti-repetition tracking
        self.recent_command_ids = []
        
        # File paths
        self.global_data_file = os.path.join(brain_dir, "basedata.json")
        self.bridge_data_file = os.path.join(brain_dir, "bridgedata.json")
        
        # Ensure brain directory exists
        if not os.path.exists(brain_dir):
            os.makedirs(brain_dir)
        
        # Load knowledge
        self.load_core_knowledge()
        self.load_bridge_data()
    
    def load_core_knowledge(self):
        """Load base knowledge from basedata.json"""
        if not os.path.exists(self.global_data_file):
            raise FileNotFoundError(f"Base knowledge file not found: {self.global_data_file}")
        
        try:
            with open(self.global_data_file, 'r', encoding='utf-8') as f:
                self.core_knowledge = json.load(f)
        except Exception as e:
            raise Exception(f"Error loading core knowledge: {e}")
    
    def load_bridge_data(self):
        """Load module bridge mapping from bridgedata.json"""
        if not os.path.exists(self.bridge_data_file):
            return  # Modules are optional
        
        try:
            with open(self.bridge_data_file, 'r', encoding='utf-8') as f:
                bridges = json.load(f)
            
            for bridge in bridges:
                keywords = bridge.get("keywords", [])
                module_file = bridge.get("module", "")
                
                if module_file:
                    module_path = os.path.join(self.brain_dir, module_file)
                    if os.path.exists(module_path):
                        for keyword in keywords:
                            self.module_bridge[keyword.lower()] = module_file
        except Exception as e:
            print(f"Warning: Error loading bridge data: {e}")
    
    def load_module(self, module_filename):
        """Load and cache a knowledge module"""
        if module_filename in self.loaded_modules:
            return self.loaded_modules[module_filename]
        
        module_path = os.path.join(self.brain_dir, module_filename)
        if not os.path.exists(module_path):
            return []
        
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.loaded_modules[module_filename] = data
                return data
        except Exception as e:
            print(f"Warning: Error loading module {module_filename}: {e}")
        
        return []
    
    def tokenize(self, text):
        """
        Tokenize text and detect action verbs.
        Returns: (tokens, action_verb)
        """
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Detect action verb
        action_verb = None
        for word in words:
            if word in Config.ACTION_VERBS:
                action_verb = word
                break
        
        # Filter meaningful words (length > 1)
        meaningful = [w for w in words if len(w) > 1]
        
        return meaningful, action_verb
    
    def stem(self, word):
        """Simple word stemming"""
        if len(word) <= 3:
            return word
        
        for suffix in ['ing', 'ly', 'ed', 'es', 's', 'er', 'est']:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        
        return word
    
    def extract_subject(self, user_tokens, matched_tokens):
        """Extract subject from user input (words after matched tokens)"""
        if not matched_tokens or not user_tokens:
            return "that"
        
        last_match_index = -1
        for token in matched_tokens:
            token_stem = self.stem(token)
            for i, user_word in enumerate(user_tokens):
                if self.stem(user_word) == token_stem:
                    last_match_index = max(last_match_index, i)
        
        if last_match_index >= 0 and last_match_index < len(user_tokens) - 1:
            subject_words = user_tokens[last_match_index + 1:]
            return " ".join(subject_words)
        
        return "that"
    
    def score_entry(self, user_tokens, entry, is_module, action_verb, word_usage_map):
        """
        Score an entry based on token matches.
        Formula: matches × priority × module_boost × verb_bonus × unique_bonus
        """
        entry_tokens = entry.get("tokens", [])
        if isinstance(entry_tokens, str):
            entry_tokens = [entry_tokens]
        
        matches = 0
        matched_token_list = []
        verb_bonus = 0
        unique_bonus = 1.0
        
        # Verb matching bonus
        if action_verb:
            for token in entry_tokens:
                if self.stem(action_verb) == self.stem(token):
                    verb_bonus = 0.5
                    break
        
        # Token matching
        for user_word in user_tokens:
            user_stem = self.stem(user_word)
            
            for token in entry_tokens:
                token_stem = self.stem(token)
                
                if user_stem == token_stem:
                    matches += 1
                    matched_token_list.append(token)
                    
                    # Unique word bonus
                    if word_usage_map and word_usage_map.get(user_word) == 1:
                        unique_bonus = Config.UNIQUE_WORD_BONUS
                    break
        
        if matches == 0:
            return 0, []
        
        priority = entry.get("val", 1.0)
        module_boost = Config.MODULE_PRIORITY_BOOST if is_module else 1.0
        
        score = matches * priority * module_boost * (1.0 + verb_bonus) * unique_bonus
        
        return score, matched_token_list
    
    def fuzzy_match(self, word, valid_tokens):
        """Find close matches using NLTK synonyms and string similarity"""
        if HAS_NLTK:
            synsets = wordnet.synsets(word)
            for syn in synsets:
                for lemma in syn.lemmas():
                    synonym = lemma.name().lower().replace('_', ' ')
                    if synonym in valid_tokens:
                        return synonym
        
        matches = difflib.get_close_matches(word, valid_tokens, n=1, cutoff=0.75)
        return matches[0] if matches else None
    
    def process(self, text):
        """
        Main text processing method.
        
        Args:
            text: User input text
            
        Returns:
            Response string
        """
        user_tokens, action_verb = self.tokenize(text)
        original_text_lower = text.lower()
        
        if not user_tokens:
            return f"I'm sorry {self.username}, I didn't catch that."
        
        # Build knowledge pool
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
        
        # Build word usage map
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
        
        # Score all entries
        scored_entries = []
        
        for entry, is_module in knowledge_pool:
            score, matched_tokens = self.score_entry(
                user_tokens, entry, is_module, action_verb, word_usage_map
            )
            
            if score > 0:
                scored_entries.append({
                    'score': score,
                    'entry': entry,
                    'matched_tokens': matched_tokens,
                    'is_module': is_module
                })
        
        # Fuzzy matching fallback
        if not scored_entries:
            all_valid_tokens = set()
            for entry, _ in knowledge_pool:
                tokens = entry.get("tokens", [])
                if isinstance(tokens, str):
                    all_valid_tokens.add(tokens.lower())
                else:
                    for t in tokens:
                        all_valid_tokens.add(t.lower())
            
            for word in user_tokens:
                correction = self.fuzzy_match(word, all_valid_tokens)
                if correction:
                    corrected_text = text.lower().replace(word, correction)
                    return self.process(corrected_text)
            
            return "I'm not sure I understand. Could you rephrase that?"
        
        # Sort and pick best match
        scored_entries.sort(key=lambda x: x['score'], reverse=True)
        
        best = scored_entries[0]
        
        if len(scored_entries) > 1:
            for candidate in scored_entries:
                entry_id = str(candidate['entry'])
                
                if entry_id not in self.recent_command_ids:
                    best = candidate
                    break
        
        entry_id = str(best['entry'])
        self.recent_command_ids.append(entry_id)
        if len(self.recent_command_ids) > 5:
            self.recent_command_ids.pop(0)
        
        # Extract subject and format response
        subject = self.extract_subject(user_tokens, best['matched_tokens'])
        
        response_text = best['entry'].get("resp", "I'm not sure how to respond.")
        response_text = response_text.replace("{subject}", subject)
        response_text = response_text.replace("{name}", self.name)
        response_text = response_text.replace("{username}", self.username)
        
        # Execute command if present
        command = best['entry'].get("cmd")
        if command:
            return self.execute_command(response_text, command, subject)
        
        return response_text
    
    def execute_command(self, text, cmd, subject):
        """Execute commands (URL or Python evaluation)"""
        if not cmd:
            return text
        
        if cmd.startswith("url:"):
            url = cmd.replace("url:", "").strip()
            url = url.replace("{subject}", subject.replace(" ", "+"))
            
            if "{subject}" in cmd and subject == "that":
                return "Please specify what you want me to search for."
            
            webbrowser.open(url)
            return f"{text} [Opening in browser]"
        
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
    
    def get_stats(self):
        """Get system statistics"""
        available_modules = set(self.module_bridge.values())
        existing_modules = []
        
        for module_file in available_modules:
            module_path = os.path.join(self.brain_dir, module_file)
            if os.path.exists(module_path):
                existing_modules.append(module_file)
        
        return {
            'core_knowledge_count': len(self.core_knowledge),
            'bridge_keywords': len(self.module_bridge),
            'available_modules': len(existing_modules),
            'loaded_modules': len(self.loaded_modules),
            'module_names': existing_modules
        }

# ============================================================================
# STANDALONE USAGE EXAMPLE
# ============================================================================
if __name__ == "__main__":
    import sys
    
    # Initialize ISAAC
    brain_dir = os.path.join(os.path.dirname(__file__), "braindata")
    isaac = IsaacCore(brain_dir)
    
    # Print stats
    stats = isaac.get_stats()
    print(f"ISAAC Core v0.5.0")
    print(f"Core Knowledge: {stats['core_knowledge_count']} entries")
    print(f"Available Modules: {stats['available_modules']}")
    print(f"Loaded Modules: {stats['loaded_modules']}")
    print("\nType 'exit' to quit.\n")
    
    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n[SYSTEM: Application terminated.]")
                break
            
            if not user_input:
                continue
            
            response = isaac.process(user_input)
            print(f"Isaac: {response}\n")
            
        except KeyboardInterrupt:
            print("\n[SYSTEM: Application terminated.]")
            break
        except Exception as e:
            print(f"Error: {e}")