## PickWise – Dota 2 Strategy Assistant

PickWise is a Flask-based AI assistant that answers Dota 2 questions about hero counters, item builds, item explanations, and general strategy. It combines a lightweight machine‑learning intent classifier with rule‑based triggers and live data from the OpenDota API.

### 1. Environment setup

1. **Create and activate a virtual environment (recommended)**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   This installs Flask, scikit-learn, pandas, numpy, NLTK, spaCy, and other dependencies used by the project.

### 2. Running the application

From the project root (`pickwise1`), run:

```bash
python app.py
```

This will start the Flask development server on `http://0.0.0.0:5000`. The main chat endpoints are:

- `GET /` – Renders the classic HTML interface (if templates are present).
- `POST /ask` – Legacy JSON API: `{"question": "your text"}`.
- `POST /chat` – Modern JSON chat API: `{"message": "your text"}`.

Both `/ask` and `/chat` return an answer, the detected intent, and a confidence score.

### 3. Training the intent model (optional)

If you want to (re)train the intent classifier used for intent prediction:

1. Make sure `pickwise/data/intents_dataset.csv` exists with at least `question` and `intent` columns.
2. From the project root, run the module:

   ```bash
   python -m pickwise.train_model
   ```

   This will train a scikit‑learn pipeline and save it to `pickwise/models/intent_model.pkl`.

PickWise will still function without the trained model by falling back to robust rule‑based intent detection and conversational response templates.

### 4. Notes

- On first use, NLTK will automatically download required tokenizers and corpora (stopwords, wordnet, punkt). This may take a moment the first time you send a request that triggers text preprocessing.
- PickWise relies on the public OpenDota API. If OpenDota is temporarily unavailable, the assistant will return a clear, human‑readable error message instead of failing.

