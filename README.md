```
8888888 .d8888b.        d8888        d8888  .d8888b. 
  888  d88P  Y88b      d88888       d88888 d88P  Y88b
  888  Y88b.          d88P888      d88P888 888    888
  888   "Y888b.      d88P 888     d88P 888 888       
  888      "Y88b.   d88P  888    d88P  888 888       
  888        "888  d88P   888   d88P   888 888    888
  888  Y88b  d88P d8888888888  d8888888888 Y88b  d88P
8888888 "Y8888P" d88P     888 d88P     888  "Y8888P" 
```
# **ISAAC: Deterministic Dyno-Module Agent**
### **Version 0.5.0**

<<<<<<< HEAD
A scalable, non-generative intent engine designed for local-first automation. Unlike LLMs, ISAAC utilizes a deterministic token-matching system and a dynamic knowledge-parsing system to provide predictable, low-latency execution.

* **Dyno-Modules**: Hot-swappable JSON knowledge shards that can be prioritized in real-time. 
* **Lexical Expansion**: Built-in support for WordNet synonyms and fuzzy string matching for natural interaction.
* **Contextual Weighting**: Adaptive scoring multipliers based on active module detection.
* **Zero-Cloud Privacy**: All processing (excluding edge-TTS/STT) happens on your local hardware.
=======
ISAAC is a scalable, non-generative intent engine designed for local-first automation. Unlike traditional LLMs, ISAAC utilizes a **deterministic token-matching system** & dynamic knowledge-parsing system to provide predictable, low-latency execution with zero-cloud privacy.

## **Core Features**
* **Dyno-Modules**: Hot-swappable JSON knowledge shards triggered by specific keywords.
* **Action-Verb Detection**: Uses ZORK-style parsing (e.g., *open, find, tell*) to prioritize specific intents.
* **Weighted Scoring**: A scoring algorithm that favors unique matches and active modules.
* **Lexical Fallback**: Integrated support for **NLTK WordNet** synonyms and **Difflib** fuzzy matching.
* **Edge-TTS**: High-quality neural voice output (en-US-AndrewNeural) with local playback.

---
>>>>>>> parent of 1543d38 (Revise README for overhauled system.)

## **The Scoring Engine**
ISAAC calculates the "Best Match" using a multi-pass scoring algorithm. It doesn't just look for words; it calculates relevance based on the following formula:

<<<<<<< HEAD
1. **Lexical Tokenization**: Raw speech is cleaned of "stop words" and passed through a stemming algorithm to isolate root meanings.  
2. **Context Detection**: If a dynamic module name is mentioned, ISAAC applies a multiplier to all intents within that specific shard.
3. **Lexical Fallback**: If an exact match fails, the engine re-routes the query using fuzzy matching or WordNet Synonyms to find similar words.  
4. **Command Execution**: Upon intent confirmation, ISAAC executes the associated py: (Python) or url: (Web) payload and finalizes the output.

## **Project Structure**
```
.  
├── isaac\_v4\_2.py          \# Primary Deterministic Engine  
├── README.md              \# Documentation  
└── braindata/             \# Knowledge Directory  
    ├── basedata.json      \# Core System Intents  
    └── \*.json             \# Dynamic User Modules
```

## **Creating Data Modules**

Scaling ISAAC is as simple as adding a new .json file to the braindata/ folder.  
```
  {  
    "uid": "search\_query\_01",  
    "cat": "web\_search",  
    "tokens": \["find", "search", "lookup"\],  
    "val": 1.0,  
    "resp": "Searching for {subject}...",  
    "cmd": "url:\[https://www.google.com/search?q=\](https://www.google.com/search?q=){subject}" (Optional)
  }  
```

### **Command Syntax Reference**

| Prefix | Description | Example |
| :---- | :---- | :---- |
| py: | Executes local Python logic | py:datetime.now().hour |
| url: | Opens system browser | url:https://github.com |
| {subject} | Captures non-token words | Searching for {subject} |
| {username} | Current user name | Hello, {username} |
=======
$$Score = Matches \times Priority \times ModuleBoost \times (1.0 + VerbBonus) \times UniqueBonus$$

### **Scoring Multipliers**
| Multiplier | Value | Description |
| :--- | :--- | :--- |
| **Module Priority** | **3.0x** | Applied if the intent is found within a dynamically loaded module. |
| **Unique Word Bonus**| **1.8x** | Applied if a user's word uniquely identifies only one specific intent. |
| **Verb Bonus** | **+0.5** | Applied if the user's sentence matches a recognized Action Verb. |
| **Fuzzy Threshold** | **0.75** | The minimum similarity required for `difflib` to suggest a correction. |

---

## **Project Structure**
The engine relies on the `braindata/` directory to function. The **Bridge** file acts as the router for all dynamic modules.

```text
.  
├── main.py                # Primary Assistant Engine
├── README.md              # Documentation  
└── braindata/             # Knowledge Directory  
    ├── basedata.json      # Core System Intents (Static)
    ├── bridgedata.json    # Module Mappings (Keywords -> Files)
    └── *.json             # Dynamic User Modules (e.g., csharp_module.json)
```
---
## **The Bridge System**
To maintain low latency, ISAAC only loads modules when relevant keywords are detected in the user's input. These relationships are defined in `bridgedata.json`:

```json
[
  {
    "keywords": ["csharp", "coding", "programming"],
    "module": "csharp_module.json"
  }
]
```
>>>>>>> parent of 1543d38 (Revise README for overhauled system.)
