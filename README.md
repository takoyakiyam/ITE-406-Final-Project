# NewsNet - Aggregated News Scraping, Analysis, and Visualization Tool

NewsNet is a user-friendly application designed to scrape, analyze, and visualize news articles from multiple sources. With features like dynamic topic categorization, sentiment analysis, and network visualization, NewsNet offers a comprehensive solution for news aggregation and insights.

_note: The scraping methods are extremely inefficient and oversimplified._

---

## Features

### 📰 Multi-source News Scraping
Scrape articles from popular websites such as:
- CNN
- Fox News
- Rappler
- GMA News
- Manila Times
- Philstar

### 🧠 Dynamic Topic Categorization
- Use advanced NLP techniques with **spaCy** and **LDA (Latent Dirichlet Allocation)**.
- Automatically categorize articles into meaningful topics.

### 😃 Sentiment Analysis
- Classify article sentiment as **Positive**, **Negative**, or **Neutral** using pre-trained transformers from **Hugging Face**.

### 🌐 Network Visualization
- Visualize relationships between news articles across different sources using **NetworkX** and **Matplotlib**.
- Understand shared themes and overlaps in news coverage.

### 🔍 Aggregated Content Management
- Search and filter scraped articles across all sources.
- Preview, manage, and organize articles in a sleek GUI.

### 📄 Export and Reporting
- Export data in **JSON** or **CSV** formats.
- Generate and preview detailed, printable HTML reports summarizing insights.

---

## Key Technologies
- **Web Scraping:** BeautifulSoup, Requests
- **Natural Language Processing:** spaCy, Gensim, NLTK, Hugging Face Transformers
- **Visualization:** NetworkX, Matplotlib
- **GUI Development:** PyQt5
- **Data Handling:** JSON, CSV

---
