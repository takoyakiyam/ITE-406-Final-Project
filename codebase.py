import sys
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextEdit, QCheckBox, QLabel, QDialog,
    QLineEdit, QTabWidget, QGroupBox
)
from datetime import datetime

# Scraping functions
def scrape_foxnews():
    url = "https://www.foxnews.com/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    return [h3.get_text(strip=True) for h3 in soup.find_all('h3')]

def scrape_philstar():
    url = "https://www.philstar.com/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    return [h2.get_text(strip=True) for h2 in soup.find_all('h2')]

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("News Scraper with Improved Layout")
        self.resize(1000, 700)

        # Main central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Greeting and date
        self.greeting_label = QLabel("<h2>Greetings, User!</h2>")
        current_date = datetime.now().strftime("%B %d, %Y")
        self.date_label = QLabel(f"Today's Date is <b> {current_date}</b>")
        self.main_layout.addWidget(self.greeting_label)
        self.main_layout.addWidget(self.date_label)

        # Top label
        self.label = QLabel("<h3>Select Websites to Scrape</h3>")
        self.main_layout.addWidget(self.label)

        # Website selection area
        self.website_groupbox = QGroupBox("Websites")
        self.website_layout = QVBoxLayout()
        self.checkbox_foxnews = QCheckBox("Fox News")
        self.checkbox_philstar = QCheckBox("Philstar")
        self.checkbox_manilaTimes = QCheckBox("Manila Times")
        self.checkbox_rappler = QCheckBox("Rappler")
        self.website_layout.addWidget(self.checkbox_foxnews)
        self.website_layout.addWidget(self.checkbox_philstar)
        self.website_layout.addWidget(self.checkbox_manilaTimes)
        self.website_layout.addWidget(self.checkbox_rappler)
        self.website_groupbox.setLayout(self.website_layout)
        self.main_layout.addWidget(self.website_groupbox)

        # Action buttons
        self.action_buttons_layout = QHBoxLayout()
        self.check_all_button = QPushButton("Select All Websites")
        self.check_all_button.clicked.connect(self.toggle_select_all)
        self.scrape_button = QPushButton("Scrape Selected Websites")
        self.scrape_button.clicked.connect(self.scrape_websites)
        self.view_aggregated_button = QPushButton("View Aggregated Articles")
        self.view_aggregated_button.clicked.connect(self.view_aggregated_content)
        self.action_buttons_layout.addWidget(self.check_all_button)
        self.action_buttons_layout.addWidget(self.scrape_button)
        self.action_buttons_layout.addWidget(self.view_aggregated_button)
        self.main_layout.addLayout(self.action_buttons_layout)

        # Results display
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("Scraped results will appear here...")
        self.main_layout.addWidget(self.results_display, stretch=2)

        # State tracking
        self.all_selected = False
        self.scraped_content = {}
        
    def toggle_select_all(self):
        """Toggle all checkboxes."""
        self.all_selected = not self.all_selected
        state = self.all_selected
        for checkbox in [self.checkbox_foxnews, self.checkbox_philstar, self.checkbox_manilaTimes, self.checkbox_rappler]:
            checkbox.setChecked(state)
        self.check_all_button.setText("Unselect All Websites" if state else "Select All Websites")

    def scrape_websites(self):
        """Scrape selected websites and display results."""
        self.results_display.clear()
        if not any([
            self.checkbox_foxnews.isChecked(),
            self.checkbox_philstar.isChecked(),
            self.checkbox_manilaTimes.isChecked(),
            self.checkbox_rappler.isChecked()
        ]):
            self.results_display.append("<b>Error:</b> No website selected. Please choose a website.")
            return

        self.scraped_content = {}
        websites = [
            ("Fox News", self.checkbox_foxnews.isChecked(), scrape_foxnews),
            ("Philstar", self.checkbox_philstar.isChecked(), scrape_philstar),
            ("Manila Times", self.checkbox_manilaTimes.isChecked(), scrape_manilaTimes),
            ("Rappler", self.checkbox_rappler.isChecked(), scrape_rappler),
        ]

        self.results_display.append(f"<b>Scraping articles...</b>")

        for name, is_checked, scraper in websites:
            if is_checked:
                try:
                    self.scraped_content[name] = scraper()
                    self.results_display.append(f"{name}: {len(self.scraped_content[name])} articles scraped.")
                except Exception as e:
                    self.results_display.append(f"{name}: Failed to scrape. ({str(e)})")

        self.results_display.append("\n<b>Scraping complete.</b>")

    def view_aggregated_content(self):
        """Display aggregated articles."""
        if not self.scraped_content:
            self.results_display.append("<b>Error:</b> No content to display. Scrape websites first.")
            return

        dialog = ContentDialog("Aggregated Articles", self.scraped_content, self)
        dialog.exec_()

