from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox,QWidget
from PyQt5.QtCore import Qt, pyqtSignal


from db_model import Kullanici, Session,CalisanBilgisi

class LoginRegisterDialog(QDialog):
    login_success = pyqtSignal(Kullanici) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Giriş Yap / Kayıt Ol")
        self.setFixedSize(400, 300)
        self.session = Session()

        self.stack_layout = QVBoxLayout(self) # Ana düzen

        # Stil uygulaması için ana widget'a padding ekleyelim
        self.setStyleSheet("padding: 10px;")

        self.login_widget = self.create_login_widget()
        self.register_widget = self.create_register_widget()
        
        # Başlangıçta sadece giriş ekranını göster
        self.stack_layout.addWidget(self.login_widget)

    def create_login_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form_layout = QFormLayout()

        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText("Kullanıcı Adınız") # Placeholder eklendi
        self.login_pass = QLineEdit(echoMode=QLineEdit.Password)
        self.login_pass.setPlaceholderText("Şifreniz") # Placeholder eklendi
        
        # Stilin uygulanması için bir özel Nesne Adı gerekmez, genel QPushButton stili uygulanacaktır.
        self.login_btn = QPushButton("Giriş Yap")
        self.login_btn.setStyleSheet("padding: 10px; font-weight: bold;") # Vurgu için padding eklendi
        
        self.switch_to_register_btn = QPushButton("Hesabın yok mu? Kayıt Ol")
        self.switch_to_register_btn.setStyleSheet("background-color: #6c757d; border: 1px solid #6c757d; color: white;") # İkincil stil
        
        form_layout.addRow("Kullanıcı Adı:", self.login_user)
        form_layout.addRow("Şifre:", self.login_pass)
        
        layout.addLayout(form_layout)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.switch_to_register_btn)

        self.login_btn.clicked.connect(self.handle_login)
        self.switch_to_register_btn.clicked.connect(lambda: self.switch_view(self.register_widget, self.login_widget))
        return widget
        
    def create_register_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form_layout = QFormLayout()

        self.register_user = QLineEdit()
        self.register_user.setPlaceholderText("Kullanıcı Adı Seçin")
        self.register_pass = QLineEdit(echoMode=QLineEdit.Password)
        self.register_pass.setPlaceholderText("Şifre Belirleyin")
        self.register_role = QComboBox()
        self.register_role.addItems(['musteri', 'calisan', 'yonetici']) # Rolleri ekle
        
        self.register_btn = QPushButton("Kayıt Ol")
        self.register_btn.setStyleSheet("background-color: #4CAF50; border: 1px solid #4CAF50; color: white; padding: 10px; font-weight: bold;") # Başarı rengi
        
        self.switch_to_login_btn = QPushButton("Zaten hesabım var? Giriş Yap")
        self.switch_to_login_btn.setStyleSheet("background-color: #6c757d; border: 1px solid #6c757d; color: white;") # İkincil stil
        
        form_layout.addRow("Kullanıcı Adı:", self.register_user)
        form_layout.addRow("Şifre:", self.register_pass)
        form_layout.addRow("Rol Seçin:", self.register_role)
        
        layout.addLayout(form_layout)
        layout.addWidget(self.register_btn)
        layout.addWidget(self.switch_to_login_btn)
        widget.hide() 

        self.register_btn.clicked.connect(self.handle_register)
        self.switch_to_login_btn.clicked.connect(lambda: self.switch_view(self.login_widget, self.register_widget))
        return widget

    def switch_view(self, show_widget, hide_widget):
        
        self.stack_layout.removeWidget(hide_widget)
        hide_widget.hide()
        self.stack_layout.addWidget(show_widget)
        show_widget.show()

    def handle_login(self):
        k_adi = self.login_user.text().strip()
        sifre = self.login_pass.text().strip()

        kullanici = self.session.query(Kullanici).filter_by(kullanici_adi=k_adi).first()

        if kullanici and kullanici.check_sifre(sifre):
            QMessageBox.information(self, "Başarılı", f"Hoş geldiniz, {kullanici.rol}!")
            self.login_success.emit(kullanici) 
            self.accept()
        else:
            QMessageBox.critical(self, "Hata", "Kullanıcı adı veya şifre hatalı.")

    def handle_register(self):
        k_adi = self.register_user.text().strip()
        sifre = self.register_pass.text().strip()
        rol = self.register_role.currentText()

        if not k_adi or not sifre:
            QMessageBox.warning(self, "Uyarı", "Kullanıcı adı ve şifre boş bırakılamaz.")
            return

        if self.session.query(Kullanici).filter_by(kullanici_adi=k_adi).first():
            QMessageBox.warning(self, "Uyarı", "Bu kullanıcı adı zaten alınmış.")
            return

        try:
            yeni_kullanici = Kullanici(kullanici_adi=k_adi, rol=rol)
            yeni_kullanici.set_sifre(sifre)
            self.session.add(yeni_kullanici)

            
            if rol in ['calisan', 'yonetici']:
                self.session.flush() 
                calisan_bilgi = CalisanBilgisi(kullanici_id=yeni_kullanici.id, pozisyon=rol)
                self.session.add(calisan_bilgi)

            self.session.commit()
            QMessageBox.information(self, "Başarılı", f"Kayıt başarılı. Rol: {rol}")
            self.switch_view(self.login_widget, self.register_widget) # Giriş ekranına dön
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Kayıt sırasında bir hata oluştu: {e}")

    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)