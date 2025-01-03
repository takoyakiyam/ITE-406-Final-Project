import sys
import csv
import json
import re
import time
import networkx as nx
import spacy
import requests
from datetime import datetime
import matplotlib.pyplot as plt
from transformers import pipeline
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextEdit, QCheckBox, QLabel, QDialog,
    QLineEdit, QTabWidget, QGroupBox, QComboBox, QListWidget, QFileDialog, QListWidgetItem, QProgressBar, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime
from gensim.corpora.dictionary import Dictionary
from gensim.models import LdaModel
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk

nltk.download('punkt')
nltk.download('stopwords')
nlp = spacy.load("en_core_web_md")
summarizer = pipeline("summarization", clean_up_tokenization_spaces=True)

# Load topic labels from a JSON file
with open("topic_labels.json", "r") as file:
    TOPIC_LABELS = json.load(file)
     
SOURCE_COLORS = {
            "Fox News": "#FF9999",
            "Philstar": "#99CCFF",
            "Manila Times": "#99FF99",
            "Rappler": "#FFCC99",
            "GMA News": "#FF99FF",
            "CNN News": "#CC9966"
        }

def categorize_topic_dynamic(keywords):
        """Categorize a topic using semantic similarity with spaCy."""
        best_label = "Miscellaneous"  # Default label if no match is found
        highest_similarity = 0
        
        for label, keyword_list in TOPIC_LABELS.items():
            label_doc = nlp(" ".join(keyword_list))  # Combine label keywords into a single text
            for keyword in keywords:
                keyword_doc = nlp(keyword)
                similarity = label_doc.similarity(keyword_doc)
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_label = label
        return best_label
    
# Scraping functions
def scrape_foxnews():
    url = "https://www.foxnews.com/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    return [h3.get_text(strip=True) for h3 in soup.find_all('h3')]

def scrape_philstar():
    url = "https://www.philstar.com/"
    max_retries = 3  # Maximum number of retries
    retry_delay = 2  # Delay between retries in seconds

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove the specific "Forex & Stocks" sections
            unwanted_sections = soup.find_all("div", class_="ribbon_section news_featured")
            for section in unwanted_sections:
                if "Forex" in section.get_text():
                    # Remove the entire parent ribbon div containing the Forex section
                    section.find_parent("div", class_="ribbon").decompose()

            # Remove the newsletter signup content section by ID
            newsletter_signup = soup.find("div", id="newsletter-signup_content")
            if newsletter_signup:
                newsletter_signup.decompose()

            lotto = soup.find("div", id="lotto_past")
            if lotto:
                lotto.decompose()

            # Extract and return the text of all <h2> elements
            return [h2.get_text(strip=True) for h2 in soup.find_all('h2')]

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to scrape Philstar after {max_retries} attempts. Error: {e}")

def scrape_manilaTimes():
    url = "https://www.manilatimes.net"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    headline_classes = ['article-title-h1', 'article-title-h4', 'article-title-h5']
    headlines = []
    for class_name in headline_classes:
        headlines.extend([div.get_text(strip=True) for div in soup.find_all('div', class_=class_name)])
    return headlines

def scrape_rappler():
    url = "https://www.rappler.com"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    return [h3.get_text(strip=True) for h3 in soup.find_all('h3')]

def scrape_gma():
    url = "https://www.gmanetwork.com/news/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Locate the JavaScript block containing the JSON data
    script_tag = soup.find("script", string=re.compile("GLOBAL_SSR_ROBOT_JUST_IN_JSON"))
    if not script_tag:
        return []

    # Extract the JSON data using regex
    json_match = re.search(r"GLOBAL_SSR_ROBOT_JUST_IN_JSON\s*=\s*(\[.*?\]);", script_tag.string)
    if not json_match:
        return []

    # Parse the JSON data
    news_data = json.loads(json_match.group(1))

    # Filter articles for today's date
    current_date = datetime.now().strftime("%Y-%m-%d")
    todays_articles = [
        item["title"]
        for item in news_data if item["published_date"] == current_date
    ]
    
    if not todays_articles:
        return f"No articles available for {current_date}. This might happen if the day has just started or no new articles are published yet."

    return todays_articles

