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

Modular, non-generative intent engine designed for local-first automation. Unlike generative-AI models, ISAAC utilizes a deterministic token-matching system with dynamic knowledge modules, allowing for a predictable & expandable agent system.

## **Key Features**

* **Dyno-Modules**: Dynamic JSON knowledge/data modules that load on-demand when specific keywords are detected. (Specific keywords are stored in bridge data file.)
* **Lexical Expansion**: Built-in support for WordNet synonyms and fuzzy string matching for natural interaction without training data. (If a word is not found, tries synonyms to make up for it.)
* **Contextual Weighting**: Layered scoring system that considers token matches, module priority, action verbs, and word uniqueness.
* **Platform Independent Core**: The engine should works on Windows, macOS, and Linux with zero platform-specific dependencies.

## **How It Works**

### **Processing Pipeline**

1. **Tokenization & Verb Detection**: User input is cleaned of stop words and analyzed for action verbs (inspired by text adventure games like ZORK).

2. **Module Loading**: If you have specified keywords in your bridge data, ISAAC can detect it from the input & the specified knowledge module is loaded from the bridge system, with priority.

4. **Scoring Algorithm**: Each knowledge entry receives a score based on:

   ```
   score = matches × priority × module_boost × verb_bonus × unique_bonus
   
   Where:
   - matches: Number of tokens that match
   - priority: Entry's "val" field (1.0-5.0)
   - module_boost: 3.0 if from dynamic module, 1.0 if core
   - verb_bonus: +0.5 if action verb matches
   - unique_bonus: 1.8 if word uniquely matches this entry
   ```

5. **Subject Extraction**: The system intelligently extracts the subject by taking all words **after** the last matched command token.
   - "open YouTube Brackeys" → subject = "Brackeys"
   - "search for python tutorials" → subject = "tutorials"

6. **Command Execution**: Upon intent confirmation, ISAAC executes the associated `py:` (Python eval) or `url:` (web browser) command.

## **Project Structure**

```
.
├── isaac_core.py           # Core engine (platform-independent)
├── voice_interpreter.py    # Voice interface example (Windows-focused)
├── requirements.txt        # Dependencies
├── README.md              # Documentation
└── braindata/             # Knowledge directory
    ├── basedata.json      # Core system intents (always loaded)
    ├── bridgedata.json    # Module keyword mappings
    └── *.json             # Dynamic knowledge modules
```

### **Architecture**

**isaac_core.py** - The base processing engine. Zero platform-specific code, can be imported to any application with `import`

**voice_interpreter.py** - Example implementation using speech recognition and TTS. Platform-specific audio libraries. (Download all libraries with `pip install`)

**bridgedata.json** - Maps keywords to module files:
```json
[
  {
    "keywords": ["csharp", "c#", "c sharp", "dotnet"],
    "module": "csharp_module.json"
  }
]
```

This allows multiple trigger words to load the same module, and modules only load when needed.

## **Installation**

Single dependency. Works on any platform:
(When nltk fails, falls back to fuzzy matching.)

```bash
pip install nltk
python isaac_core.py
```

## **Creating Knowledge Modules**

### **Basic Entry Structure**

```json
{
  "tokens": ["search", "find", "google"],
  "val": 3.0,
  "resp": "Searching for {subject}",
  "cmd": "url:https://www.google.com/search?q={subject}"
}
```

### **Field Reference**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tokens` | list/string | Yes | Words that trigger this entry. Stemming applied automatically. |
| `val` | float | Yes | Priority multiplier (1.0-5.0). Higher = more priority when matched. |
| `resp` | string | Yes | Response text. Supports `{subject}`, `{name}`, `{username}` placeholders. |
| `cmd` | string | No | Command to execute. Prefix with `py:` or `url:`. |

### **Command Syntax**

| Prefix | Description | Example |
|--------|-------------|---------|
| `py:` | Executes Python code | `py:datetime.now().strftime('%I:%M %p')` |
| `url:` | Opens system browser | `url:https://github.com/{subject}` |
| `{subject}` | Extracted query subject | Words after matched tokens |
| `{username}` | Current user name | Personalization |
| `{name}` | Agent name | Self-reference |

