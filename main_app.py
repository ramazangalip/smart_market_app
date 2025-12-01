import sys
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QMainWindow, QStackedWidget, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

from db_model import Kullanici, Session 
from auth_screen import LoginRegisterDialog

from views.musteri_view import MusteriView 
from views.calisan_view import CalisanView
from views.yonetici_view import YoneticiView

# --- QT STİL SAYFASI TANIMI (MODERN TEMA) ---

PRIMARY_COLOR = "#007ACC"  # Mavi (Modern vurgu)
SECONDARY_COLOR = "#4CAF50" # Yeşil (Başarı/Onay)
BACKGROUND_COLOR = "#F0F0F0" # Açık gri
TEXT_COLOR = "#333333"

style_sheet = f"""
/* Genel Pencere ve Zemin */
QWidget {{
    background-color: {BACKGROUND_COLOR};
    color: {TEXT_COLOR};
    font-family: Arial, sans-serif;
    font-size: 10pt;
}}

/* Başlıklar ve Etiketler */
QLabel {{
    color: {TEXT_COLOR};
    padding: 2px;
}}

/* Butonlar */
QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: 1px solid {PRIMARY_COLOR};
    border-radius: 5px; /* Köşeleri yuvarla */
    padding: 8px 15px;
    margin: 2px;
}}

/* Buton Etkileşimi (Mouse üzerine gelince) */
QPushButton:hover {{
    background-color: #005f99; /* Daha koyu mavi */
    border: 1px solid #005f99;
}}

/* QLineEdit ve QTableWidget (Giriş Alanları) */
QLineEdit, QTableWidget, QGroupBox, QComboBox {{
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 5px;
    background-color: white;
}}

/* QTableWidget Başlıkları (Header) */
QHeaderView::section {{
    background-color: #DDDDDD;
    color: {TEXT_COLOR};
    padding: 6px;
    border: 1px solid #CCCCCC;
    font-weight: bold;
}}

/* Navigasyon Butonları (Side Menu) */
/* Nesne Adı "nav_btn" olan butonlar için özel stil */
QPushButton#nav_btn {{
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 10px 15px;
    margin: 5px 0;
    color: {TEXT_COLOR};
}}

QPushButton#nav_btn:hover {{
    background-color: #E0E0E0;
}}

/* ÖNEMLİ: Seçili olan menü butonu için */
QPushButton#nav_btn:checked {{
    background-color: #D0D0D0;
    border-left: 5px solid {PRIMARY_COLOR};
    font-weight: bold;
}}

/* Dashboard Kartları gibi özel vurgular için */
h4 {{
    color: {PRIMARY_COLOR};
}}
"""

class AkilliMarketMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Akıllı Market Sistemi")
        self.setGeometry(100, 100, 1000, 700)
        self.session = Session()
        self.current_user = None
        
        # Bu kısım, stili uygulamadan sonra çalışmalıdır
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.show_login_dialog()

    def show_login_dialog(self):
 
        for i in range(self.stacked_widget.count()):
            self.stacked_widget.widget(i).deleteLater()
        
        login_dialog = LoginRegisterDialog(self)
        login_dialog.login_success.connect(self.handle_login_success)
        
        
        if login_dialog.exec_() != QDialog.Accepted:
            
            QApplication.quit()

    def handle_login_success(self, kullanici):
        self.current_user = kullanici
        self.setup_main_view(kullanici.rol)

    def setup_main_view(self, rol):
        self.setWindowTitle(f"Akıllı Market Sistemi - {rol.capitalize()}")
        
        
        if rol == 'musteri':
            self.view = MusteriView(self.session, self.current_user)
        elif rol == 'calisan':
            self.view = CalisanView(self.session, self.current_user)
        elif rol == 'yonetici':
            self.view = YoneticiView(self.session, self.current_user)
        else:
            
            QMessageBox.critical(self, "Hata", "Geçersiz Kullanıcı Rolü!")
            QApplication.quit()
            return
            
        self.stacked_widget.addWidget(self.view)
        self.stacked_widget.setCurrentWidget(self.view)

    def closeEvent(self, event):
        self.session.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # --- STİL UYGULAMASI ---
    app.setStyleSheet(style_sheet) 
    
    window = AkilliMarketMainWindow()
    window.show()
    sys.exit(app.exec_())