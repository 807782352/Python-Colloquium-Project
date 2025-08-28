# Python-Colloquium-Project

## Overview
A smart vacation rental platform (like Airbnb) with:
- Streamlit UI for user login/signup, dashboard, and property recommendations
- Persistent user and property data (JSON/SQLite)
- Personalized property recommendations using SBERT vector search
- AI-powered travel agent chat (OpenRouter LLM API)

---

## Project Structure

```
Python-Colloquium-Project/
│
├── main.py, core.py, cli.py           # CLI and core logic
├── requirements.txt                   # Python dependencies
├── .env                               # OpenRouter API key
├── README.md                          # Project documentation
│
├── datasets/
│   ├── users.json                     # User data
│   └── property_listings.json         # Property data
│
├── models/                            # Data models (optional)
├── core/                              # User/property management logic
├── Gr8-Summer-Stays/                  # Streamlit UI app
│   ├── app.py, ui.py, backend_logic.py
│   └── requirements.txt
│
├── recommenders/
│   ├── sbert_recommender.py           # SBERT vector search logic
│   ├── property_vector_db.sqlite      # SQLite DB for property embeddings
│   └── sbert_models/saved_model/      # Pretrained SBERT model files
```

---

## Features & Flow

### 1. User Management
- Sign up/login with user ID, name, group size, preferred environment, budget, password
- Passwords are securely hashed
- Edit/view profile in the dashboard

### 2. Property Listings & Embeddings
- Properties stored in `datasets/property_listings.json`
- Embeddings generated using SBERT and stored in `property_vector_db.sqlite`
- Fast, semantic recommendations using vector search

### 3. Recommendations (Streamlit UI)
- After login, users see personalized property recommendations
- Recommendations use SBERT vector search on precomputed embeddings in SQLite DB
- Properties are ranked by similarity to user preferences (preferred environments, budget)

### 4. AI Travel Agent Chat
- Chat with an AI travel agent (OpenRouter LLM)
- Get travel advice, property suggestions, itinerary help, etc.
- API key loaded from `.env` (never hardcoded)

---

## Setup Instructions

1. **Clone the repository**
   ```sh
   git clone <repo-url>
   ```
2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```
3. **Create and add your OpenRouter/OpenAI API key**
    For OpenRouter: Go to https://openrouter.ai/ and sign up for an account. Generate an API key from your dashboard.

     ```
     OPENROUTER_API_KEY=sk-...
     # or for OpenAI
     OPENAI_API_KEY=sk-...
     ```
4. **(First time only) Generate property embeddings**
   ```sh
   python recommenders/sbert_recommender.py
   ```
   This creates `property_vector_db.sqlite` for fast recommendations.
5. **Run the Streamlit UI**
   ```sh
   streamlit run Gr8-Summer-Stays/app.py
   ```

---

## How to Use

- **Sign up or log in**
- **Dashboard:**
  - View/edit profile
  - See recommended properties (vector search)
  - Save properties
  - Chat with AI travel agent

---

## Recommendation Logic
- User preferences (environments, budget) are embedded using SBERT
- Vector search finds the most similar properties from the SQLite DB
- Top-N properties are shown, ranked by similarity

---

## Requirements
- requests
- python-dotenv
- sentence-transformers
- numpy
- streamlit

---

## Notes
- All sensitive info (API keys) is kept in `.env` (never commit this file)
- If you add new properties, rerun the embedding script to update the DB
- The app is modular and easy to extend

---

## Example Usage

```
$ python main.py
# ... Select mode: CLI or UI ...
# For CLI: interact in the terminal
# For UI: the app will launch Streamlit and open in your browser
# Sign up, log in, view recommendations, chat with AI
```

---
## Acknowledgments
Parts of the initial code framework were generated with the assistance of AI tools, including GitHub Copilot and ChatGPT. The overall system design, logic development, and code review were performed by the project team.

## References
- [SBERT Documentation](https://sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html)
- [Sentence Transformers Tutorial (YouTube)](https://www.youtube.com/watch?app=desktop&v=nZ5j289WN8g)