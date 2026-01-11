"""
ISAAC Core - Deterministic Dyno-Module Agent
Version 0.5.0

Platform-independent text processing engine.
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

try:
    import nltk
    from nltk.corpus import wordnet
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False

class Config:
    AGENT_NAME = "Isaac"
    USER_NAME = "User"
    MODULE_PRIORITY_BOOST = 3.0
    UNIQUE_WORD_BONUS = 1.8
    
    ACTION_VERBS = {
        "open", "close", "search", "find", "look", "get", "take", 
        "show", "display", "play", "stop", "start", "run", "execute",
        "tell", "say", "speak", "explain", "describe", "define"
    }
    
    BYPASS_WORDS = {
        "how", "who", "what", "when", "where", "why", 
        "time", "date", "help", "joke"
    }

class IsaacCore:
    def __init__(self, brain_dir, agent_name=None, user_name=None):
        self.brain_dir = brain_dir
        self.name = agent_name or Config.AGENT_NAME
        self.username = user_name or Config.USER_NAME
        
        self.core_knowledge = []
        self.module_bridge = {}
        self.loaded_modules = {}
        self.recent_command_ids = []
        
        self.global_data_file = os.path.join(brain_dir, "basedata.json")
        self.bridge_data_file = os.path.join(brain_dir, "bridgedata.json")
        
        if not os.path.exists(brain_dir):
            os.makedirs(brain_dir)
        
        self.load_core_knowledge()
        self.load_bridge_data()
    
    def load_core_knowledge(self):
        if not os.path.exists(self.global_data_file):
            raise FileNotFoundError(f"Base knowledge file not found: {self.global_data_file}")
        
        try:
            with open(self.global_data_file, 'r', encoding='utf-8') as f:
                self.core_knowledge = json.load(f)
        except Exception as e:
            raise Exception(f"Error loading core knowledge: {e}")
    
    def load_bridge_data(self):
        if not os.path.exists(self.bridge_data_file):
            return
        
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
        words = re.findall(r'\b\w+\b', text.lower())
        
        action_verb = None
        for word in words:
            if word in Config.ACTION_VERBS:
                action_verb = word
                break
        
        meaningful_words = [w for w in words if len(w) > 1]
        
        return meaningful_words, action_verb
    
    def stem(self, word):
        if len(word) <= 3:
            return word
        
        for suffix in ['ing', 'ly', 'ed', 'es', 's', 'er', 'est']:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        
        return word
    
    def get_synonyms(self, word):
        """Get synonyms for a word using WordNet"""
        if not HAS_NLTK:
            return []
        
        synonyms = []
        for synset in wordnet.synsets(word):
            for lemma in synset.lemmas():
                synonym = lemma.name().lower().replace('_', ' ')
                if synonym != word:
                    synonyms.append(synonym)
        
        return synonyms
    
    def extract_subject(self, user_tokens, matched_tokens):
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
        entry_tokens = entry.get("tokens", [])
        if isinstance(entry_tokens, str):
            entry_tokens = [entry_tokens]
        
        match_count = 0
        matched_tokens = []
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
                    match_count += 1
                    matched_tokens.append(token)
                    
                    if word_usage_map and word_usage_map.get(user_word) == 1:
                        unique_bonus = Config.UNIQUE_WORD_BONUS
                    break
        
        if match_count == 0:
            return 0, []
        
        priority = entry.get("val", 1.0)
        module_boost = Config.MODULE_PRIORITY_BOOST if is_module else 1.0
        
        final_score = match_count * priority * module_boost * (1.0 + verb_bonus) * unique_bonus
        
        return final_score, matched_tokens
    
    def find_synonym_matches(self, word, all_valid_tokens):
        """Find token matches using synonyms"""
        synonyms = self.get_synonyms(word)
        
        for synonym in synonyms:
            synonym_stem = self.stem(synonym)
            for valid_token in all_valid_tokens:
                if synonym_stem == self.stem(valid_token):
                    return valid_token
        
        # Fallback to fuzzy string matching
        matches = difflib.get_close_matches(word, all_valid_tokens, n=1, cutoff=0.75)
        return matches[0] if matches else None
    
    def process(self, text):
        user_tokens, action_verb = self.tokenize(text)
        text_lowercase = text.lower()
        
        if not user_tokens:
            return f"I'm sorry {self.username}, I didn't catch that."
        
        # Build knowledge pool from core + dynamic modules
        knowledge_pool = []
        
        for entry in self.core_knowledge:
            knowledge_pool.append((entry, False))
        
        loaded_module_names = set()
        for keyword, module_file in self.module_bridge.items():
            if keyword in text_lowercase:
                module_data = self.load_module(module_file)
                if module_data and module_file not in loaded_module_names:
                    loaded_module_names.add(module_file)
                    for entry in module_data:
                        knowledge_pool.append((entry, True))
        
        # Build word usage map for unique word detection
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
        scored_results = []
        
        for entry, is_module in knowledge_pool:
            score, matched_tokens = self.score_entry(
                user_tokens, entry, is_module, action_verb, word_usage_map
            )
            
            if score > 0:
                scored_results.append({
                    'score': score,
                    'entry': entry,
                    'matched_tokens': matched_tokens,
                    'is_module': is_module
                })
        
        # If no direct matches, try synonym expansion
        if not scored_results:
            all_valid_tokens = set()
            for entry, _ in knowledge_pool:
                tokens = entry.get("tokens", [])
                if isinstance(tokens, str):
                    all_valid_tokens.add(tokens.lower())
                else:
                    for t in tokens:
                        all_valid_tokens.add(t.lower())
            
            # Check each unmatched word for synonyms
            for word in user_tokens:
                synonym_match = self.find_synonym_matches(word, all_valid_tokens)
                if synonym_match:
                    corrected_text = text.lower().replace(word, synonym_match)
                    return self.process(corrected_text)
            
            return "I'm not sure I understand. Could you rephrase that?"
        
        # Pick best match (avoid recent repeats)
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        
        best_result = scored_results[0]
        
        if len(scored_results) > 1:
            for candidate in scored_results:
                entry_id = str(candidate['entry'])
                
                if entry_id not in self.recent_command_ids:
                    best_result = candidate
                    break
        
        entry_id = str(best_result['entry'])
        self.recent_command_ids.append(entry_id)
        if len(self.recent_command_ids) > 5:
            self.recent_command_ids.pop(0)
        
        # Extract subject and format response
        subject = self.extract_subject(user_tokens, best_result['matched_tokens'])
        
        response = best_result['entry'].get("resp", "I'm not sure how to respond.")
        response = response.replace("{subject}", subject)
        response = response.replace("{name}", self.name)
        response = response.replace("{username}", self.username)
        
        # Execute command if present
        cmd = best_result['entry'].get("cmd")
        if cmd:
            return self.execute_command(response, cmd, subject)
        
        return response
    
    def execute_command(self, text, cmd, subject):
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

if __name__ == "__main__":
    import sys
    
    brain_dir = os.path.join(os.path.dirname(__file__), "braindata")
    isaac = IsaacCore(brain_dir)
    
    stats = isaac.get_stats()
    print(f"ISAAC Core v0.5.0")
    print(f"Core Knowledge: {stats['core_knowledge_count']} entries")
    print(f"Available Modules: {stats['available_modules']}")
    print(f"Loaded Modules: {stats['loaded_modules']}")
    print("\nType 'exit' to quit.\n")
    
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