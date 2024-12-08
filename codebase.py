import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import CountVectorizer
from gensim.models import LdaModel
from gensim.corpora import Dictionary
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QCheckBox, QLabel, QDialog, QLineEdit, QHBoxLayout)

# Scraping functions
def scrape_foxnews():
    url = "https://www.foxnews.com/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    headlines = [h3.get_text(strip=True) for h3 in soup.find_all('h3')]
    return headlines

def scrape_philstar():
    url = "https://www.philstar.com/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    headlines = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
    return headlines

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
    headlines = [h3.get_text(strip=True) for h3 in soup.find_all('h3')]
    return headlines

# Analysis Tools
class AnalysisTools:
    @staticmethod
    def topic_modeling(articles, num_topics=5):
        """Perform LDA topic modeling on the given articles."""
        # Preprocess articles
        vectorizer = CountVectorizer(stop_words='english')
        X = vectorizer.fit_transform(articles)
        feature_names = vectorizer.get_feature_names_out()

        # Create dictionary and corpus for LDA
        tokens = [text.split() for text in articles]
        dictionary = Dictionary(tokens)
        corpus = [dictionary.doc2bow(text) for text in tokens]

        # Perform LDA
        lda = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=15)
        topics = lda.show_topics(formatted=False)
        topic_summaries = []
        for topic in topics:
            words = [word for word, _ in topic[1]]
            topic_summaries.append(f"Topic {topic[0]}: {', '.join(words)}")
        return topic_summaries

    @staticmethod
    def build_cooccurrence_graph(articles):
        """Build a co-occurrence graph from the given articles."""
        graph = nx.Graph()
        for article in articles:
            words = article.split()
            for i, word1 in enumerate(words):
                for word2 in words[i + 1:]:
                    if graph.has_edge(word1, word2):
                        graph[word1][word2]['weight'] += 1
                    else:
                        graph.add_edge(word1, word2, weight=1)
        return graph

    @staticmethod
    def visualize_graph(graph):
        """Visualize the graph using Matplotlib."""
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(graph)
        nx.draw_networkx_nodes(graph, pos, node_size=700)
        nx.draw_networkx_edges(graph, pos, width=1.0, alpha=0.5)
        nx.draw_networkx_labels(graph, pos, font_size=12)
        plt.title("Co-occurrence Graph")
        plt.show()

# Content Dialog
class ContentDialog(QDialog):
    def __init__(self, title, aggregated_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)
        self.aggregated_content = aggregated_content

        # Layouts
        main_layout = QVBoxLayout(self)
        filter_layout = QHBoxLayout()
        search_layout = QHBoxLayout()

        # Source filter checkboxes
        self.source_checkboxes = {}
        for source in self.aggregated_content.keys():
            checkbox = QCheckBox(source)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.update_display)
            filter_layout.addWidget(checkbox)
            self.source_checkboxes[source] = checkbox

        # Search bar
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Enter keyword to search...")
        search_layout.addWidget(self.search_input)

        # Search button
        self.search_button = QPushButton("Search", self)
        self.search_button.clicked.connect(self.search_content)
        search_layout.addWidget(self.search_button)

        # Display area
        self.text_display = QTextEdit(self)
        self.text_display.setReadOnly(True)
        self.update_display()

        # Add layouts and widgets
        main_layout.addLayout(filter_layout)
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.text_display)

    def update_display(self):
        """Update the displayed content based on selected sources."""
        selected_sources = [source for source, checkbox in self.source_checkboxes.items() if checkbox.isChecked()]
        filtered_content = []

        for source in selected_sources:
            for article in self.aggregated_content[source]:
                filtered_content.append(f"[{source.upper()}] {article}")

        self.text_display.setText("\n".join(filtered_content) if filtered_content else "No articles available.")

    def search_content(self):
        """Search for a keyword and refresh content to show only matching lines."""
        keyword = self.search_input.text().strip()
        if not keyword:
            self.update_display()
            return

        selected_sources = [source for source, checkbox in self.source_checkboxes.items() if checkbox.isChecked()]
        matching_lines = []

        for source in selected_sources:
            for article in self.aggregated_content[source]:
                if keyword.lower() in article.lower():
                    matching_lines.append(f"[{source.upper()}] {article}")

        self.text_display.setText("\n".join(matching_lines) if matching_lines else "No matching content found.")

