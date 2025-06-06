## 💖 FitFinder AI

*Built by Sam and Bella*

A fashion-forward outfit recommender powered by Claude (Anthropic) and Google Shopping via SerpAPI. Describe your event, vibe, or color aesthetic — and get curated, shoppable outfit suggestions with style and sass.

### 🎯 Features

* 💬 **Conversational AI** powered by Claude 3 Sonnet on Amazon Bedrock
* 🛍️ **Real-time fashion search** with SerpAPI + Google Shopping
* 💡 **Contextual memory**: Claude asks clarifying questions before suggesting outfits
* 👛 Optional follow-ups for **accessories, bags, and shoes**
* 🎨 **Beautiful UI** with a soft pink palette and animated splash screen

### 🖥️ How to Run Locally

1. **Clone the repo**

```bash
git clone https://github.com/YOUR-USERNAME/fitfinder-ai.git
cd fitfinder-ai
```

2. **Set up your environment**

```bash
python -m venv genAIenv
source genAIenv/bin/activate  # or `.\genAIenv\Scripts\activate` on Windows
pip install -r requirements.txt
```

3. **Set up your `.env` file** in the project root:

```
SERPAPI_API_KEY=your_serpapi_key_here
AWS_PROFILE=your_aws_profile  # or omit if your credentials are globally configured
```

4. **Run the app**

```bash
streamlit run fitfinder.py
```

---

### 📁 Project Structure

```
fitfinder-ai/
├── fitfinder.py            # Main Streamlit app
├── requirements.txt        # Cleaned dependencies
├── .env                    # Environment secrets (not pushed)
├── .streamlit/
│   └── config.toml         # Light mode, custom theme
└── README.md               # You're reading it!
```

---

### 🌐 Technologies Used

* **Streamlit** for the frontend UI
* **Anthropic Claude 3 Sonnet** via Amazon Bedrock for LLM-powered styling
* **SerpAPI** with Google Shopping engine for real-time fashion product data
* **Python + dotenv** for environment and tool management

---

### ✨ Future Ideas

* Outfit filter (price, season, formality)
* Outfit collage exports
* Social sharing or Pinterest-style board integration
* Multi-agent support (stylist, trend predictor, etc.)