def scrape_cnn():
    url = "https://www.cnn.com/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all <span> elements with the class 'container__headline-text'
    headlines = [
        span.get_text(strip=True) 
        for span in soup.find_all('span', class_='container__headline-text')
        if 'headline' in span.attrs.get('data-editable', '')
    ]

    return headlines

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NewsNet")
        self.resize(800, 800)

        # Main central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 16px;
                color: #333333;
            }
            QGroupBox {
                border: 2px solid #cccccc;
                border-radius: 10px;
                padding: 10px;
                margin-top: 15px;
                background-color: #ffffff;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
            QCheckBox {
                font-size: 14px;
                padding: 5px;
            }
            QComboBox {
                font-size: 14px;
                padding: 5px;
            }
        """)

        # Header Section
        header_layout = QVBoxLayout()
        self.greeting_label = QLabel("<h1>Welcome to NewsNet</h1>")
        self.greeting_label.setAlignment(Qt.AlignCenter)
        self.greeting_label.setStyleSheet("font-size: 24px; color: #0078d7;")
        header_layout.addWidget(self.greeting_label)
        
        current_date = datetime.now().strftime("%B %d, %Y")
        self.date_label = QLabel(f"Today's Date: <b>{current_date}</b>")
        self.date_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.date_label)
        self.main_layout.addLayout(header_layout)

        # Top label
        self.label = QLabel("<h3>Select Websites to Scrape</h3>")
        self.main_layout.addWidget(self.label)
        
        # Add report preview widget
        self.report_preview = QWebEngineView()
        self.report_preview.setVisible(False)  # Initially hidden
        self.main_layout.addWidget(self.report_preview)

        # Website Selection Area
        self.website_groupbox = QGroupBox("Websites to Scrape")
        website_layout = QHBoxLayout()
        self.checkbox_foxnews = QCheckBox("Fox News")
        self.checkbox_philstar = QCheckBox("Philstar")
        self.checkbox_manilaTimes = QCheckBox("Manila Times")
        self.checkbox_rappler = QCheckBox("Rappler")
        self.checkbox_gma = QCheckBox("GMA News")
        self.checkbox_cnn = QCheckBox("CNN News")
        for checkbox in [self.checkbox_foxnews, self.checkbox_philstar, self.checkbox_manilaTimes, self.checkbox_rappler, self.checkbox_gma, self.checkbox_cnn]:
            checkbox.setStyleSheet("font-size: 14px; color: #333333;")
            website_layout.addWidget(checkbox)
        self.website_groupbox.setLayout(website_layout)
        self.main_layout.addWidget(self.website_groupbox)

        # Scraping Operations Group
        self.scraping_operations_group = QGroupBox("Scraping Operations")
        self.scraping_operations_layout = QHBoxLayout()
        self.check_all_button = QPushButton("Select All Websites")
        self.check_all_button.clicked.connect(self.toggle_select_all)
        self.scrape_button = QPushButton("Scrape Selected Websites")
        self.scrape_button.clicked.connect(self.scrape_websites)
        self.scraping_operations_layout.addWidget(self.check_all_button)
        self.scraping_operations_layout.addWidget(self.scrape_button)
        self.scraping_operations_group.setLayout(self.scraping_operations_layout)
        self.main_layout.addWidget(self.scraping_operations_group)

        # Analysis Operations Group
        self.analysis_operations_group = QGroupBox("Analysis Operations")
        self.analysis_operations_layout = QHBoxLayout()
        self.view_aggregated_button = QPushButton("👁️‍🗨️ View Aggregated Articles")
        self.view_aggregated_button.clicked.connect(self.view_aggregated_content)
        self.visualize_network_button = QPushButton("🌐  Visualize Network")
        self.visualize_network_button.clicked.connect(self.visualize_network)
        self.analyze_topics_button = QPushButton("👨🏻‍💻 Analyze Topics")
        self.analyze_topics_button.clicked.connect(self.analyze_topics)
        self.generate_report_button = QPushButton("📄 Generate Report")
        self.generate_report_button.clicked.connect(self.generate_report)
        self.export_data_button = QPushButton("💾 Export Data")
        self.export_data_button.clicked.connect(self.export_data)

        self.analysis_operations_layout.addWidget(self.view_aggregated_button)
        self.analysis_operations_layout.addWidget(self.visualize_network_button)
        self.analysis_operations_layout.addWidget(self.analyze_topics_button)
        self.analysis_operations_layout.addWidget(self.generate_report_button)
        self.analysis_operations_layout.addWidget(self.export_data_button)
        self.analysis_operations_group.setLayout(self.analysis_operations_layout)
        self.main_layout.addWidget(self.analysis_operations_group)

        # Results display
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("Scraped results will appear here...")
        self.main_layout.addWidget(self.results_display)

        # State tracking
        self.all_selected = False
        self.scraped_content = {}
        
    def preprocess_articles(self, articles):
        """Preprocess articles for topic modeling."""
        import nltk
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize

        # Download necessary NLTK data
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)

        stop_words = set(stopwords.words('english'))
        processed_articles = []
        for article in articles:
            tokens = word_tokenize(article.lower())  # Tokenize and lowercase
            tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
            processed_articles.append(tokens)
        return processed_articles


    def toggle_select_all(self):
        """Toggle all checkboxes."""
        self.all_selected = not self.all_selected
        state = self.all_selected
        for checkbox in [self.checkbox_foxnews, self.checkbox_philstar, self.checkbox_manilaTimes, self.checkbox_rappler, self.checkbox_gma, self.checkbox_cnn]:
            checkbox.setChecked(state)
        self.check_all_button.setText("Unselect All Websites" if state else "Select All Websites")

    def scrape_websites(self):
        """Scrape selected websites and display results."""
        self.results_display.clear()
        if not any([
            self.checkbox_foxnews.isChecked(),
            self.checkbox_philstar.isChecked(),
            self.checkbox_manilaTimes.isChecked(),
            self.checkbox_rappler.isChecked(),
            self.checkbox_gma.isChecked(),
            self.checkbox_cnn.isChecked()
        ]):
            self.results_display.append("<b>Error:</b> No website selected. Please choose a website.")
            return

        # Show the loading dialog
        loading_dialog = LoadingDialog("Scraping websites...", self)
        loading_dialog.show()
        QApplication.processEvents()  # Allow the dialog to update
        
        self.scraped_content = {}
        websites = [
            ("Fox News", self.checkbox_foxnews.isChecked(), scrape_foxnews),
            ("Philstar", self.checkbox_philstar.isChecked(), scrape_philstar),
            ("Manila Times", self.checkbox_manilaTimes.isChecked(), scrape_manilaTimes),
            ("Rappler", self.checkbox_rappler.isChecked(), scrape_rappler),
            ("GMA News", self.checkbox_gma.isChecked(), scrape_gma),
            ("CNN News", self.checkbox_cnn.isChecked(), scrape_cnn)
        ]

        self.results_display.append(f"<b>Scraping articles...</b>")

        try:
            for name, is_checked, scraper in websites:
                if is_checked:
                    # Update the dialog message for each website
                    loading_dialog.update_message(f"Scraping {name}...")
                    QApplication.processEvents()  # Update the dialog
                    
                    try:
                        self.scraped_content[name] = scraper()
                        self.results_display.append(f"{name}: {len(self.scraped_content[name])} articles scraped.")
                    except Exception as e:
                        self.results_display.append(f"{name}: Failed to scrape. ({str(e)})")
        finally:
            # Close the loading dialog when scraping is complete
            loading_dialog.close()

        self.results_display.append("\n<b>Scraping complete.</b>")

    def visualize_network(self):
        """Visualize the network of common articles across news sources."""
        if not self.scraped_content:
            self.results_display.append("<b>Error:</b> No content to visualize. Scrape websites first.")
            return

        # Open the VisualizeNetworkDialog
        dialog = VisualizeNetworkDialog(self.scraped_content, self)
        dialog.exec_()

    def analyze_topics(self):
        """Analyze topics from aggregated articles using LDA and dynamic matching."""
        if not self.scraped_content:
            self.results_display.append("<b>Error:</b> No content to analyze. Scrape websites first.")
            return

        # Open dynamic dialog for topic analysis
        dialog = TopicAnalysisDialog(self.scraped_content, self)
        dialog.exec_()

    def generate_report(self):
        """Generate a detailed, printable report and preview it in a dialog."""
        self.results_display.clear()

        if not self.scraped_content:
            self.results_display.append("<b>Error:</b> No content available to generate a report. Scrape websites first.")
            return

        self.results_display.append("<b>Generating report...</b>")

        # Create a base HTML template for the report
        report_html = [
            "<html>",
            "<head>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1, h2, h3 { color: #2c3e50; }",
            "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
            "table, th, td { border: 1px solid #ddd; }",
            "th, td { padding: 8px; text-align: left; }",
            "th { background-color: #f4f4f4; }",
            ".section { margin-bottom: 30px; }",
            "</style>",
            "</head>",
            "<body>",
        ]

        # Report Header
        current_date = datetime.now().strftime("%B %d, %Y")
        report_html.append(f"<h1>News Analysis Report</h1>")
        report_html.append(f"<p><b>Date:</b> {current_date}</p>")

        # Aggregated Scrape Count
        total_articles = sum(len(articles) for articles in self.scraped_content.values())
        report_html.append(f"<div class='section'><h2>Aggregated Scrape Count</h2>")
        report_html.append(f"<p>Total Articles Scraped: <b>{total_articles}</b></p></div>")

        # Scraped Content Summary by Source
        report_html.append("<div class='section'><h2>Scraped Content Summary</h2>")
        report_html.append("<table><tr><th>Source</th><th>Articles Scraped</th></tr>")
        for source, articles in self.scraped_content.items():
            report_html.append(f"<tr><td>{source}</td><td>{len(articles)}</td></tr>")
        report_html.append("</table></div>")

        # Topic Modeling Summary
        report_html.append("<div class='section'><h2>Topic Analysis</h2>")
        combined_articles = [article for articles in self.scraped_content.values() for article in articles]
        if combined_articles:
            processed_articles = self.preprocess_articles(combined_articles)
            dictionary = Dictionary(processed_articles)
            corpus = [dictionary.doc2bow(text) for text in processed_articles]
            lda_model = LdaModel(corpus, num_topics=5, id2word=dictionary, passes=15)

            # Include top topics
            topics = lda_model.show_topics(num_topics=5, num_words=5, formatted=False)
            report_html.append("<ul>")
            for idx, topic in topics:
                keywords = ", ".join([word for word, _ in topic])
                report_html.append(f"<li><b>Topic {idx + 1}:</b> {keywords}</li>")
            report_html.append("</ul>")
        else:
            report_html.append("<p>No articles available for topic analysis.</p>")
        report_html.append("</div>")

        # Close HTML
        report_html.append("</body></html>")
        report_html = "\n".join(report_html)

        # Open the ReportPreviewDialog
        dialog = ReportPreviewDialog(report_html, self)
        dialog.exec_()

        self.results_display.append("<b>Report preview loaded successfully!</b>")


    def export_data(self):
        """Export scraped data to JSON or CSV."""
        if not self.scraped_content:
            self.results_display.append("<b>Error:</b> No data available to export. Scrape websites first.")
            return

        # Get the current date and time for the default file name
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_file_name = f"AggregatedNews - {current_time}"

        # Open a file dialog for the user to choose the save location
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            default_file_name,  # Set the default file name here
            "JSON Files (*.json);;CSV Files (*.csv)",
            options=options
        )

        if not file_path:
            self.results_display.append("<b>Export canceled:</b> No file selected.")
            return

        try:
            if file_path.endswith(".json"):
                # Save as JSON
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(self.scraped_content, file, indent=4, ensure_ascii=False)
                self.results_display.append(f"<b>Success:</b> Data exported to {file_path}")
            elif file_path.endswith(".csv"):
                # Save as CSV
                with open(file_path, "w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Source", "Article"])
                    for source, articles in self.scraped_content.items():
                        for article in articles:
                            writer.writerow([source, article])
                self.results_display.append(f"<b>Success:</b> Data exported to {file_path}")
            else:
                self.results_display.append("<b>Error:</b> Unsupported file format.")
        except Exception as e:
            self.results_display.append(f"<b>Error:</b> Failed to export data. ({str(e)})")

    def view_aggregated_content(self):
            """Display aggregated articles."""
            if not self.scraped_content:
                self.results_display.append("<b>Error:</b> No content to display. Scrape websites first.")
                return

            dialog = AggregatedNews("Aggregated Articles", self.scraped_content, self)
            dialog.exec_()

class AggregatedNews(QDialog):
    def __init__(self, title, aggregated_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)

        # Main layout
        self.aggregated_content = aggregated_content
        self.layout = QVBoxLayout(self)

        # Initialize sentiment analyzer and cache
        self.sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
        self.sentiment_cache = {}  # Cache to store precomputed sentiment results

        # Store current search query and sentiment filter globally
        self.current_query = ""
        self.current_sentiment = "All"

        # Search bar
        search_layout = QHBoxLayout()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Type to search articles...")
        self.search_field.textChanged.connect(self.update_filters)  # Dynamic search
        search_layout.addWidget(self.search_field)
        self.layout.addLayout(search_layout)

        # Sorting Dropdown
        sort_layout = QHBoxLayout()
        self.sort_dropdown = QComboBox()
        self.sort_dropdown.addItems(["Sort by Sentiment", "All", "Positive", "Negative"])
        self.sort_dropdown.setFixedSize(150, 25)
        self.sort_dropdown.model().item(0).setEnabled(False)
        self.sort_dropdown.currentTextChanged.connect(self.update_filters)  # Dynamic sort
        sort_layout.addWidget(QLabel("Sort:"))
        sort_layout.addWidget(self.sort_dropdown)
        self.layout.addLayout(sort_layout)

        # Description for color coding
        description_label = QLabel(
            "<b>Color Coding:</b> "
            "<span style='color: #006400;'>Green</span>: Positive, "
            "<span style='color: red;'>Red</span>: Negative"
        )
        description_label.setWordWrap(True)
        self.layout.addWidget(description_label)

        # Tab view for content
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.refresh_current_tab)  # Refresh the tab when switching

        # Create "All Articles" tab
        self.all_articles_tab = QWidget()
        self.all_articles_layout = QVBoxLayout(self.all_articles_tab)
        self.all_articles_list = QListWidget()

        # Combine all articles into one list
        self.combined_articles = []
        for articles in aggregated_content.values():
            self.combined_articles.extend(articles)

        # Precompute sentiment for all articles
        self.precompute_sentiments()

        # Populate the "All Articles" list
        self.populate_list_widget(self.all_articles_list, self.combined_articles)
        self.all_articles_layout.addWidget(self.all_articles_list)
        self.tabs.addTab(self.all_articles_tab, "All Articles")

        # Add source-specific tabs
        self.source_displays = {}
        for source, articles in aggregated_content.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            list_widget = QListWidget()
            self.populate_list_widget(list_widget, articles)
            tab_layout.addWidget(list_widget)
            self.tabs.addTab(tab, source)
            self.source_displays[source] = list_widget

        # Add tabs to layout
        self.layout.addWidget(self.tabs)

    def analyze_sentiment(self, text):
        """Analyze sentiment using precomputed results."""
        if text not in self.sentiment_cache:
            result = self.sentiment_analyzer(text[:512])  # Truncate to DistilBERT max token length
            label = result[0]['label']  # Positive or Negative
            self.sentiment_cache[text] = "positive" if label == "POSITIVE" else "negative"
        return self.sentiment_cache[text]

    def precompute_sentiments(self):
        """Precompute and cache sentiments for all articles."""
        for article in self.combined_articles:
            self.analyze_sentiment(article)

    def populate_list_widget(self, list_widget, articles):
        """Populate a QListWidget with a list of articles, color-coded by sentiment."""
        list_widget.clear()
        if not articles:
            # Add placeholder for no results
            placeholder_item = QListWidgetItem("No articles match your query.")
            placeholder_item.setForeground(Qt.gray)
            list_widget.addItem(placeholder_item)
            return

        for article in articles:
            sentiment = self.analyze_sentiment(article)
            item = QListWidgetItem(article)

            # Set text color based on sentiment
            if sentiment == "positive":
                item.setForeground(Qt.darkGreen)
            elif sentiment == "negative":
                item.setForeground(Qt.red)

            # Make text bold
            font = QFont()
            font.setBold(True)
            item.setFont(font)

            list_widget.addItem(item)

    def update_filters(self):
        """Update the search query and sentiment filter dynamically."""
        self.current_query = self.search_field.text().strip().lower()
        self.current_sentiment = self.sort_dropdown.currentText()
        self.refresh_all_tabs()

    def refresh_current_tab(self):
        """Refresh the currently active tab based on the search query and sentiment filter."""
        current_tab_index = self.tabs.currentIndex()
        tab_name = self.tabs.tabText(current_tab_index)

        if tab_name == "All Articles":
            articles = self.combined_articles
            list_widget = self.all_articles_list
        else:
            articles = self.aggregated_content.get(tab_name, [])
            list_widget = self.source_displays.get(tab_name)

        self.apply_filters_and_update(list_widget, articles)

    def refresh_all_tabs(self):
        """Refresh all tabs to reflect the search query and sentiment filter."""
        for tab_index in range(self.tabs.count()):
            tab_name = self.tabs.tabText(tab_index)
            if tab_name == "All Articles":
                articles = self.combined_articles
                list_widget = self.all_articles_list
            else:
                articles = self.aggregated_content.get(tab_name, [])
                list_widget = self.source_displays.get(tab_name)

            self.apply_filters_and_update(list_widget, articles)

    def apply_filters_and_update(self, list_widget, articles):
        """Apply search and sentiment filters to a given list and update the widget."""
        # Apply sentiment filter
        if self.current_sentiment != "All":
            articles = [
                article for article in articles
                if self.analyze_sentiment(article) == self.current_sentiment.lower()
            ]

        # Apply search query filter
        if self.current_query:
            articles = [article for article in articles if self.current_query in article.lower()]

        self.populate_list_widget(list_widget, articles)

class TopicAnalysisDialog(QDialog):
    def __init__(self, scraped_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Topic Analysis")
        self.resize(900, 750)

        # Save scraped content
        self.scraped_content = scraped_content

        # Create a vertical layout
        self.layout = QVBoxLayout(self)

        # Add header and description
        date = datetime.now().strftime("%B %d, %Y")  # Current date
        header = QLabel(f"<h2>Topic Analysis for {date}</h2>")
        description = QLabel(
            "<p><i>This analysis uses <b>Latent Dirichlet Allocation (LDA)</b> to extract topics from articles. "
            "Please note that the topic distribution is an approximation and may not be fully accurate.</i></p>"
        )
        header.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)

        # Add header and description to the layout
        self.layout.addWidget(header)
        self.layout.addWidget(description)

        # Dropdown for selecting the news source
        self.layout.addWidget(QLabel("Select News Source:"))  # Proper label for combobox
        self.source_dropdown = QComboBox()
        self.source_dropdown.addItem("All Sources")
        self.source_dropdown.addItems(self.scraped_content.keys())
        self.source_dropdown.currentTextChanged.connect(self.update_graph)
        self.layout.addWidget(self.source_dropdown)

        # Placeholder for graph
        self.figure, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Initial graph generation
        self.update_graph()

    def preprocess_articles(self, articles):
        """Preprocess articles for topic modeling."""
        stop_words = set(stopwords.words('english'))
        processed_articles = []
        for article in articles:
            tokens = word_tokenize(article.lower())  # Tokenize and lowercase
            tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
            processed_articles.append(tokens)
        return processed_articles

    def update_graph(self):
        """Update the bar graph dynamically based on the selected news source."""
        selected_source = self.source_dropdown.currentText()

        # Combine articles based on the user's choice
        if selected_source == "All Sources":
            combined_articles = []
            for articles in self.scraped_content.values():
                combined_articles.extend(articles)
            bar_color = "#CCCCCC"  # Default color for "All Sources"
        else:
            combined_articles = self.scraped_content.get(selected_source, [])
            bar_color = SOURCE_COLORS.get(selected_source, "#CCCCCC")  # Use source-specific color

        if not combined_articles:
            self.ax.clear()
            self.ax.set_title(f"No articles available for {selected_source}")
            self.canvas.draw()
            return

        # Preprocess articles and perform topic modeling
        processed_articles = self.preprocess_articles(combined_articles)
        dictionary = Dictionary(processed_articles)
        corpus = [dictionary.doc2bow(text) for text in processed_articles]

        try:
            lda_model = LdaModel(corpus, num_topics=5, id2word=dictionary, passes=15)
        except Exception as e:
            self.ax.clear()
            self.ax.set_title(f"Error during topic modeling: {str(e)}")
            self.canvas.draw()
            return

        topics = lda_model.show_topics(num_topics=5, num_words=5, formatted=False)
        labeled_topics = []
        for idx, topic in topics:
            keywords = [word for word, _ in topic]
            label = categorize_topic_dynamic(keywords)
            weight_sum = sum(weight for _, weight in topic)
            labeled_topics.append((label, weight_sum, keywords))

        self.ax.clear()
        topic_labels = [label for label, _, _ in labeled_topics]
        weights = [weight for _, weight, _ in labeled_topics]

        # Draw the bar graph with the source-specific color
        self.ax.barh(topic_labels, weights, color=bar_color, align="center")
        self.ax.set_xlabel("Weight")
        self.ax.set_title(f"Top Topics for {selected_source}")
        self.ax.invert_yaxis()
        self.canvas.draw()

class VisualizeNetworkDialog(QDialog):
    def __init__(self, scraped_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visualize Network")
        self.resize(900, 900)

        # Save scraped content
        self.scraped_content = scraped_content

        # Main layout for the dialog
        self.layout = QVBoxLayout(self)

        # Add directions and labels at the top
        self.directions = QLabel(
            "<h3>News Articles Network</h3>"
            "<p>This visualization shows the shared news articles between different sources.</p>"
            "<p><b>Source Node Colors:</b></p>"
            "<p><u><b style='color:#CCCCCC;'>⬤ Grey Nodes</b></u>: Represent shared news articles between two or more sources.</p>"
            "<p>Edges are color-coded to match their respective sources.</p>"
            "<p><i>Hover over a node to view the full title of an article.</i></p>"
        )


        self.directions.setWordWrap(True)
        self.layout.addWidget(self.directions)

        # Placeholder for the network graph
        self.figure, self.ax = plt.subplots(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Generate and display the network graph
        self.G, self.pos, self.labels, self.node_types = self.generate_network_graph()

        # Connect hover event for article nodes
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def generate_network_graph(self):
        """Create and display a network graph of common articles with improved spacing."""
        if not self.scraped_content:
            self.ax.clear()
            self.ax.set_title("No data available to visualize.")
            self.canvas.draw()
            return None, None, None, None

        # Build the network graph
        G = nx.Graph()
        sources = list(self.scraped_content.keys())
        labels = {}  # Dictionary to map nodes to labels for hover
        node_types = {}  # Dictionary to distinguish between sources and articles

        # Assign distinct pastel colors to sources
        source_colors = {
            source: color for source, color in zip(
                sources, ['#FF9999', '#99CCFF', '#99FF99', '#FFCC99', '#FF99FF', '#CC9966']
            )
        }

        # Add nodes for each source
        for source in sources:
            G.add_node(source, type='source', color=source_colors[source])
            labels[source] = source  # Use source name as its label
            node_types[source] = "source"

        # Compare articles and add shared articles as nodes and edges
        for i, source1 in enumerate(sources):
            for source2 in sources[i + 1:]:
                for article1 in self.scraped_content[source1]:
                    for article2 in self.scraped_content[source2]:
                        if self.has_significant_word_overlap(article1, article2):
                            truncated_title = self.truncate_text(article1)
                            G.add_node(truncated_title, type='article', color='#CCCCCC')  # Light grey for shared articles
                            G.add_edge(source1, truncated_title, color=source_colors[source1])
                            G.add_edge(source2, truncated_title, color=source_colors[source2])
                            labels[truncated_title] = article1  # Store full article title for hover
                            node_types[truncated_title] = "article"

        # Visualization: Extract node and edge colors
        node_colors = [G.nodes[node].get('color', 'gray') for node in G.nodes]
        edge_colors = [G[u][v]['color'] for u, v in G.edges]

        # Use spring layout with high repulsion for better spacing
        pos = nx.spring_layout(G, k=3.0, seed=42)  # Increased `k` for more spacing

        # Clear the previous graph
        self.ax.clear()
        self.ax.set_title("News Articles Network")

        # Draw nodes
        nx.draw_networkx_nodes(
            G, pos, nodelist=G.nodes, ax=self.ax,
            node_color=node_colors, node_size=700
        )

        # Draw edges with color matching their sources
        for (u, v), color in zip(G.edges, edge_colors):
            x = [pos[u][0], pos[v][0]]
            y = [pos[u][1], pos[v][1]]
            self.ax.plot(x, y, color=color, linewidth=2.5)

        # Draw labels for source nodes
        source_labels = {node: node for node in G.nodes if node_types.get(node) == "source"}
        nx.draw_networkx_labels(G, pos, labels=source_labels, font_size=10, font_weight="bold", ax=self.ax)

        # Render the canvas
        self.canvas.draw()
        return G, pos, labels, node_types

    def has_significant_word_overlap(self, title1, title2):
        """Check if two article titles have at least 4 words in common."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        common_words = words1 & words2
        return len(common_words) >= 4

    def truncate_text(self, text, max_length=50):
        """Truncate long text to fit within the graph."""
        return text if len(text) <= max_length else text[:max_length] + "..."

    def on_hover(self, event):
        """Display the full title of article nodes near the hovered node on the graph."""
        if event.inaxes == self.ax:
            # Remove only dynamic hover labels
            for text in self.ax.texts:
                if getattr(text, "is_hover_label", False):  # Only remove hover labels
                    text.remove()

            for node, (x, y) in self.pos.items():
                # Map the node's position from data coordinates to display coordinates
                screen_x, screen_y = self.ax.transData.transform((x, y))
                canvas_width = self.canvas.width()  # Get the width of the canvas in pixels

                # Check proximity in pixels (tuned to 10-pixel radius)
                if abs(screen_x - event.x) < 10 and abs(screen_y - event.y) < 10:
                    node_type = self.node_types.get(node)
                    if node_type == "article":
                        full_title = self.labels.get(node, "")

                        # Determine the label's horizontal position based on node's location
                        if screen_x > canvas_width / 2:  # If node is on the right half
                            label_x = x - 0.02  # Position label to the left
                        else:  # If node is on the left half
                            label_x = x + 0.02  # Position label to the right

                        # Add a dynamic label near the hovered node
                        hover_label = self.ax.text(
                            label_x, y, full_title,
                            fontsize=8, color="black", weight="bold", zorder=10
                        )
                        hover_label.is_hover_label = True  # Mark this label as a hover label
                        self.canvas.draw_idle()
                        return

            # Redraw the canvas to clear hover labels if no node is hovered
            self.canvas.draw_idle()

class ReportPreviewDialog(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Preview")
        self.resize(900, 600)

        # Layout for the dialog
        layout = QVBoxLayout(self)

        # Add QWebEngineView for previewing the report
        self.web_view = QWebEngineView()
        self.web_view.setHtml(html_content)
        layout.addWidget(self.web_view)

        # Add print button
        self.print_button = QPushButton("🖨️ Print Report")
        self.print_button.clicked.connect(self.print_report)
        layout.addWidget(self.print_button)

    def print_report(self):
        """Print the report."""
        printer = QPrinter()
        printer.setPageSize(QPrinter.A4)
        printer.setOutputFormat(QPrinter.NativeFormat)

        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            self.web_view.print(printer)
            
class LoadingDialog(QDialog):
    def __init__(self, message="Loading, please wait...", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Please Wait")
        self.setModal(True)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.resize(300, 100)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)  # Infinite loading effect
        layout.addWidget(self.progress)

    def update_message(self, new_message):
        self.label.setText(new_message)
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
