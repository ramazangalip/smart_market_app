# main_app.py

import sys
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QMainWindow, QStackedWidget, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

# Diğer dosyalardan import'lar
from db_model import Kullanici, Session 
from auth_screen import LoginRegisterDialog
# Rol tabanlı view'leri views klasöründe oluşturduğunuzu varsayıyoruz
from views.musteri_view import MusteriView 
from views.calisan_view import CalisanView
from views.yonetici_view import YoneticiView

class AkilliMarketMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Akıllı Market Sistemi")
        self.setGeometry(100, 100, 1000, 700)
        self.session = Session()
        self.current_user = None

        # Ana widget ve düzen
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Sayfa geçişlerini yönetecek Stacked Widget
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # Giriş ekranını göster
        self.show_login_dialog()

    def show_login_dialog(self):
        # Önceki içeriği temizle
        for i in range(self.stacked_widget.count()):
            self.stacked_widget.widget(i).deleteLater()
        
        login_dialog = LoginRegisterDialog(self)
        login_dialog.login_success.connect(self.handle_login_success)
        
        # Uygulama başlangıcında modal olarak aç
        if login_dialog.exec_() != QDialog.Accepted:
            # Kullanıcı kapatırsa veya iptal ederse uygulamayı kapat
            QApplication.quit()

    def handle_login_success(self, kullanici):
        self.current_user = kullanici
        self.setup_main_view(kullanici.rol)

    def setup_main_view(self, rol):
        self.setWindowTitle(f"Akıllı Market Sistemi - {rol.capitalize()}")
        
        # Rol tabanlı sayfa oluşturma
        if rol == 'musteri':
            self.view = MusteriView(self.session, self.current_user)
        elif rol == 'calisan':
            self.view = CalisanView(self.session, self.current_user)
        elif rol == 'yonetici':
            self.view = YoneticiView(self.session, self.current_user)
        else:
            # Tanımlanmayan rol
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
    window = AkilliMarketMainWindow()
    window.show()
    sys.exit(app.exec_())