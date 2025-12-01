from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QLabel, QStackedWidget, QHeaderView, QLineEdit, 
    QMessageBox, QGroupBox, QHBoxLayout as QBtnLayout
)
from PyQt5.QtCore import Qt
from db_model import Urun, Siparis, Kullanici, Session ,Satis,SatisDetay
from sqlalchemy.orm import joinedload
from sqlalchemy import func # SQLAlchemy fonksiyonları için import
from datetime import datetime, date, timedelta # date ve timedelta Dashboard için eklendi

# ReportLab ve OS kütüphanelerini import ediyoruz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os

class CalisanView(QWidget):
    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.satis_sepetic = {}
        self.satis_to_print = None 
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- Sol Menü (Navigasyon) ---
        menu_widget = QWidget()
        menu_layout = QVBoxLayout(menu_widget)
        
        self.btn_dashboard = QPushButton("🏠 Dashboard")
        self.btn_dashboard.setObjectName("nav_btn") # STİL İÇİN EKLENDİ
        
        self.btn_satis_ekrani = QPushButton("💵 Satış Ekranı")
        self.btn_satis_ekrani.setObjectName("nav_btn") # STİL İÇİN EKLENDİ
        
        self.btn_siparisler = QPushButton("📦 Gelen Siparişler")
        self.btn_siparisler.setObjectName("nav_btn") # STİL İÇİN EKLENDİ
        
        self.btn_fatura = QPushButton("🧾 Fatura Oluştur")
        self.btn_fatura.setObjectName("nav_btn") # STİL İÇİN EKLENDİ
        
        menu_layout.addWidget(self.btn_dashboard)
        menu_layout.addWidget(self.btn_satis_ekrani)
        menu_layout.addWidget(self.btn_siparisler)
        menu_layout.addWidget(self.btn_fatura) 
        menu_layout.addStretch()

        menu_widget.setFixedWidth(200)
        main_layout.addWidget(menu_widget)
        
        # --- Sağ İçerik Alanı (Stacked Widget) ---
        self.stacked_content = QStackedWidget()
        main_layout.addWidget(self.stacked_content)
        
        # İçerik Sayfalarını Oluşturma
        self.dashboard_page = self.create_dashboard_page() # Dashboard metodu çağrıldı
        self.satis_ekrani_page = self.create_satis_ekrani_page()
        self.siparisler_page = self.create_siparisler_page()
        self.fatura_page = self.create_fatura_page() 
        
        # Sayfaları Stacked Widget'a Ekleme
        self.stacked_content.addWidget(self.dashboard_page) 
        self.stacked_content.addWidget(self.satis_ekrani_page)
        self.stacked_content.addWidget(self.siparisler_page)
        self.stacked_content.addWidget(self.fatura_page) 
        
        # Bağlantılar
        self.btn_dashboard.clicked.connect(lambda: self.stacked_content.setCurrentWidget(self.dashboard_page))
        self.btn_satis_ekrani.clicked.connect(lambda: self.show_satis_ekrani())
        self.btn_siparisler.clicked.connect(lambda: self.show_siparisler_page())
        self.btn_fatura.clicked.connect(lambda: self.show_fatura_page()) 
        
        self.stacked_content.setCurrentWidget(self.dashboard_page) # Başlangıç: Dashboard
    
    # --- DASHBOARD METODU ---
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"<h2>Hoş Geldiniz, {self.current_user.kullanici_adi.capitalize()}</h2>"))
        layout.addWidget(QLabel("<hr>"))
        
        try:
            bugun = date.today()
            
            # 1. Günlük Satış Performansı
            gunluk_satis_sayisi = self.session.query(Satis).filter(
                Satis.calisan_id == self.current_user.id,
                func.date(Satis.tarih) == bugun
            ).count()
            
            gunluk_ciro = self.session.query(func.sum(Satis.toplam_tutar)).filter(
                Satis.calisan_id == self.current_user.id,
                func.date(Satis.tarih) == bugun
            ).scalar() or 0.0

            # 2. Yeni Bekleyen Siparişler 
            bekleyen_siparis_sayisi = self.session.query(Siparis).filter(
                Siparis.durum == 'Bekleniyor'
            ).count()
            
            html_content = f"""
            <div style="display: flex; justify-content: space-around; padding: 20px;">
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #e6f7ff;">
                    <h4>📅 Bugünki Satış Sayısı</h4>
                    <p style="font-size: 24px; color: blue;"><b>{gunluk_satis_sayisi}</b> Adet</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #e6ffe6;">
                    <h4>💰 Bugünki Ciro</h4>
                    <p style="font-size: 24px; color: green;"><b>{gunluk_ciro:.2f}</b> ₺</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #fff0e6;">
                    <h4>📦 Yeni Siparişler</h4>
                    <p style="font-size: 24px; color: #ff8c00;"><b>{bekleyen_siparis_sayisi}</b> Bekleyen</p>
                </div>
            </div>
            """
            
            layout.addWidget(QLabel(html_content))
            
        except Exception as e:
            layout.addWidget(QLabel(f"Dashboard verileri yüklenemedi: {e}"))
            
        layout.addStretch()
        return page

    # --- Satış Ekranı Metotları (POS) ---
    
    def create_satis_ekrani_page(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.addWidget(QLabel("<h2>💵 Hızlı Satış Ekranı</h2>"))
        
        content_layout = QHBoxLayout()

        # 1. Sepet Alanı
        sepet_group = QGroupBox("Sepet")
        sepet_layout = QVBoxLayout(sepet_group)
        self.sepet_table = QTableWidget()
        self.sepet_table.setColumnCount(6) 
        self.sepet_table.setHorizontalHeaderLabels(["Barkod", "Ürün Adı", "Fiyat", "Adet", "Toplam", "İşlemler"]) 
        self.sepet_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sepet_layout.addWidget(self.sepet_table)
        content_layout.addWidget(sepet_group, 3) 

        # 2. İşlem Alanı
        islem_group = QGroupBox("İşlemler")
        islem_layout = QVBoxLayout(islem_group)

        # Barkod Girişi
        barkod_layout = QBtnLayout()
        self.barkod_input = QLineEdit(placeholderText="Barkod Tarayın veya Girin")
        self.barkod_input.returnPressed.connect(self.add_to_satis_sepeti) 
        barkod_layout.addWidget(self.barkod_input)
        islem_layout.addLayout(barkod_layout)

        # Toplam Tutar ve Ödeme
        islem_layout.addStretch()
        self.toplam_tutar_label = QLabel("<h2>Toplam: 0.00 ₺</h2>")
        islem_layout.addWidget(self.toplam_tutar_label)
        
        self.odeme_btn = QPushButton("✅ Satışı Tamamla")
        self.odeme_btn.setFixedHeight(50)
        self.odeme_btn.clicked.connect(self.tamamla_satis)
        
        self.iptal_btn = QPushButton("❌ Satışı İptal Et")
        self.iptal_btn.clicked.connect(self.iptal_satis)
        
        islem_layout.addWidget(self.odeme_btn)
        islem_layout.addWidget(self.iptal_btn)
        content_layout.addWidget(islem_group, 2) 

        main_layout.addLayout(content_layout)
        return page

    def show_satis_ekrani(self):
        self.stacked_content.setCurrentWidget(self.satis_ekrani_page)
        self.barkod_input.setFocus() 

    def add_to_satis_sepeti(self, barkod_input_val=None, adet=1):
        if barkod_input_val is None:
            barkod = self.barkod_input.text().strip()
            self.barkod_input.clear() 
        else:
            barkod = barkod_input_val

        if not barkod:
            return

        urun = self.session.query(Urun).filter_by(barkod=barkod).first()
        
        if urun is None:
            QMessageBox.warning(self, "Hata", "Ürün bulunamadı.")
            return

        if urun.stok < adet:
            QMessageBox.warning(self, "Stok", f"{urun.isim} için yeterli stok yok. Mevcut: {urun.stok}")
            return

        if barkod in self.satis_sepetic:
            self.satis_sepetic[barkod]['adet'] += adet
        else:
            self.satis_sepetic[barkod] = {'urun': urun, 'adet': adet}

        self.update_sepet_table()
        
    def change_sepet_item_quantity(self, row, delta):
        barkod = self.sepet_table.item(row, 0).text()
        
        if barkod in self.satis_sepetic:
            current_adet = self.satis_sepetic[barkod]['adet']
            urun = self.satis_sepetic[barkod]['urun']
            new_adet = current_adet + delta
            
            if new_adet <= 0:
                del self.satis_sepetic[barkod]
            elif new_adet > urun.stok:
                QMessageBox.warning(self, "Stok", f"{urun.isim} için yeterli stok yok. Mevcut: {urun.stok}")
                return
            else:
                self.satis_sepetic[barkod]['adet'] = new_adet
                
            self.update_sepet_table()

    def update_sepet_table(self):
        self.sepet_table.setRowCount(len(self.satis_sepetic))
        self.sepet_table.setColumnCount(6) 
        self.sepet_table.setHorizontalHeaderLabels(["Barkod", "Ürün Adı", "Fiyat", "Adet", "Toplam", "İşlemler"])
        
        toplam_tutar = 0.0
        
        for i, (barkod, item) in enumerate(self.satis_sepetic.items()):
            urun = item['urun']
            adet = item['adet']
            ara_toplam = urun.fiyat * adet
            toplam_tutar += ara_toplam

            self.sepet_table.setItem(i, 0, QTableWidgetItem(barkod))
            self.sepet_table.setItem(i, 1, QTableWidgetItem(urun.isim))
            self.sepet_table.setItem(i, 2, QTableWidgetItem(f"{urun.fiyat:.2f} ₺"))
            self.sepet_table.setItem(i, 3, QTableWidgetItem(str(adet)))
            self.sepet_table.setItem(i, 4, QTableWidgetItem(f"{ara_toplam:.2f} ₺"))

            islem_widget = QWidget()
            islem_layout = QBtnLayout(islem_widget)
            islem_layout.setContentsMargins(0,0,0,0)
            
            btn_minus = QPushButton("-")
            btn_minus.setFixedWidth(25)
            btn_minus.clicked.connect(lambda checked, row=i, delta=-1: self.change_sepet_item_quantity(row, delta))
            
            btn_plus = QPushButton("+")
            btn_plus.setFixedWidth(25)
            btn_plus.clicked.connect(lambda checked, row=i, delta=1: self.change_sepet_item_quantity(row, delta))
            
            islem_layout.addWidget(btn_minus)
            islem_layout.addWidget(btn_plus)
            
            self.sepet_table.setCellWidget(i, 5, islem_widget)
            
        self.toplam_tutar_label.setText(f"<h2>Toplam: {toplam_tutar:.2f} ₺</h2>")
        self.barkod_input.setFocus()
        if self.sepet_table.rowCount() > 0:
            self.sepet_table.scrollToBottom()


    def tamamla_satis(self):
        if not self.satis_sepetic:
            QMessageBox.warning(self, "Uyarı", "Sepet boş. Lütfen ürün ekleyin.")
            return

        toplam_tutar = 0.0
        satis_detaylari = []
        
        for barkod, item in self.satis_sepetic.items():
            urun = item['urun']
            adet = item['adet']
            
            if urun.stok < adet:
                QMessageBox.critical(self, "Stok Hatası", f"{urun.isim} için yeterli stok yok. Mevcut: {urun.stok}")
                return 

            ara_toplam = urun.fiyat * adet
            toplam_tutar += ara_toplam
            
            satis_detaylari.append({
                'urun_id': urun.id,
                'adet': adet,
                'birim_fiyat': urun.fiyat 
            })

        try:
            yeni_satis = Satis(
                calisan_id=self.current_user.id,
                tarih=datetime.now(),
                toplam_tutar=toplam_tutar
            )
            self.session.add(yeni_satis)
            self.session.flush() 

            for detay in satis_detaylari:
                satis_detay = SatisDetay(
                    satis_id=yeni_satis.id,
                    urun_id=detay['urun_id'],
                    adet=detay['adet'],
                    birim_fiyat=detay['birim_fiyat']
                )
                self.session.add(satis_detay)
                
                db_urun = self.session.query(Urun).filter_by(id=detay['urun_id']).with_for_update().first()
                if db_urun:
                    db_urun.stok -= detay['adet']
            
            self.session.commit()
            QMessageBox.information(self, "Başarılı", f"Satış tamamlandı. Toplam Tutar: {toplam_tutar:.2f} ₺")
            
            self.satis_to_print = yeni_satis 
            self.iptal_satis() 
            self.show_fatura_page() 

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Veritabanı Hatası", f"Satış işlemi sırasında beklenmedik bir hata oluştu: {e}")

    def iptal_satis(self):
        self.satis_sepetic = {}
        self.update_sepet_table()

    # --- Sipariş Yönetimi Metotları ---

    def create_siparisler_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>📦 Gelen Müşteri Siparişleri</h2>"))

        self.siparis_table = QTableWidget()
        self.siparis_table.setColumnCount(4)
        self.siparis_table.setHorizontalHeaderLabels(["ID", "Müşteri", "Tarih", "Durum"])
        self.siparis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.siparis_table)

        self.guncelle_btn = QPushButton("Durumu 'Hazırlanıyor' Olarak Güncelle")
        self.guncelle_btn.clicked.connect(self.update_siparis_status)
        layout.addWidget(self.guncelle_btn)
        return page

    def show_siparisler_page(self):
        self.stacked_content.setCurrentWidget(self.siparisler_page)
        self.load_siparisler()

    def load_siparisler(self):
        siparisler = self.session.query(Siparis).options(joinedload(Siparis.kullanici)).filter(Siparis.durum != 'Tamamlandı').all()
        self.siparis_table.setRowCount(len(siparisler))

        for i, siparis in enumerate(siparisler):
            kullanici_adi = siparis.kullanici.kullanici_adi if siparis.kullanici else "Bilinmiyor"
            
            self.siparis_table.setItem(i, 0, QTableWidgetItem(str(siparis.id)))
            self.siparis_table.setItem(i, 1, QTableWidgetItem(kullanici_adi))
            self.siparis_table.setItem(i, 2, QTableWidgetItem(siparis.tarih.strftime("%Y-%m-%d %H:%M")))
            self.siparis_table.setItem(i, 3, QTableWidgetItem(siparis.durum))

    def update_siparis_status(self):
        secili_satirlar = self.siparis_table.selectionModel().selectedRows()
        if not secili_satirlar:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir sipariş seçin.")
            return

        try:
            for index in secili_satirlar:
                siparis_id = int(self.siparis_table.item(index.row(), 0).text())
                siparis = self.session.query(Siparis).filter_by(id=siparis_id).first()
                
                if siparis:
                    if siparis.durum == 'Bekleniyor':
                        siparis.durum = 'Hazırlanıyor'
            
            self.session.commit()
            QMessageBox.information(self, "Başarılı", f"{len(secili_satirlar)} adet sipariş durumu güncellendi.")
            self.load_siparisler()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Sipariş güncellenirken bir hata oluştu: {e}")

    # --- Fatura Oluşturma Metotları ---

    def create_fatura_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>🧾 Fatura Oluştur</h2>"))
        
        # Son Satışı Gösterme Alanı
        self.fatura_bilgi_label = QLabel("<h3>Fatura Özeti</h3>")
        self.fatura_bilgi_label.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
        layout.addWidget(self.fatura_bilgi_label)
        
        self.fatura_detay_table = QTableWidget()
        self.fatura_detay_table.setColumnCount(4)
        self.fatura_detay_table.setHorizontalHeaderLabels(["Ürün", "Adet", "Birim Fiyat", "Tutar"])
        self.fatura_detay_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.fatura_detay_table)
        
        # Kullanıcıya göre fatura oluşturma (Şimdilik son satışı getiriyoruz)
        self.btn_son_satis = QPushButton("Son Yapılan Satışı Getir")
        self.btn_son_satis.clicked.connect(self.load_son_satis_fatura)
        layout.addWidget(self.btn_son_satis)
        
        self.btn_yazdir = QPushButton("Faturayı Yazdır (PDF)") # Metin güncellendi
        self.btn_yazdir.setEnabled(False) 
        self.btn_yazdir.clicked.connect(self.print_fatura) # Bağlantı güncellendi
        layout.addWidget(self.btn_yazdir)
        
        return page

    def show_fatura_page(self):
        self.stacked_content.setCurrentWidget(self.fatura_page)
        self.load_son_satis_fatura() 

    def load_son_satis_fatura(self):
        son_satis = self.session.query(Satis).options(joinedload(Satis.detaylar).joinedload(SatisDetay.urun)).filter(
            Satis.calisan_id == self.current_user.id
        ).order_by(Satis.tarih.desc()).first()

        if not son_satis:
            self.fatura_bilgi_label.setText("<h3>Fatura Özeti</h3><br>Bu çalışan tarafından yapılmış satış bulunmamaktadır.")
            self.fatura_detay_table.setRowCount(0)
            self.btn_yazdir.setEnabled(False)
            self.satis_to_print = None # Önemli
            return

        self.satis_to_print = son_satis 
        
        self.fatura_bilgi_label.setText(
            f"<h3>Fatura Özeti (Son Satış ID: {son_satis.id})</h3>"
            f"Tarih: {son_satis.tarih.strftime('%Y-%m-%d %H:%M')}<br>"
            f"Toplam Tutar: <b>{son_satis.toplam_tutar:.2f} ₺</b>"
        )
        
        detaylar = son_satis.detaylar
        self.fatura_detay_table.setRowCount(len(detaylar))
        
        for i, detay in enumerate(detaylar):
            urun_adi = detay.urun.isim if detay.urun else "Bilinmeyen Ürün"
            ara_tutar = detay.adet * detay.birim_fiyat
            
            self.fatura_detay_table.setItem(i, 0, QTableWidgetItem(urun_adi))
            self.fatura_detay_table.setItem(i, 1, QTableWidgetItem(str(detay.adet)))
            self.fatura_detay_table.setItem(i, 2, QTableWidgetItem(f"{detay.birim_fiyat:.2f} ₺"))
            self.fatura_detay_table.setItem(i, 3, QTableWidgetItem(f"{ara_tutar:.2f} ₺"))
            
        self.btn_yazdir.setEnabled(True)
        
    def print_fatura(self):
        if self.satis_to_print:
            self.generate_pdf_fatura(self.satis_to_print)
        else:
            QMessageBox.warning(self, "Uyarı", "Yazdırılacak bir satış bulunamadı. Lütfen 'Son Yapılan Satışı Getir' butonuna tıklayın.")

    def generate_pdf_fatura(self, satis_obj):
        tarih_str = satis_obj.tarih.strftime("%Y%m%d_%H%M%S")
        filename = f"Fatura_{satis_obj.id}_{tarih_str}.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("<b>AKILLI MARKET SATIŞ FATURASI</b>", styles['Title']))
        story.append(Spacer(1, 12))

        fatura_info = [
            ['Fatura ID:', str(satis_obj.id)],
            ['Tarih:', satis_obj.tarih.strftime('%Y-%m-%d %H:%M')],
            ['Çalışan:', self.current_user.kullanici_adi]
        ]
        t = Table(fatura_info, colWidths=[100, 200])
        t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(t)
        story.append(Spacer(1, 18))

        data = [["Ürün Adı", "Adet", "Birim Fiyat (₺)", "Tutar (₺)"]]
        
        toplam_tutar = 0
        
        for detay in satis_obj.detaylar:
            urun_adi = detay.urun.isim if detay.urun else "Bilinmeyen Ürün"
            ara_tutar = detay.adet * detay.birim_fiyat
            toplam_tutar += ara_tutar
            data.append([
                urun_adi, 
                str(detay.adet), 
                f"{detay.birim_fiyat:.2f}",
                f"{ara_tutar:.2f}"
            ])

        data.append(['', '', '<b>GENEL TOPLAM:</b>', f'<b>{toplam_tutar:.2f}</b>'])
        
        col_widths = [250, 50, 100, 100]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey), 
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), 
            ('ALIGN', (2, -1), (-2, -1), 'LEFT'), 
        ]))
        story.append(t)
        story.append(Spacer(1, 18))
        
        story.append(Paragraph("<i>Bizi tercih ettiğiniz için teşekkür ederiz!</i>", styles['Italic']))

        doc.build(story)
        
        QMessageBox.information(self, "PDF Oluşturuldu", 
                                f"Fatura başarıyla oluşturuldu: <b>{filename}</b>\nDosya konumu: {os.getcwd()}")
    
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"<h2>Hoş Geldiniz, {self.current_user.kullanici_adi.capitalize()}</h2>"))
        layout.addWidget(QLabel("<hr>"))
        
        try:
            from sqlalchemy import func
            from datetime import date, timedelta
            
            bugun = date.today()
            
            # 1. Günlük Satış Performansı
            gunluk_satis_sayisi = self.session.query(Satis).filter(
                Satis.calisan_id == self.current_user.id,
                func.date(Satis.tarih) == bugun
            ).count()
            
            gunluk_ciro = self.session.query(func.sum(Satis.toplam_tutar)).filter(
                Satis.calisan_id == self.current_user.id,
                func.date(Satis.tarih) == bugun
            ).scalar() or 0.0

            # 2. Yeni Bekleyen Siparişler (Çalışanın ilgilenmesi gereken)
            bekleyen_siparis_sayisi = self.session.query(Siparis).filter(
                Siparis.durum == 'Bekleniyor'
            ).count()
            
            html_content = f"""
            <div style="display: flex; justify-content: space-around; padding: 20px;">
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #e6f7ff;">
                    <h4>📅 Bugünki Satış Sayısı</h4>
                    <p style="font-size: 24px; color: blue;"><b>{gunluk_satis_sayisi}</b> Adet</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #e6ffe6;">
                    <h4>💰 Bugünki Ciro</h4>
                    <p style="font-size: 24px; color: green;"><b>{gunluk_ciro:.2f}</b> ₺</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #fff0e6;">
                    <h4>📦 Yeni Siparişler</h4>
                    <p style="font-size: 24px; color: #ff8c00;"><b>{bekleyen_siparis_sayisi}</b> Bekleyen</p>
                </div>
            </div>
            """
            
            layout.addWidget(QLabel(html_content))
            
        except Exception as e:
            layout.addWidget(QLabel(f"Dashboard verileri yüklenemedi: {e}"))
            
        layout.addStretch()
        return page