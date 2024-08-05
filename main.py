import sys
import os
import json
import importlib.util
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QLineEdit, QPushButton, QHBoxLayout, QFileDialog, QLabel, QTextEdit, QDialog, QDialogButtonBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, QPoint
from PyQt5.QtGui import QPixmap
import qrcode
from bs4 import BeautifulSoup

class PluginManager:
    def __init__(self, plugin_directory='plugins'):
        self.plugin_directory = plugin_directory
        self.plugins = []
        self.load_plugins()

    def load_plugins(self):
        if not os.path.exists(self.plugin_directory):
            print(f"Plugin directory '{self.plugin_directory}' does not exist. No plugins loaded.")
            return
        
        for folder_name in os.listdir(self.plugin_directory):
            folder_path = os.path.join(self.plugin_directory, folder_name)
            if os.path.isdir(folder_path):
                manifest_path = os.path.join(folder_path, 'manifest.json')
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            main_script = manifest.get('main', 'plugin.py')
                            plugin_path = os.path.join(folder_path, main_script)
                            self.load_plugin(plugin_path)
                    except Exception as e:
                        print(f"Error loading plugin from {manifest_path}: {e}")

    def load_plugin(self, plugin_path):
        try:
            spec = importlib.util.spec_from_file_location("plugin", plugin_path)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            if hasattr(plugin, 'on_load'):
                plugin.on_load()
            self.plugins.append(plugin)
        except Exception as e:
            print(f"Error loading plugin {plugin_path}: {e}")

    def trigger_event(self, event_name, *args, **kwargs):
        for plugin in self.plugins:
            if hasattr(plugin, event_name):
                try:
                    getattr(plugin, event_name)(*args, **kwargs)
                except Exception as e:
                    print(f"Error executing {event_name} in plugin {plugin}: {e}")


class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if type == QWebEnginePage.NavigationTypeLinkClicked:
            self.setUrl(url)
            return False
        return super().acceptNavigationRequest(url, type, isMainFrame)

