from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QStackedWidget, QHeaderView, QLineEdit, QMessageBox, QWidget as QBtnWidget, QHBoxLayout as QBtnLayout
from PyQt5.QtCore import Qt, pyqtSignal, QTimer 
from sqlalchemy.orm import joinedload
from sqlalchemy import func 
from db_model import Urun, Siparis, Kullanici, SiparisDetay
from datetime import datetime
import random 

class MusteriView(QWidget):
    bildirim_geldi = pyqtSignal(int)

    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.siparis_sepetic = {} 
        self.bildirimler = [] 
        self.bildirim_sayaci = 0 
        self.bildirilen_urunler = set() # YENİ: Bildirimi gönderilen ürün ID'lerini tutar
        
        self.setup_ui()
        self.start_bildirim_kontrol_timer()

    def start_bildirim_kontrol_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_urun_bildirimleri)
        self.timer.start(5000) # Her 5 saniyede bir kontrol et

    def check_urun_bildirimleri(self):
        try:
            urunler = self.session.query(Urun).filter(Urun.stok > 0).all()
            yeni_bildirim_sayisi = 0
            
            for urun in urunler:
                # Sadece stoğu kritik seviyede (1-10 arası) olan ürünler için bildirim gönder
                if urun.stok > 0 and urun.stok <= 10:
                    
                    # Bu ürün daha önce bildirilmediyse VE stoğu belli bir eşiğin altındaysa
                    if urun.id not in self.bildirilen_urunler:
                        
                        self.bildirimler.append(f"📦 STOK GİRİŞİ: {urun.isim} (Mevcut Stok: {urun.stok})")
                        yeni_bildirim_sayisi += 1
                        self.bildirilen_urunler.add(urun.id) # Bildirildi olarak işaretle

                # Eğer ürünün stoğu normale dönerse (örnek 10'un üstüne çıkarsa)
                elif urun.stok > 10 and urun.id in self.bildirilen_urunler:
                    # Normal seviyeye döndüğü için listeden çıkarılabilir
                    self.bildirilen_urunler.discard(urun.id)
            
            if yeni_bildirim_sayisi > 0:
                self.bildirim_sayaci += yeni_bildirim_sayisi
                QMessageBox.information(self, "Yeni Bildirim", f"{yeni_bildirim_sayisi} yeni stok bildirimi var!")
                
                self.btn_bildirimler.setText(f"🔔 Bildirimler ({self.bildirim_sayaci})")
                
                if self.stacked_content.currentWidget() == self.bildirimler_page:
                    self.load_bildirimler()

        except Exception as e:
            print(f"Bildirim kontrol hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Bildirim kontrol hatası: {e}")


    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- Sol Menü (Navigasyon) ---
        menu_widget = QWidget()
        menu_layout = QVBoxLayout(menu_widget)
        
        self.btn_dashboard = QPushButton("🏠 Dashboard")
        self.btn_dashboard.setObjectName("nav_btn") 
        
        self.btn_urunler = QPushButton("🛒 Ürünler ve Sipariş")
        self.btn_urunler.setObjectName("nav_btn") 
        
        self.btn_siparislerim = QPushButton("📄 Siparişlerim")
        self.btn_siparislerim.setObjectName("nav_btn") 
        
        self.btn_odeme = QPushButton("💳 Ödeme (Sepet)")
        self.btn_odeme.setObjectName("nav_btn") 
        
        self.btn_bildirimler = QPushButton("🔔 Bildirimler") # YENİ BUTON
        self.btn_bildirimler.setObjectName("nav_btn") # YENİ BUTON

        menu_layout.addWidget(self.btn_dashboard)
        menu_layout.addWidget(self.btn_urunler)
        menu_layout.addWidget(self.btn_siparislerim)
        menu_layout.addWidget(self.btn_odeme)
        menu_layout.addWidget(self.btn_bildirimler) 
        menu_layout.addStretch() 

        menu_widget.setFixedWidth(200)
        main_layout.addWidget(menu_widget)
        
        # --- Sağ İçerik Alanı (Stacked Widget) ---
        self.stacked_content = QStackedWidget()
        main_layout.addWidget(self.stacked_content)
        
        # İçerik Sayfalarını Oluşturma
        self.dashboard_page = self.create_dashboard_page() 
        self.urunler_page = self.create_urunler_page()
        self.siparislerim_page = self.create_siparislerim_page()
        self.odeme_page = self.create_odeme_page()
        self.bildirimler_page = self.create_bildirimler_page() 
        
        self.stacked_content.addWidget(self.dashboard_page)
        self.stacked_content.addWidget(self.urunler_page)
        self.stacked_content.addWidget(self.siparislerim_page)
        self.stacked_content.addWidget(self.odeme_page)
        self.stacked_content.addWidget(self.bildirimler_page) 
        
        # Bağlantılar
        self.btn_dashboard.clicked.connect(lambda: self.stacked_content.setCurrentWidget(self.dashboard_page))
        self.btn_urunler.clicked.connect(lambda: self.show_urunler_page())
        self.btn_siparislerim.clicked.connect(lambda: self.show_siparislerim_page())
        self.btn_odeme.clicked.connect(lambda: self.show_odeme_page())
        self.btn_bildirimler.clicked.connect(lambda: self.show_bildirimler_page()) 
        
        self.show_urunler_page() 
        
    # --- YENİ BİLDİRİM SAYFASI METOTLARI ---
    
    def create_bildirimler_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>🔔 Bildirim Merkezi</h2>"))
        
        self.bildirim_listesi = QTableWidget()
        self.bildirim_listesi.setColumnCount(1)
        self.bildirim_listesi.setHorizontalHeaderLabels(["Bildirim"])
        self.bildirim_listesi.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.bildirim_listesi)
        
        self.btn_bildirim_temizle = QPushButton("Bildirimleri Temizle")
        self.btn_bildirim_temizle.clicked.connect(self.clear_bildirimler)
        layout.addWidget(self.btn_bildirim_temizle)
        
        return page
        
    def show_bildirimler_page(self):
        self.stacked_content.setCurrentWidget(self.bildirimler_page)
        self.load_bildirimler()
        
    def load_bildirimler(self):
        # Bildirim listesini tabloya yükle
        self.bildirim_listesi.setRowCount(len(self.bildirimler))
        
        for i, mesaj in enumerate(reversed(self.bildirimler)): # En yeniyi en üste getir
            self.bildirim_listesi.setItem(i, 0, QTableWidgetItem(mesaj))

        # Sayaç sıfırlama (Kullanıcı sayfayı görüntülediği için)
        if self.bildirim_sayaci > 0:
            self.bildirim_sayaci = 0
            self.btn_bildirimler.setText("🔔 Bildirimler")

    def clear_bildirimler(self):
        self.bildirimler = []
        self.bildirim_sayaci = 0
        self.load_bildirimler()
        self.btn_bildirimler.setText("🔔 Bildirimler")
    
    # --- DASHBOARD METODU ---
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"<h2>Hoş Geldiniz, Sn. {self.current_user.kullanici_adi.capitalize()}</h2>"))
        layout.addWidget(QLabel("<hr>"))
        
        try:
            # Müşterinin son sipariş durumunu ve toplam sipariş sayısını çekme
            toplam_siparis_sayisi = self.session.query(Siparis).filter(
                Siparis.kullanici_id == self.current_user.id
            ).count()
            
            son_siparis = self.session.query(Siparis).filter(
                Siparis.kullanici_id == self.current_user.id
            ).order_by(Siparis.tarih.desc()).first()
            
            son_durum = son_siparis.durum if son_siparis else "Henüz Sipariş Yok"
            
            html_content = f"""
            <div style="display: flex; justify-content: space-around; padding: 20px;">
                <div style="border: 1px solid #ddd; padding: 15px; width: 45%; background-color: #f0f8ff;">
                    <h4>📋 Toplam Sipariş Sayısı</h4>
                    <p style="font-size: 24px; color: blue;"><b>{toplam_siparis_sayisi}</b> Adet</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 45%; background-color: #fff0f0;">
                    <h4>⏳ Son Sipariş Durumu</h4>
                    <p style="font-size: 24px; color: {'green' if son_durum == 'Tamamlandı' else 'red'};"><b>{son_durum}</b></p>
                </div>
            </div>
            """
            
            layout.addWidget(QLabel(html_content))
            layout.addWidget(QLabel("<i>Ana menüden ürünleri görüntüleyebilir veya sipariş geçmişinizi kontrol edebilirsiniz.</i>"))

        except Exception as e:
            # Hata oluştuğunda sadece hatayı göster, uygulamanın çökmesini engelle
            layout.addWidget(QLabel(f"Dashboard verileri yüklenemedi: {e}"))
            
        layout.addStretch()
        return page

    # --- Ürünler Sayfası ---

    def create_urunler_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h3>🛒 Tüm Ürünler ve Sipariş</h3>"))
        
        self.urun_table = QTableWidget()
        self.urun_table.setColumnCount(5)
        self.urun_table.setHorizontalHeaderLabels(["ID", "Barkod", "Ürün Adı", "Fiyat", "İşlem"])
        self.urun_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.urun_table)
        
        sepete_ekle_layout = QHBoxLayout()
        self.sepete_ekle_barkod = QLineEdit(placeholderText="Barkod Girin")
        self.sepete_ekle_adet = QLineEdit(placeholderText="Adet (Varsayılan 1)")
        self.sepete_ekle_btn = QPushButton("Sepete Ekle")
        
        sepete_ekle_layout.addWidget(QLabel("Hızlı Ekle:"))
        sepete_ekle_layout.addWidget(self.sepete_ekle_barkod)
        sepete_ekle_layout.addWidget(self.sepete_ekle_adet)
        sepete_ekle_layout.addWidget(self.sepete_ekle_btn)
        
        layout.addLayout(sepete_ekle_layout)

        self.sepete_ekle_btn.clicked.connect(self.add_to_sepet_manual)
        
        return page
        
    def show_urunler_page(self):
        self.stacked_content.setCurrentWidget(self.urunler_page)
        self.load_urunler()

    def load_urunler(self):
        urunler = self.session.query(Urun).filter(Urun.stok > 0).all()
        self.urun_table.setRowCount(len(urunler))
        
        for i, urun in enumerate(urunler):
            self.urun_table.setItem(i, 0, QTableWidgetItem(str(urun.id)))
            self.urun_table.setItem(i, 1, QTableWidgetItem(urun.barkod))
            self.urun_table.setItem(i, 2, QTableWidgetItem(urun.isim))
            self.urun_table.setItem(i, 3, QTableWidgetItem(f"{urun.fiyat:.2f} ₺"))
            
            add_btn = QPushButton("Sepete Ekle")
            add_btn.clicked.connect(lambda checked, b=urun.barkod: self.add_to_sepet(b))
            self.urun_table.setCellWidget(i, 4, add_btn)

    def add_to_sepet(self, barkod, adet=1):
        urun = self.session.query(Urun).filter_by(barkod=barkod).first()
        
        if urun is None:
             QMessageBox.warning(self, "Hata", "Ürün bulunamadı.")
             return
             
        mevcut_adet = self.siparis_sepetic[barkod]['adet'] if barkod in self.siparis_sepetic else 0
        
        if urun.stok >= mevcut_adet + adet:
            if barkod in self.siparis_sepetic:
                self.siparis_sepetic[barkod]['adet'] += adet
            else:
                self.siparis_sepetic[barkod] = {'urun': urun, 'adet': adet}
            QMessageBox.information(self, "Sepet", f"{urun.isim} sepete eklendi. Toplam: {self.siparis_sepetic[barkod]['adet']} adet.")
        else:
             QMessageBox.warning(self, "Stok Yetersiz", f"Maksimum {urun.stok} adet ekleyebilirsiniz.")
             
    def add_to_sepet_manual(self):
        barkod = self.sepete_ekle_barkod.text().strip()
        adet_str = self.sepete_ekle_adet.text().strip()
        adet = int(adet_str) if adet_str.isdigit() and int(adet_str) > 0 else 1
        
        self.add_to_sepet(barkod, adet)
        self.sepete_ekle_barkod.clear()
        self.sepete_ekle_adet.clear()

    # --- Sipariş Geçmişi Sayfası ---

    def create_siparislerim_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h3>📄 Sipariş Geçmişiniz</h3>"))
        
        self.siparis_gecmisi_table = QTableWidget()
        self.siparis_gecmisi_table.setColumnCount(4)
        self.siparis_gecmisi_table.setHorizontalHeaderLabels(["ID", "Tarih", "Tutar", "Durum"])
        self.siparis_gecmisi_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.siparis_gecmisi_table.itemSelectionChanged.connect(self.display_siparis_details)
        layout.addWidget(self.siparis_gecmisi_table)
        
        self.siparis_detay_label = QLabel("Detay görmek için yukarıdan bir sipariş seçin.")
        self.siparis_detay_label.setStyleSheet("border: 1px solid #ccc; padding: 5px;")
        layout.addWidget(self.siparis_detay_label)
        
        self.siparis_urunler_table = QTableWidget()
        self.siparis_urunler_table.setColumnCount(3)
        self.siparis_urunler_table.setHorizontalHeaderLabels(["Ürün Adı", "Adet", "Birim Fiyat"])
        self.siparis_urunler_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.siparis_urunler_table)

        return page

    def show_siparislerim_page(self):
        self.stacked_content.setCurrentWidget(self.siparislerim_page)
        self.load_siparis_gecmisi()

    def load_siparis_gecmisi(self):
        siparisler = self.session.query(Siparis).filter(
            Siparis.kullanici_id == self.current_user.id
        ).order_by(Siparis.tarih.desc()).all()
        
        self.siparis_gecmisi_table.setRowCount(len(siparisler))
        
        for i, siparis in enumerate(siparisler):
            self.siparis_gecmisi_table.setItem(i, 0, QTableWidgetItem(str(siparis.id)))
            self.siparis_gecmisi_table.setItem(i, 1, QTableWidgetItem(siparis.tarih.strftime('%Y-%m-%d %H:%M')))
            self.siparis_gecmisi_table.setItem(i, 2, QTableWidgetItem(f"{siparis.toplam_tutar:.2f} ₺"))
            self.siparis_gecmisi_table.setItem(i, 3, QTableWidgetItem(siparis.durum))
            
    def display_siparis_details(self):
        selected_rows = self.siparis_gecmisi_table.selectionModel().selectedRows()
        if not selected_rows:
            self.siparis_detay_label.setText("Detay görmek için yukarıdan bir sipariş seçin.")
            self.siparis_urunler_table.setRowCount(0)
            return

        row = selected_rows[0].row()
        siparis_id = int(self.siparis_gecmisi_table.item(row, 0).text())
        
        siparis = self.session.query(Siparis).options(joinedload(Siparis.detaylar).joinedload(SiparisDetay.urun)).filter(
            Siparis.id == siparis_id
        ).one_or_none()
        
        if siparis:
            self.siparis_detay_label.setText(
                f"Sipariş ID: {siparis.id} | Durum: <b>{siparis.durum}</b> | Toplam: {siparis.toplam_tutar:.2f} ₺"
            )
            
            detaylar = siparis.detaylar
            self.siparis_urunler_table.setRowCount(len(detaylar))
            
            for i, detay in enumerate(detaylar):
                urun_adi = detay.urun.isim if detay.urun else "Bilinmeyen Ürün"
                
                self.siparis_urunler_table.setItem(i, 0, QTableWidgetItem(urun_adi))
                self.siparis_urunler_table.setItem(i, 1, QTableWidgetItem(str(detay.adet)))
                self.siparis_urunler_table.setItem(i, 2, QTableWidgetItem(f"{detay.birim_fiyat:.2f} ₺"))
        else:
             self.siparis_detay_label.setText("Sipariş detayları yüklenemedi.")


    def change_sepet_item_quantity(self, row, delta):
        barkod = self.odeme_sepet_table.item(row, 0).text()
        
        if barkod in self.siparis_sepetic:
            current_adet = self.siparis_sepetic[barkod]['adet']
            urun = self.siparis_sepetic[barkod]['urun']
            new_adet = current_adet + delta
            
            if new_adet <= 0:
                del self.siparis_sepetic[barkod]
            elif new_adet > urun.stok:
                QMessageBox.warning(self, "Stok", f"{urun.isim} için yeterli stok yok. Mevcut: {urun.stok}")
                return
            else:
                self.siparis_sepetic[barkod]['adet'] = new_adet
                
            self.load_sepet_ozet() 

    def remove_from_sepet(self, barkod):
        if barkod in self.siparis_sepetic:
            del self.siparis_sepetic[barkod]
            QMessageBox.information(self, "Sepet", "Ürün sepetten çıkarıldı.")
            self.load_sepet_ozet() 


    def create_odeme_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        self.odeme_sepet_table = QTableWidget()
        self.odeme_sepet_table.setColumnCount(6) 
        self.odeme_sepet_table.setHorizontalHeaderLabels(["Barkod", "Ürün Adı", "Fiyat", "Adet", "Ara Toplam", "İşlem"])
        self.odeme_sepet_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("<h3>💳 Sepet Özeti ve Ödeme</h3>"))
        layout.addWidget(self.odeme_sepet_table)
        
        self.toplam_label = QLabel("Toplam Tutar: 0.00 ₺")
        self.toplam_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.toplam_label)
        
        self.odeme_btn = QPushButton("Siparişi Tamamla ve Öde (Stoktan Düşülecek)")
        self.odeme_btn.clicked.connect(self.tamamla_siparis)
        layout.addWidget(self.odeme_btn)
        
        return page

    def show_odeme_page(self):
        self.stacked_content.setCurrentWidget(self.odeme_page)
        self.load_sepet_ozet()

    def load_sepet_ozet(self):
        self.odeme_sepet_table.setRowCount(len(self.siparis_sepetic))
        self.odeme_sepet_table.setColumnCount(6) 
        toplam_tutar = 0.0
        for i, (barkod, item) in enumerate(self.siparis_sepetic.items()):
            urun = item['urun']
            adet = item['adet']
            ara_toplam = urun.fiyat * adet
            toplam_tutar += ara_toplam
            
            
            self.odeme_sepet_table.setItem(i, 0, QTableWidgetItem(barkod)) 
            self.odeme_sepet_table.setItem(i, 1, QTableWidgetItem(urun.isim))
            self.odeme_sepet_table.setItem(i, 2, QTableWidgetItem(f"{urun.fiyat:.2f} ₺"))
            self.odeme_sepet_table.setItem(i, 3, QTableWidgetItem(str(adet)))
            self.odeme_sepet_table.setItem(i, 4, QTableWidgetItem(f"{ara_toplam:.2f} ₺"))
            
            
            islem_widget = QBtnWidget()
            islem_layout = QBtnLayout(islem_widget)
            islem_layout.setContentsMargins(0,0,0,0)

            btn_minus = QPushButton("-")
            btn_minus.setFixedWidth(25)
            btn_minus.clicked.connect(lambda checked, row=i, delta=-1: self.change_sepet_item_quantity(row, delta))
            
            btn_plus = QPushButton("+")
            btn_plus.setFixedWidth(25)
            btn_plus.clicked.connect(lambda checked, row=i, delta=1: self.change_sepet_item_quantity(row, delta))
            
            remove_btn = QPushButton("X")
            remove_btn.setFixedWidth(25)
            remove_btn.clicked.connect(lambda checked, b=barkod: self.remove_from_sepet(b))

            islem_layout.addWidget(btn_minus)
            islem_layout.addWidget(QLabel(str(adet))) 
            islem_layout.addWidget(btn_plus)
            islem_layout.addWidget(remove_btn)
            
            self.odeme_sepet_table.setCellWidget(i, 5, islem_widget) 
            
        self.toplam_label.setText(f"Toplam Tutar: {toplam_tutar:.2f} ₺")

    def tamamla_siparis(self):
        if not self.siparis_sepetic:
            QMessageBox.warning(self, "Sepet Boş", "Sepetinizde ürün bulunmamaktadır.")
            return

        toplam_tutar = 0.0
        siparis_detaylari = []
        
        
        for barkod, item in self.siparis_sepetic.items():
            urun = item['urun']
            adet = item['adet']
            toplam_tutar += urun.fiyat * adet
            
            siparis_detaylari.append({
                'urun_id': urun.id,
                'adet': adet,
                'birim_fiyat': urun.fiyat 
            })

        
        try:

            yeni_siparis = Siparis(
                kullanici_id=self.current_user.id, 
                durum="Bekleniyor",
                toplam_tutar=toplam_tutar,
                tarih=datetime.now()
            )
            self.session.add(yeni_siparis)
            self.session.flush() 

            
            for detay in siparis_detaylari:
                siparis_detay = SiparisDetay(
                    siparis_id=yeni_siparis.id,
                    urun_id=detay['urun_id'],
                    adet=detay['adet'],
                    birim_fiyat=detay['birim_fiyat']
                )
                self.session.add(siparis_detay)
                
                
                db_urun = self.session.query(Urun).filter_by(id=detay['urun_id']).with_for_update().first()
                if db_urun:
                    db_urun.stok -= detay['adet']
            
            self.session.commit()
            QMessageBox.information(self, "Sipariş Başarılı", f"Siparişiniz alındı ve 'Bekleniyor' durumuna geçti. Tutar: {toplam_tutar:.2f} ₺")
            
            self.siparis_sepetic = {} 
            self.load_sepet_ozet() 
            self.show_siparislerim_page()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Sipariş oluşturulurken hata: {e}")
            
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"<h2>Hoş Geldiniz, Sn. {self.current_user.kullanici_adi.capitalize()}</h2>"))
        layout.addWidget(QLabel("<hr>"))
        
        try:
            # Müşterinin son sipariş durumunu ve toplam sipariş sayısını çekme
            toplam_siparis_sayisi = self.session.query(Siparis).filter( # DÜZELTİLDİ: toplam_siparis_sayisi kullanıldı
                Siparis.kullanici_id == self.current_user.id
            ).count()
            
            son_siparis = self.session.query(Siparis).filter(
                Siparis.kullanici_id == self.current_user.id
            ).order_by(Siparis.tarih.desc()).first()
            
            son_durum = son_siparis.durum if son_siparis else "Henüz Sipariş Yok"
            
            html_content = f"""
            <div style="display: flex; justify-content: space-around; padding: 20px;">
                <div style="border: 1px solid #ddd; padding: 15px; width: 45%; background-color: #f0f8ff;">
                    <h4>📋 Toplam Sipariş Sayısı</h4>
                    <p style="font-size: 24px; color: blue;"><b>{toplam_siparis_sayisi}</b> Adet</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 45%; background-color: #fff0f0;">
                    <h4>⏳ Son Sipariş Durumu</h4>
                    <p style="font-size: 24px; color: {'green' if son_durum == 'Tamamlandı' else 'red'};"><b>{son_durum}</b></p>
                </div>
            </div>
            """
            
            layout.addWidget(QLabel(html_content))
            layout.addWidget(QLabel("<i>Ana menüden ürünleri görüntüleyebilir veya sipariş geçmişinizi kontrol edebilirsiniz.</i>"))

        except Exception as e:
            layout.addWidget(QLabel(f"Dashboard verileri yüklenemedi: {e}"))
            
        layout.addStretch()
        return page