# dialogs/urun_ekle_dialog.py

from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QMessageBox
from db_model import Urun # Urun modelini db_model dosyasından import edin
from sqlalchemy.exc import IntegrityError

class UrunEkleDuzenleDialog(QDialog):
    def __init__(self, session, urun=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.urun = urun # Düzenleme modundaysa mevcut Ürün nesnesi
        
        if self.urun:
            self.setWindowTitle("Ürün Düzenle")
        else:
            self.setWindowTitle("Yeni Ürün Ekle")
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.isim_input = QLineEdit()
        self.barkod_input = QLineEdit()
        self.stok_input = QLineEdit()
        self.fiyat_input = QLineEdit()

        # Eğer düzenleme modu ise, mevcut verileri yükle
        if self.urun:
            self.isim_input.setText(self.urun.isim)
            self.barkod_input.setText(self.urun.barkod)
            self.stok_input.setText(str(self.urun.stok))
            self.fiyat_input.setText(str(self.urun.fiyat))
            # Barkodu düzenlemeyi engelle (genellikle barkod birincil anahtar gibi davranır)
            self.barkod_input.setReadOnly(True) 

        layout.addRow("Ürün Adı:", self.isim_input)
        layout.addRow("Barkod:", self.barkod_input)
        layout.addRow("Stok:", self.stok_input)
        layout.addRow("Fiyat (TL):", self.fiyat_input)

        self.save_btn = QPushButton("Kaydet")
        self.save_btn.clicked.connect(self.save_urun)
        layout.addWidget(self.save_btn)
        
    def save_urun(self):
        isim = self.isim_input.text().strip()
        barkod = self.barkod_input.text().strip()
        
        try:
            stok = int(self.stok_input.text())
            fiyat = float(self.fiyat_input.text())
        except ValueError:
            QMessageBox.critical(self, "Hata", "Stok ve Fiyat geçerli sayı olmalıdır.")
            return

        if not isim or not barkod:
            QMessageBox.warning(self, "Eksik Bilgi", "Ürün Adı ve Barkod boş bırakılamaz.")
            return
            
        try:
            if self.urun:
                # Düzenleme Modu
                self.urun.isim = isim
                self.urun.stok = stok
                self.urun.fiyat = fiyat
                QMessageBox.information(self, "Başarılı", f"'{isim}' ürünü güncellendi.")
            else:
                # Yeni Ekleme Modu
                yeni_urun = Urun(isim=isim, barkod=barkod, stok=stok, fiyat=fiyat)
                self.session.add(yeni_urun)
                QMessageBox.information(self, "Başarılı", f"'{isim}' ürünü başarıyla eklendi.")
            
            self.session.commit()
            self.accept()
            
        except IntegrityError:
            self.session.rollback()
            QMessageBox.critical(self, "Veritabanı Hatası", "Bu barkod zaten sistemde kayıtlı.")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"İşlem sırasında bir hata oluştu: {e}")