class BrowserTab(QWidget):
    def __init__(self, plugin_manager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.layout = QVBoxLayout(self)
        
        # URL Bar and Buttons
        self.url_bar = QLineEdit(self)
        self.url_bar.setPlaceholderText('Enter URL or file path')
        self.url_bar.returnPressed.connect(self.load_content)
        
        self.back_button = QPushButton('<', self)
        self.back_button.clicked.connect(self.go_back)
        
        self.forward_button = QPushButton('>', self)
        self.forward_button.clicked.connect(self.go_forward)
        
        self.reload_button = QPushButton('Reload', self)
        self.reload_button.clicked.connect(self.reload_page)
        
        """self.close_button = QPushButton('Close', self)
        self.close_button.clicked.connect(self.close_browser)"""

        self.open_file_button = QPushButton('Open File', self)
        self.open_file_button.clicked.connect(self.open_file)

        self.qr_code_button = QPushButton('QR Code', self)
        self.qr_code_button.clicked.connect(self.generate_qr_code)

        self.save_page_button = QPushButton('Save Page', self)
        self.save_page_button.clicked.connect(self.save_page)

        self.view_source_button = QPushButton('View Source', self)
        self.view_source_button.clicked.connect(self.view_source)

        # Navigation Layout
        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.reload_button)
        nav_layout.addWidget(self.url_bar)
        """nav_layout.addWidget(self.close_button)"""
        nav_layout.addWidget(self.open_file_button)
        nav_layout.addWidget(self.qr_code_button)
        nav_layout.addWidget(self.save_page_button)
        nav_layout.addWidget(self.view_source_button)
        
        self.layout.addLayout(nav_layout)
        
        # Web Engine View and Content View
        self.browser = QWebEngineView(self)
        self.browser.setPage(CustomWebEnginePage(self.browser))
        self.text_view = QTextEdit(self)
        self.text_view.setReadOnly(True)
        self.image_view = QLabel(self)
        self.image_view.setAlignment(Qt.AlignCenter)
        
        self.layout.addWidget(self.browser)
        self.layout.addWidget(self.text_view)
        self.layout.addWidget(self.image_view)

        self.browser.setVisible(True)
        self.text_view.setVisible(False)
        self.image_view.setVisible(False)

        self.browser.setUrl(QUrl('https://www.google.com'))
        self.browser.urlChanged.connect(self.on_url_change)

    def load_content(self):
        path = self.url_bar.text()
        if os.path.exists(path):
            # ローカルファイルのパスを処理
            _, extension = os.path.splitext(path)
            extension = extension.lower()

            if extension in ['.html', '.htm']:
                self.display_html(path)
            elif extension in ['.txt']:
                self.display_text(path)
            elif extension in ['.jpg', '.jpeg', '.png', '.gif']:
                self.display_image(path)
            else:
                self.display_unsupported()
        else:
            # URLとして処理
            self.load_url(path)
    
    def load_url(self, url):
        if not url.startswith('http') and not url.startswith('ginga::'):
            url = 'http://' + url
        if url.startswith('http://') or url.startswith('https://'):
            self.browser.setUrl(QUrl(url))
            self.browser.setVisible(True)
            self.text_view.setVisible(False)
            self.image_view.setVisible(False)
        elif url.startswith('ginga::'):
            file_path = "http://localhost:8264/" + url[7:]
            self.url_bar.setText(file_path)
            self.load_content()
            self.url_bar.setText("ginga::" + url[7:])

    def display_html(self, file_path):
        self.browser.setUrl(QUrl.fromLocalFile(file_path))
        self.browser.setVisible(True)
        self.text_view.setVisible(False)
        self.image_view.setVisible(False)
    
    def display_text(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        self.text_view.setPlainText(text)
        self.text_view.setVisible(True)
        self.browser.setVisible(False)
        self.image_view.setVisible(False)
    
    def display_image(self, file_path):
        pixmap = QPixmap(file_path)
        self.image_view.setPixmap(pixmap)
        self.image_view.setVisible(True)
        self.browser.setVisible(False)
        self.text_view.setVisible(False)
    
    def display_unsupported(self):
        self.text_view.setPlainText("サポートされていないファイル形式です。")
        self.text_view.setVisible(True)
        self.browser.setVisible(False)
        self.image_view.setVisible(False)
    
    def go_back(self):
        if self.browser.isVisible():
            self.browser.back()
    
    def go_forward(self):
        if self.browser.isVisible():
            self.browser.forward()
    
    def reload_page(self):
        if self.browser.isVisible():
            self.browser.reload()
    
    def close_browser(self):
        QApplication.instance().quit()
    
    def on_url_change(self, qurl):
        url = qurl.toString()
        self.url_bar.setText(url)
        self.plugin_manager.trigger_event('on_url_change', url)

    def open_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "HTML Files (*.html);;Text Files (*.txt);;Image Files (*.jpg *.jpeg *.png *.gif);;All Files (*)", options=options)
        if file_path:
            self.url_bar.setText(file_path)
            self.load_content()

    def generate_qr_code(self):
        content = self.url_bar.text()
        if content:
            # QRコードを生成
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(content)
            qr.make(fit=True)

            img = qr.make_image(fill='black', back_color='white')
            img.save('qr_code.png')

            # QRコードを表示
            qr_dialog = QDialog(self)
            qr_dialog.setWindowTitle("QR Code")
            qr_layout = QVBoxLayout(qr_dialog)
            qr_label = QLabel()
            qr_pixmap = QPixmap('qr_code.png')
            qr_label.setPixmap(qr_pixmap)
            qr_layout.addWidget(qr_label)
            qr_dialog.setLayout(qr_layout)
            qr_dialog.exec_()

    def save_page(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Page As", "", "HTML Files (*.html);;All Files (*)", options=options)
        if file_path:
            self.browser.page().save(file_path, QWebEnginePage.CompleteHtmlSaveFormat)

    def view_source(self):
        self.browser.page().toHtml(self.show_source)

    def show_source(self, html):
        self.text_view.setPlainText(html)
        self.text_view.setVisible(True)
        self.browser.setVisible(False)
        self.image_view.setVisible(False)

    def validate_content(self):
        self.browser.page().toHtml(self.check_html)

    def check_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        errors = []
        
        # シンプルなバリデーションルール
        if soup.title is None:
            errors.append("No <title> tag found.")
        
        if not soup.find_all('h1'):
            errors.append("No <h1> tags found.")

        if not soup.find_all('meta', {'name': 'description'}):
            errors.append("No <meta name='description'> tags found.")
        
        if errors:
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle("Validation Results")
            layout = QVBoxLayout()
            error_text = "\n".join(errors)
            error_label = QLabel(error_text)
            layout.addWidget(error_label)
            error_dialog.setLayout(layout)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(error_dialog.accept)
            layout.addWidget(button_box)
            error_dialog.exec_()
        else:
            success_dialog = QDialog(self)
            success_dialog.setWindowTitle("Validation Results")
            layout = QVBoxLayout()
            success_label = QLabel("No major issues found.")
            layout.addWidget(success_label)
            success_dialog.setLayout(layout)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(success_dialog.accept)
            layout.addWidget(button_box)
            success_dialog.exec_()

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Python Browser with Plugin Support and QR/Validation')
        self.setGeometry(100, 100, 1200, 800)

        # Initialize PluginManager
        self.plugin_manager = PluginManager()
        
        # Remove the standard window frame and close button
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title bar layout
        title_bar = QWidget()
        title_bar_layout = QHBoxLayout(title_bar)
        nameee = QLabel('Ginga Browser')
        title_bar_layout.addWidget(nameee)
        
        # Title bar buttons
        self.minimize_button = QPushButton('-', self)
        self.minimize_button.setFixedWidth(40)
        self.minimize_button.clicked.connect(self.showMinimized)
        
        self.maximize_button = QPushButton('□', self)
        self.maximize_button.setFixedWidth(40)
        self.maximize_button.clicked.connect(self.toggle_maximize_restore)
        
        self.close_button = QPushButton('X', self)
        self.close_button.setFixedWidth(40)
        self.close_button.clicked.connect(self.close)

        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.minimize_button)
        title_bar_layout.addWidget(self.maximize_button)
        title_bar_layout.addWidget(self.close_button)

        layout.addWidget(title_bar)
        
        # Set up mouse event tracking for window movement
        self.old_position = None
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.setSpacing(0)
        title_bar.mousePressEvent = self.start_move
        title_bar.mouseMoveEvent = self.move_window

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tabs)
        
        # Adding first tab
        self.add_new_tab(QUrl('https://www.google.com'), 'New Tab')
        
        # New tab button
        self.new_tab_button = QPushButton('+', self)
        self.new_tab_button.setFixedWidth(40)
        self.new_tab_button.clicked.connect(self.add_blank_tab)
        self.tabs.setCornerWidget(self.new_tab_button)
        
        # Load custom stylesheet
        self.load_stylesheet()

    def add_new_tab(self, url, label):
        new_tab = BrowserTab(self.plugin_manager)
        new_tab.browser.setUrl(url)
        index = self.tabs.addTab(new_tab, label)
        self.tabs.setCurrentIndex(index)
        new_tab.url_bar.setText(url.toString())
        new_tab.browser.titleChanged.connect(lambda title: self.set_tab_title(index, title))
        new_tab.browser.urlChanged.connect(lambda url: self.set_tab_url(index, url))

    def add_blank_tab(self):
        self.add_new_tab(QUrl('https://www.google.com'), 'New Tab')
    
    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
    
    def set_tab_title(self, index, title):
        self.tabs.setTabText(index, title)
    
    def set_tab_url(self, index, url):
        current_tab = self.tabs.widget(index)
        if current_tab:
            current_tab.url_bar.setText(url.toString())

    def load_stylesheet(self):
        try:
            with open('style.css', 'r', encoding='utf-8') as f:
                style = f.read()
                self.setStyleSheet(style)
        except FileNotFoundError:
            print("CSS file not found. Skipping stylesheet loading.")

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText('□')
        else:
            self.showMaximized()
            self.maximize_button.setText('❐')

    def start_move(self, event):
        if event.button() == Qt.LeftButton:
            self.old_position = event.globalPos()
            event.accept()
        
    def move_window(self, event):
        if self.old_position is not None:
            delta = QPoint(event.globalPos() - self.old_position)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_position = event.globalPos()
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Browser()
    window.show()
    sys.exit(app.exec_())
