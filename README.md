# **ISAAC: Deterministic Dyno-Module Agent**

A scalable, non-generative intent engine designed for local-first automation. Unlike LLMs, ISAAC utilizes a deterministic token-matching system and a dynamic knowledge-parsing system to provide predictable, low-latency execution.

* **Dyno-Modules**: Hot-swappable JSON knowledge shards that can be prioritized in real-time. 
* **Lexical Expansion**: Built-in support for WordNet synonyms and fuzzy string matching for natural interaction.
* **Contextual Weighting**: Adaptive scoring multipliers based on active module detection.
* **Zero-Cloud Privacy**: All processing (excluding edge-TTS/STT) happens on your local hardware.

## **How It Works**

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