# Main Application Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced News Scraper with Topic Modeling & Graph Analysis")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Add a label
        self.label = QLabel("Select websites to scrape:")
        self.layout.addWidget(self.label)

        # Add checkboxes for website selection
        self.checkbox_foxnews = QCheckBox("Fox News")
        self.checkbox_philstar = QCheckBox("Philstar")
        self.checkbox_manilaTimes = QCheckBox("Manila Times")
        self.checkbox_rappler = QCheckBox("Rappler")

        # Add checkboxes to layout
        self.layout.addWidget(self.checkbox_foxnews)
        self.layout.addWidget(self.checkbox_philstar)
        self.layout.addWidget(self.checkbox_manilaTimes)
        self.layout.addWidget(self.checkbox_rappler)

        # Add buttons
        self.scrape_button = QPushButton("Scrape Selected Websites")
        self.scrape_button.clicked.connect(self.scrape_websites)
        self.layout.addWidget(self.scrape_button)

        self.aggregated_button = QPushButton("View Aggregated Articles")
        self.aggregated_button.clicked.connect(self.view_aggregated_content)
        self.layout.addWidget(self.aggregated_button)

        self.topic_button = QPushButton("Perform Topic Modeling")
        self.topic_button.clicked.connect(self.perform_topic_modeling)
        self.layout.addWidget(self.topic_button)

        self.graph_button = QPushButton("Visualize Co-occurrence Graph")
        self.graph_button.clicked.connect(self.visualize_cooccurrence_graph)
        self.layout.addWidget(self.graph_button)

        # Add a text area to display results
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.layout.addWidget(self.results_display)

        # Storage for scraped content
        self.scraped_content = {}

    def scrape_websites(self):
        """Scrape selected websites and aggregate articles."""
        self.scraped_content = {}
        websites = [
            ("Fox News", self.checkbox_foxnews.isChecked(), scrape_foxnews),
            ("Philstar", self.checkbox_philstar.isChecked(), scrape_philstar),
            ("Manila Times", self.checkbox_manilaTimes.isChecked(), scrape_manilaTimes),
            ("Rappler", self.checkbox_rappler.isChecked(), scrape_rappler),
        ]
        for name, is_checked, scrape_func in websites:
            if is_checked:
                try:
                    articles = scrape_func()
                    self.scraped_content[name] = articles
                    self.results_display.append(f"{name}: Scraped {len(articles)} articles.")
                except Exception as e:
                    self.results_display.append(f"{name}: Failed to scrape ({e}).")
        self.results_display.append("\nScraping complete.\n")

    def view_aggregated_content(self):
        """Display all aggregated content in a dialog."""
        if not self.scraped_content:
            self.results_display.append("<b>Error:</b> No content to display. Please scrape websites first.")
            return

        dialog = ContentDialog("Aggregated Articles", self.scraped_content, self)
        dialog.exec_()

    def perform_topic_modeling(self):
        """Perform topic modeling on the scraped articles."""
        if not self.scraped_content:
            self.results_display.append("No articles to analyze. Please scrape websites first.")
            return
        articles = [article for source in self.scraped_content.values() for article in source]
        topics = AnalysisTools.topic_modeling(articles)
        self.results_display.append("\n".join(topics))

    def visualize_cooccurrence_graph(self):
        """Visualize a co-occurrence graph from the scraped articles."""
        if not self.scraped_content:
            self.results_display.append("No articles to analyze. Please scrape websites first.")
            return
        articles = [article for source in self.scraped_content.values() for article in source]
        graph = AnalysisTools.build_cooccurrence_graph(articles)
        AnalysisTools.visualize_graph(graph)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