class ContentDialog(QDialog):
    def __init__(self, title, aggregated_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)

        # Main layout
        self.aggregated_content = aggregated_content
        self.layout = QVBoxLayout(self)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Type to search articles...")
        self.search_button = QPushButton("🔍")
        self.search_button.clicked.connect(self.perform_search)
        self.clear_button = QPushButton("🔄")
        self.clear_button.clicked.connect(self.clear_search)
        search_layout.addWidget(self.search_field)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.clear_button)
        self.layout.addLayout(search_layout)

        # Tab view for content
        self.tabs = QTabWidget()

        # Create "All Articles" tab first
        self.all_articles_tab = QWidget()
        self.all_articles_layout = QVBoxLayout(self.all_articles_tab)
        self.all_articles_display = QTextEdit()
        self.all_articles_display.setReadOnly(True)

        # Combine all articles into one list
        self.combined_articles = []
        for articles in aggregated_content.values():
            self.combined_articles.extend(articles)

        # Display all articles in the "All Articles" tab
        self.all_articles_display.setText("\n".join(self.combined_articles))
        self.all_articles_layout.addWidget(self.all_articles_display)

        # Add "All Articles" tab as the first tab
        self.tabs.addTab(self.all_articles_tab, "All Articles")

        # Add source-specific tabs
        self.source_displays = {}
        for source, articles in aggregated_content.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            text_display = QTextEdit()
            text_display.setReadOnly(True)
            text_display.setText("\n".join(articles))
            tab_layout.addWidget(text_display)
            self.tabs.addTab(tab, source)
            self.source_displays[source] = text_display

        # Add tabs to layout
        self.layout.addWidget(self.tabs)

    def perform_search(self):
        """Search articles and update the display."""
        query = self.search_field.text().strip().lower()
        if not query:
            return

        # Determine current tab
        current_tab_index = self.tabs.currentIndex()
        current_tab_name = self.tabs.tabText(current_tab_index)

        no_results_message = f"<i>There's no articles matching '{query}' for today.</i>"

        if current_tab_name == "All Articles":
            # Filter all articles
            filtered = [article for article in self.combined_articles if query in article.lower()]
            if filtered:
                self.all_articles_display.setText("\n".join(filtered))
            else:
                self.all_articles_display.setText(no_results_message)
        else:
            # Filter articles for the specific source
            source_articles = self.aggregated_content.get(current_tab_name, [])
            filtered = [article for article in source_articles if query in article.lower()]
            if current_tab_name in self.source_displays:
                if filtered:
                    self.source_displays[current_tab_name].setText("\n".join(filtered))
                else:
                    self.source_displays[current_tab_name].setText(no_results_message)


    def clear_search(self):
        """Clear search and reset all tabs to original content."""
        self.search_field.clear()

        # Reset "All Articles" tab
        self.all_articles_display.setText("\n".join(self.combined_articles))

        # Reset each source-specific tab
        for source, articles in self.aggregated_content.items():
            if source in self.source_displays:
                self.source_displays[source].setText("\n".join(articles))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