### **Example: Time Query**

```json
{
  "tokens": ["time"],
  "val": 5.0,
  "resp": "The current time is",
  "cmd": "py:datetime.now().strftime('%I:%M %p')"
}
```

Input: "what's the time"
- Matches: "time" token
- Score: `1 match × 5.0 priority = 5.0`
- Executes: Python datetime code
- Output: "The current time is 02:34 PM"

### **Example: YouTube Search**

```json
{
  "tokens": ["youtube"],
  "val": 4.5,
  "resp": "Opening YouTube for {subject}",
  "cmd": "url:https://www.youtube.com/results?search_query={subject}"
}
```

Input: "open YouTube Brackeys"
- Matches: "youtube" token
- Subject: "Brackeys" (word after matched token)
- Opens: `youtube.com/results?search_query=Brackeys`

## **Creating Dynamic Modules**

Modules are specialized knowledge files that load on-demand when their keywords are mentioned.

### **Step 1: Create Custom Module File**

Create `braindata/python_module.json`:

```json
[
  {
    "tokens": ["list", "python"],
    "val": 3.0,
    "resp": "Python lists: my_list = [1, 2, 3]. Access with my_list[0]. Methods: append(), remove(), len()"
  },
  {
    "tokens": ["dictionary", "dict", "python"],
    "val": 3.0,
    "resp": "Python dicts: my_dict = {'key': 'value'}. Access: my_dict['key']. Methods: keys(), values(), items()"
  }
]
```

### **Step 2: Register in Bridge**

Once a module is created, we need to tell ISAAC when to call for these modules so we don't overload the system with all modules at once.

Add to `braindata/bridgedata.json`:

```json
[
  {
    "keywords": ["python", "py"],
    "module": "python_module.json"
  }
]
```

### **Step 3: Use**

If the setup was done correctly, you will see the modules listed & everything should work correctly!

Input: "how do I use python lists"
- Detects: "python" keyword
- Loads: `python_module.json` with 3x priority boost
- Matches: "list" + "python" tokens
- Score: `2 matches × 3.0 val × 3.0 module = 18.0`
- Response: Python list syntax

## **API Usage**

### **Basic Integration**

```python
from isaac_core import IsaacCore

# Initialize
isaac = IsaacCore(brain_dir="./braindata")

# Process text
response = isaac.process("what time is it")
print(response)  # "The current time is 02:34 PM"
```

### **Custom Configuration**

```python
isaac = IsaacCore(
    brain_dir="./braindata",
    agent_name="Jarvis",
    user_name="Tony"
)

response = isaac.process("hello")
# "Hello Tony. How can I assist?"
```

## **Advanced Configuration**

### **Tuning Parameters**

In `isaac_core.py`, adjust `Config` class:

```python
class Config:
    MODULE_PRIORITY_BOOST = 3.0    # Multiplier for module entries
    UNIQUE_WORD_BONUS = 1.8        # Boost for unique matches
    
    ACTION_VERBS = {
        "open", "search", "find", "explain"
        # Add custom action verbs
    }
```

### **Custom Stemming**

Modify the `stem()` method to add language-specific rules:

```python
def stem(self, word):
    # Add custom suffixes for your language
    for suffix in ['ing', 'ly', 'ed', 'es']:
        if word.endswith(suffix):
            return word[:-len(suffix)]
    return word
```

## **Troubleshooting**

### **"No matches found" for valid queries**

- Check token spelling in your JSON files
- Remember stemming: "searching" matches "search"
- Verify `val` priority isn't too low (try 3.0+)

### **Wrong intent selected**

- Increase `val` for correct entry
- Add more specific tokens
- Use unique words that only appear in that entry

### **Module not loading**

- Verify keyword exists in `bridgedata.json`
- Check module filename matches exactly
- Ensure JSON is valid (use a validator)
