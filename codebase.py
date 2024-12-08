import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QCheckBox, QLabel, QDialog, QLineEdit, QHBoxLayout)

# Scraping functions
def scrape_foxnews():
    url = "https://www.foxnews.com/"
    response = requests.get(url, timeout=10)  # Timeout to prevent hanging
    response.raise_for_status()  # Raise HTTPError for bad responses
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

# Pop-up dialog to display scraped content with search functionality
class ContentDialog(QDialog):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)
        self.content = content

        # Layouts
        main_layout = QVBoxLayout(self)
        search_layout = QHBoxLayout()

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
        self.text_display.setText("\n".join(self.content))

        # Add layouts and widgets
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.text_display)

    def search_content(self):
        """Search for a keyword and refresh content to show only matching lines."""
        keyword = self.search_input.text().strip()
        if not keyword:
            # If search bar is empty, display all content
            self.text_display.setText("\n".join(self.content))
            return

        # Filter matching lines
        matching_lines = [
            line for line in self.content if keyword.lower() in line.lower()
        ]

        if matching_lines:
            self.text_display.setText("\n".join(matching_lines))
        else:
            self.text_display.setText("No matching content found.")
            
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fine-Tunable News Scraper")
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

        # Add a button to toggle checkbox selection
        self.check_all_button = QPushButton("Select All Websites")
        self.check_all_button.clicked.connect(self.toggle_select_all)
        self.layout.addWidget(self.check_all_button)

        # Add a button to start scraping
        self.scrape_button = QPushButton("Scrape Selected Websites")
        self.scrape_button.clicked.connect(self.scrape_websites)
        self.layout.addWidget(self.scrape_button)

        # Add a button to view aggregated articles
        self.view_aggregated_button = QPushButton("View Aggregated Articles")
        self.view_aggregated_button.clicked.connect(self.view_aggregated_content)
        self.layout.addWidget(self.view_aggregated_button)

        # Add a text area to display results
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.layout.addWidget(self.results_display)

        # Start in fullscreen mode
        self.showFullScreen()

        # Track the toggle state of the "Select All Websites" button
        self.all_selected = False

        # Storage for scraped content
        self.scraped_content = {}

    def toggle_select_all(self):
        """Toggle between selecting and unselecting all checkboxes."""
        self.all_selected = not self.all_selected
        new_state = self.all_selected

        # Set the state of all checkboxes
        self.checkbox_foxnews.setChecked(new_state)
        self.checkbox_philstar.setChecked(new_state)
        self.checkbox_manilaTimes.setChecked(new_state)
        self.checkbox_rappler.setChecked(new_state)

        # Update the button label
        self.check_all_button.setText("Unselect All Websites" if new_state else "Select All Websites")

    def scrape_websites(self):
        """Scrape selected websites and display results."""
        # Clear the results display before starting
        self.results_display.clear()

        # Check if at least one website is selected
        if not any([
            self.checkbox_foxnews.isChecked(),
            self.checkbox_philstar.isChecked(),
            self.checkbox_manilaTimes.isChecked(),
            self.checkbox_rappler.isChecked()
        ]):
            self.results_display.append("<b>Error:</b> No website selected for scraping. Please select at least one website.")
            return

        # Get the current date in a human-readable format
        current_date = datetime.now().strftime("These are the articles for %B %d, %Y.")
        self.results_display.append(f"<b>{current_date}</b>\n")

        # Mapping of checkboxes to scraping functions
        websites = [
            ("Fox News", self.checkbox_foxnews.isChecked(), scrape_foxnews),
            ("Philstar", self.checkbox_philstar.isChecked(), scrape_philstar),
            ("Manila Times", self.checkbox_manilaTimes.isChecked(), scrape_manilaTimes),
            ("Rappler", self.checkbox_rappler.isChecked(), scrape_rappler),
        ]

        # Reset scraped content storage
        self.scraped_content = {}

        # Scrape selected websites
        for name, is_checked, scrape_function in websites:
            if is_checked:
                try:
                    self.scraped_content[name] = scrape_function()
                    self.results_display.append(f"{name}: {len(self.scraped_content[name])} articles scraped.")
                except requests.exceptions.RequestException as e:
                    self.results_display.append(f"{name}: Failed to scrape (Network Error: {e}).")
                except Exception as e:
                    self.results_display.append(f"{name}: Failed to scrape (Error: {e}).")

        self.results_display.append("\nScraping complete.\n")

    def view_aggregated_content(self):
        """Display all aggregated content in a dialog."""
        if not self.scraped_content:
            self.results_display.append("<b>Error:</b> No content to display. Please scrape websites first.")
            return

        dialog = ContentDialog("Aggregated Articles", self.scraped_content, self)
        dialog.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
