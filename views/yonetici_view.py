from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QLabel, QStackedWidget, QHeaderView, QMessageBox, 
    QLineEdit, QDialog, QFormLayout, QHBoxLayout as QBtnLayout
)
from PyQt5.QtCore import Qt, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap 
from sqlalchemy.orm import joinedload
from sqlalchemy import func, extract 
from db_model import *
from dialogs.urun_ekle_dialog import UrunEkleDuzenleDialog

# ReportLab ve OS kütüphanelerini import ediyoruz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
from datetime import datetime, timedelta, date 

# Matplotlib için gerekli importlar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io


# --- Yardımcı Düzenleme Penceresi: Çalışan Bilgilerini Güncelleme ---
# ... (CalisanDuzenleDialog sınıfı aynı kalır) ...
class CalisanDuzenleDialog(QDialog):
    def __init__(self, calisan, session, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{calisan.kullanici.kullanici_adi} Düzenle")
        self.calisan = calisan
        self.session = session
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self) 
        
        self.maas_input = QLineEdit(str(self.calisan.maas))
        self.pozisyon_input = QLineEdit(self.calisan.pozisyon)

        layout.addRow("Maaş:", self.maas_input)
        layout.addRow("Pozisyon:", self.pozisyon_input)

        self.save_btn = QPushButton("Kaydet")
        self.save_btn.clicked.connect(self.save_changes)
        layout.addWidget(self.save_btn)

    def save_changes(self):
        try:
            yeni_maas = float(self.maas_input.text())
            yeni_pozisyon = self.pozisyon_input.text().strip()
            
            self.calisan.maas = yeni_maas
            self.calisan.pozisyon = yeni_pozisyon
            self.session.commit()
            
            QMessageBox.information(self, "Başarılı", "Çalışan bilgileri güncellendi.")
            self.accept()
        except ValueError:
            QMessageBox.critical(self, "Hata", "Maaş geçerli bir sayı olmalıdır.")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Veritabanı hatası: {e}")
# --- Ana Yönetici Görünümü ---
class YoneticiView(QWidget):
    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- Sol Menü (Navigasyon) ---
        menu_widget = QWidget()
        menu_layout = QVBoxLayout(menu_widget) 
        
        self.btn_dashboard = QPushButton("🏠 Dashboard")
        self.btn_dashboard.setObjectName("nav_btn") 
        
        self.btn_raporlama = QPushButton("📊 Raporlama")
        self.btn_raporlama.setObjectName("nav_btn") 
        
        self.btn_siparisler = QPushButton("📦 Tüm Siparişler")
        self.btn_siparisler.setObjectName("nav_btn") 
        
        self.btn_calisan_yonetim = QPushButton("👥 Çalışan Yönetimi")
        self.btn_calisan_yonetim.setObjectName("nav_btn") 
        
        self.btn_urun_yonetim = QPushButton("📦 Ürün Yönetimi") 
        self.btn_urun_yonetim.setObjectName("nav_btn") 
        
        menu_layout.addWidget(self.btn_dashboard)
        menu_layout.addWidget(self.btn_raporlama)
        menu_layout.addWidget(self.btn_siparisler)
        menu_layout.addWidget(self.btn_calisan_yonetim)
        menu_layout.addWidget(self.btn_urun_yonetim) 
        menu_layout.addStretch()

        menu_widget.setFixedWidth(200)
        main_layout.addWidget(menu_widget)
        
        # --- Sağ İçerik Alanı (Stacked Widget) ---
        self.stacked_content = QStackedWidget()
        main_layout.addWidget(self.stacked_content)
        
        # İçerik Sayfalarını Oluşturma
        self.dashboard_page = self.create_dashboard_page() 
        self.raporlama_page = self.create_raporlama_page()
        self.siparisler_page = self.create_siparisler_page()
        self.calisan_yonetim_page = self.create_calisan_yonetim_page()
        self.urun_yonetim_page = self.create_urun_yonetim_page() 
        
        self.stacked_content.addWidget(self.dashboard_page)
        self.stacked_content.addWidget(self.raporlama_page)
        self.stacked_content.addWidget(self.siparisler_page)
        self.stacked_content.addWidget(self.calisan_yonetim_page)
        self.stacked_content.addWidget(self.urun_yonetim_page) 
        
        # Bağlantılar
        self.btn_dashboard.clicked.connect(lambda: self.stacked_content.setCurrentWidget(self.dashboard_page))
        self.btn_raporlama.clicked.connect(self.show_raporlama_page)
        self.btn_siparisler.clicked.connect(self.show_siparisler_page)
        self.btn_calisan_yonetim.clicked.connect(self.show_calisan_yonetim_page)
        self.btn_urun_yonetim.clicked.connect(self.show_urun_yonetim_page) 
        
        self.stacked_content.setCurrentWidget(self.dashboard_page)

    # --- DASHBOARD METODU (GÜNCELLENDİ) ---
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"<h2>Hoş Geldiniz, Yönetici {self.current_user.kullanici_adi.capitalize()}</h2>"))
        layout.addWidget(QLabel("<hr>"))

        # 1. Özet Kartlar
        try:
            toplam_urun_sayisi = self.session.query(Urun).count()
            kritik_stok_sayisi = self.session.query(Urun).filter(Urun.stok < 5).count()
            otuz_gun_oncesi = datetime.now() - timedelta(days=30)
            son_30_gun_ciro = self.session.query(func.sum(Satis.toplam_tutar)).filter(
                Satis.tarih >= otuz_gun_oncesi
            ).scalar() or 0.0
            bekleyen_siparis_sayisi = self.session.query(Siparis).filter(
                Siparis.durum == 'Bekleniyor'
            ).count()

            html_content = f"""
            <div style="display: flex; justify-content: space-around; padding: 20px;">
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #f9f9f9;">
                    <h4>📉 Kritik Stok</h4>
                    <p style="font-size: 24px; color: red;"><b>{kritik_stok_sayisi}</b> Ürün</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #f9f9f9;">
                    <h4>💰 Son 30 Gün Ciro</h4>
                    <p style="font-size: 24px; color: green;"><b>{son_30_gun_ciro:.2f}</b> ₺</p>
                </div>
                <div style="border: 1px solid #ddd; padding: 15px; width: 30%; background-color: #f9f9f9;">
                    <h4>⏳ Bekleyen Sipariş</h4>
                    <p style="font-size: 24px; color: orange;"><b>{bekleyen_siparis_sayisi}</b> Adet</p>
                </div>
            </div>
            <p><i>Genel Ürün Sayısı: {toplam_urun_sayisi}</i></p>
            """
            
            layout.addWidget(QLabel(html_content))
            
            # 2. Grafik Alanı (YENİ EKLENTİ)
            layout.addWidget(QLabel("<h3>Son 30 Günlük Satış Trendi</h3>"))
            self.sales_chart_label = QLabel("Grafik Yükleniyor...")
            self.sales_chart_label.setAlignment(Qt.AlignCenter)
            self.sales_chart_label.setMinimumSize(500, 300)
            layout.addWidget(self.sales_chart_label)
            
            # Grafiği yükle
            self.load_sales_chart()

        except Exception as e:
            layout.addWidget(QLabel(f"Dashboard verileri yüklenemedi: {e}"))
            
        layout.addStretch()
        return page

    # YENİ METOT: Satış trendi grafiğini oluşturur ve QLabel'a yükler
    def load_sales_chart(self):
        try:
            otuz_gun_oncesi = datetime.now() - timedelta(days=30)
            
            sales_data = self.session.query(
                func.date(Satis.tarih).label('date'),
                func.sum(Satis.toplam_tutar).label('total_sales')
            ).filter(
                Satis.tarih >= otuz_gun_oncesi
            ).group_by(func.date(Satis.tarih)).order_by(func.date(Satis.tarih)).all()

            if not sales_data:
                self.sales_chart_label.setText("Son 30 günde satış verisi bulunmamaktadır.")
                return

            # Hata Çözümü: Veritabanından gelen string tarihleri datetime.date objesine dönüştür.
            dates = []
            sales = []
            
            for d in sales_data:
                # SQLAlchemy/SQLite bazen tarihi string olarak döndürür
                if isinstance(d.date, str):
                    try:
                        # String'i datetime objesine çevir
                        dt_obj = datetime.strptime(d.date, '%Y-%m-%d').date()
                    except ValueError:
                        # Eğer format farklıysa veya dönüşüm başarısız olursa atla
                        continue 
                else:
                    dt_obj = d.date
                
                dates.append(dt_obj)
                sales.append(d.total_sales)

            # Matplotlib ile grafiği çizme
            fig, ax = plt.subplots(figsize=(6, 3))
            
            # Çubuk grafik kullanımı
            ax.bar(dates, sales, color='#007ACC')
            
            ax.set_title('Günlük Ciro (Son 30 Gün)')
            ax.set_ylabel('Ciro (₺)')
            
            # Eksen etiketlerini ayarlama (Sadece dates objelerini kullanıyoruz)
            if dates:
                # Sadece her 5 günde bir etiket göster
                ax.set_xticks(dates[::5]) 
                ax.set_xticklabels([d.strftime('%m-%d') for d in dates[::5]], rotation=45, ha='right')
            
            plt.tight_layout()

            # Grafiği QPixmap'e dönüştürme
            buf = io.BytesIO()
            fig.savefig(buf, format='png')
            plt.close(fig) 
            
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue(), 'png')
            self.sales_chart_label.setPixmap(pixmap)
            self.sales_chart_label.setText("") 

        except Exception as e:
            self.sales_chart_label.setText(f"Grafik yüklenirken hata oluştu: {e}")
            print(f"Grafik Hatası: {e}") 

    # --- Çalışan Yönetimi Metotları ---
    
    def create_calisan_yonetim_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>👥 Çalışan Yönetimi</h2>"))

        self.calisan_table = QTableWidget()
        self.calisan_table.setColumnCount(5)
        self.calisan_table.setHorizontalHeaderLabels(["ID", "Kullanıcı Adı", "Pozisyon", "Maaş", "İşlem"])
        self.calisan_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.calisan_table)
        
        self.guncelle_btn = QPushButton("Çalışanları Yenile")
        self.guncelle_btn.clicked.connect(self.load_calisanlar)
        layout.addWidget(self.guncelle_btn)
        
        return page

    def show_calisan_yonetim_page(self):
        self.stacked_content.setCurrentWidget(self.calisan_yonetim_page)
        self.load_calisanlar()

    def load_calisanlar(self):
        calisanlar_data = self.session.query(CalisanBilgisi).options(joinedload(CalisanBilgisi.kullanici)).join(
            Kullanici, CalisanBilgisi.kullanici_id == Kullanici.id 
        ).filter(
            Kullanici.rol.in_(['calisan', 'yonetici'])
        ).all()
        
        self.calisan_table.setRowCount(len(calisanlar_data))
        
        for i, calisan_bilgi in enumerate(calisanlar_data):
            kullanici = calisan_bilgi.kullanici
            
            self.calisan_table.setItem(i, 0, QTableWidgetItem(str(kullanici.id)))
            self.calisan_table.setItem(i, 1, QTableWidgetItem(kullanici.kullanici_adi))
            self.calisan_table.setItem(i, 2, QTableWidgetItem(calisan_bilgi.pozisyon))
            self.calisan_table.setItem(i, 3, QTableWidgetItem(f"{calisan_bilgi.maas:.2f} ₺"))
            
            edit_btn = QPushButton("Düzenle")
            edit_btn.clicked.connect(lambda checked, c=calisan_bilgi: self.open_calisan_duzenle(c))
            self.calisan_table.setCellWidget(i, 4, edit_btn) # HATA DÜZELTİLDİ

    def open_calisan_duzenle(self, calisan_bilgi):
        dialog = CalisanDuzenleDialog(calisan_bilgi, self.session, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_calisanlar() 
            
    # --- Sipariş Görüntüleme Metotları (Tüm Siparişler) ---
    
    def create_siparisler_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>📦 Tüm Gelen Siparişler</h2>"))

        self.siparis_table = QTableWidget()
        self.siparis_table.setColumnCount(5)
        self.siparis_table.setHorizontalHeaderLabels(["ID", "Müşteri", "Tarih", "Tutar", "Durum"])
        self.siparis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.siparis_table)

        self.guncelle_btn = QPushButton("Siparişleri Yenile")
        self.guncelle_btn.clicked.connect(self.load_siparisler)
        layout.addWidget(self.guncelle_btn)
        return page
        
    def show_siparisler_page(self):
        self.stacked_content.setCurrentWidget(self.siparisler_page)
        self.load_siparisler()

    def load_siparisler(self):
        siparisler = self.session.query(Siparis).options(joinedload(Siparis.kullanici)).order_by(Siparis.tarih.desc()).all()
        self.siparis_table.setRowCount(len(siparisler))

        for i, siparis in enumerate(siparisler):
            kullanici_adi = siparis.kullanici.kullanici_adi if siparis.kullanici else "Bilinmiyor"
            
            self.siparis_table.setItem(i, 0, QTableWidgetItem(str(siparis.id)))
            self.siparis_table.setItem(i, 1, QTableWidgetItem(kullanici_adi))
            self.siparis_table.setItem(i, 2, QTableWidgetItem(siparis.tarih.strftime("%Y-%m-%d %H:%M")))
            self.siparis_table.setItem(i, 3, QTableWidgetItem(f"{siparis.toplam_tutar:.2f} ₺"))
            self.siparis_table.setItem(i, 4, QTableWidgetItem(siparis.durum))

    # --- Raporlama Metotları ---
    
    def create_raporlama_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>📊 Raporlama Ekranı</h2>"))
        
        self.rapor_btn_layout = QBtnLayout()
        self.rapor_yenile_btn = QPushButton("Raporları Yenile")
        self.rapor_yenile_btn.clicked.connect(lambda: (self.load_stok_raporu(), self.load_satis_raporu()))
        self.btn_rapor_yazdir = QPushButton("PDF Raporu Oluştur")
        self.btn_rapor_yazdir.clicked.connect(self.generate_yonetici_pdf)
        
        self.rapor_btn_layout.addWidget(self.rapor_yenile_btn)
        self.rapor_btn_layout.addWidget(self.btn_rapor_yazdir)
        layout.addLayout(self.rapor_btn_layout)
        
        # 1. Kritik Stok Raporu
        layout.addWidget(QLabel("<h3>Kritik Stok Seviyesi (< 5 Adet)</h3>"))
        self.stok_raporu_table = QTableWidget()
        self.stok_raporu_table.setColumnCount(3)
        self.stok_raporu_table.setHorizontalHeaderLabels(["Ürün Adı", "Barkod", "Stok"])
        self.stok_raporu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.stok_raporu_table)

        # 2. Genel Satış Raporu
        layout.addWidget(QLabel("<h3>Genel Satış Özeti</h3>"))
        
        self.toplam_satis_label = QLabel("Toplam Satılan Ürün: 0 | Toplam Gelir: 0.00 ₺")
        layout.addWidget(self.toplam_satis_label)
        
        self.personel_satis_table = QTableWidget()
        self.personel_satis_table.setColumnCount(3)
        self.personel_satis_table.setHorizontalHeaderLabels(["Çalışan", "Satış Sayısı", "Toplam Ciro"])
        self.personel_satis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.personel_satis_table)
        
        return page

    def show_raporlama_page(self):
        self.stacked_content.setCurrentWidget(self.raporlama_page)
        self.load_stok_raporu()
        self.load_satis_raporu() 

    def load_stok_raporu(self):
        kritik_stok_urunler = self.session.query(Urun).filter(Urun.stok < 5).order_by(Urun.stok.asc()).all()
        self.stok_raporu_table.setRowCount(len(kritik_stok_urunler))
        
        for i, urun in enumerate(kritik_stok_urunler):
            self.stok_raporu_table.setItem(i, 0, QTableWidgetItem(urun.isim))
            self.stok_raporu_table.setItem(i, 1, QTableWidgetItem(urun.barkod))
            self.stok_raporu_table.setItem(i, 2, QTableWidgetItem(str(urun.stok)))

    def load_satis_raporu(self):
        genel_satis_sonuc = self.session.query( 
            func.count(Satis.id), 
            func.sum(Satis.toplam_tutar)
        ).one_or_none() 

        toplam_adet = self.session.query(func.sum(SatisDetay.adet)).scalar() or 0
        
        if genel_satis_sonuc and genel_satis_sonuc[0] > 0:
            toplam_satis_sayisi = genel_satis_sonuc[0]
            toplam_gelir = genel_satis_sonuc[1] if genel_satis_sonuc[1] else 0.0
        else:
            toplam_satis_sayisi = 0
            toplam_gelir = 0.0
            
        self.toplam_satis_label.setText(
            f"Toplam Satılan Ürün: {toplam_adet} | Toplam Gelir: <b>{toplam_gelir:.2f} ₺</b>"
        )
        
        # Çalışan Bazlı Satış Raporu
        personel_satis_sonuclari = self.session.query(
            Kullanici.kullanici_adi, 
            func.count(Satis.id), 
            func.sum(Satis.toplam_tutar)
        ).join(Satis, Kullanici.id == Satis.calisan_id).group_by(Kullanici.kullanici_adi).all()

        self.personel_satis_table.setRowCount(len(personel_satis_sonuclari))
        
        for i, (ad, sayi, tutar) in enumerate(personel_satis_sonuclari):
            self.personel_satis_table.setItem(i, 0, QTableWidgetItem(ad))
            self.personel_satis_table.setItem(i, 1, QTableWidgetItem(str(sayi)))
            self.personel_satis_table.setItem(i, 2, QTableWidgetItem(f"{tutar:.2f} ₺"))

    def generate_yonetici_pdf(self):
        
        kritik_stok_urunler = self.session.query(Urun).filter(Urun.stok < 5).order_by(Urun.stok.asc()).all()
        
        personel_satis_sonuclari = self.session.query(
            Kullanici.kullanici_adi, 
            func.count(Satis.id), 
            func.sum(Satis.toplam_tutar)
        ).join(Satis, Kullanici.id == Satis.calisan_id).group_by(Kullanici.kullanici_adi).all()
        
        genel_satis_sonuc = self.session.query(func.sum(SatisDetay.adet)).scalar() or 0
        genel_ciro = self.session.query(func.sum(Satis.toplam_tutar)).scalar() or 0.0
        
        
        tarih_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Yonetici_Raporu_{tarih_str}.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        
        story.append(Paragraph("<b>AKILLI MARKET YÖNETİCİ RAPORU</b>", styles['Title']))
        story.append(Paragraph(f"Tarih: {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 24))

        
        story.append(Paragraph("<b>1. Genel Satış Özeti</b>", styles['h2']))
        story.append(Paragraph(f"Toplam Satılan Ürün Adedi: <b>{genel_satis_sonuc}</b>", styles['BodyText']))
        story.append(Paragraph(f"Toplam Elde Edilen Ciro: <b>{genel_ciro:.2f} ₺</b>", styles['BodyText']))
        story.append(Spacer(1, 18))

        
        story.append(Paragraph("<b>2. Kritik Stok Raporu (< 5 Adet)</b>", styles['h2']))
        if kritik_stok_urunler:
            stok_data = [["Ürün Adı", "Barkod", "Stok"]]
            for urun in kritik_stok_urunler:
                stok_data.append([urun.isim, urun.barkod, str(urun.stok)])
            
            t = Table(stok_data, colWidths=[200, 150, 100])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("<i>Kritik stok seviyesinde ürün bulunmamaktadır.</i>", styles['Italic']))
        story.append(Spacer(1, 18))

        
        story.append(Paragraph("<b>3. Çalışan Bazlı Performans</b>", styles['h2']))
        if personel_satis_sonuclari:
            personel_data = [["Çalışan Adı", "Satış Sayısı", "Toplam Ciro (₺)"]]
            for ad, sayi, tutar in personel_satis_sonuclari:
                personel_data.append([ad, str(sayi), f"{tutar:.2f}"])
                
            t = Table(personel_data, colWidths=[150, 100, 150])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("<i>Henüz çalışan satışı kaydedilmemiştir.</i>", styles['Italic']))

        
        doc.build(story)
        
        QMessageBox.information(self, "PDF Oluşturuldu", 
                                f"Yönetici Raporu başarıyla oluşturuldu: <b>{filename}</b>\nDosya konumu: {os.getcwd()}")


    
    def create_urun_yonetim_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>📦 Ürün Yönetimi (Ekle/Düzenle/Sil)</h2>"))

        self.urun_table = QTableWidget()
        self.urun_table.setColumnCount(6)
        self.urun_table.setHorizontalHeaderLabels(["ID", "Barkod", "İsim", "Stok", "Fiyat", "İşlemler"])
        self.urun_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.urun_table)
        
        btn_layout = QBtnLayout()
        self.btn_yeni_urun = QPushButton("➕ Yeni Ürün Ekle")
        self.btn_yeni_urun.clicked.connect(self.open_urun_ekle)
        
        btn_layout.addWidget(self.btn_yeni_urun)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return page

    def show_urun_yonetim_page(self):
        self.stacked_content.setCurrentWidget(self.urun_yonetim_page)
        self.load_urunler()

    def load_urunler(self):
        urunler = self.session.query(Urun).all()
        self.urun_table.setRowCount(len(urunler))
        
        for i, urun in enumerate(urunler):
            self.urun_table.setItem(i, 0, QTableWidgetItem(str(urun.id)))
            self.urun_table.setItem(i, 1, QTableWidgetItem(urun.barkod))
            self.urun_table.setItem(i, 2, QTableWidgetItem(urun.isim))
            self.urun_table.setItem(i, 3, QTableWidgetItem(str(urun.stok)))
            self.urun_table.setItem(i, 4, QTableWidgetItem(f"{urun.fiyat:.2f} ₺"))

            islem_widget = QWidget()
            islem_layout = QBtnLayout(islem_widget)
            islem_layout.setContentsMargins(0,0,0,0)
            
            edit_btn = QPushButton("Düzenle")
            edit_btn.clicked.connect(lambda checked, u=urun: self.open_urun_duzenle(u))
            
            delete_btn = QPushButton("Sil")
            delete_btn.clicked.connect(lambda checked, u=urun: self.delete_urun(u))
            
            islem_layout.addWidget(edit_btn)
            islem_layout.addWidget(delete_btn)
            self.urun_table.setCellWidget(i, 5, islem_widget)

    def open_urun_ekle(self):
        dialog = UrunEkleDuzenleDialog(self.session, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_urunler() 

    def open_urun_duzenle(self, urun):
        dialog = UrunEkleDuzenleDialog(self.session, urun=urun, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_urunler() 

    def delete_urun(self, urun):
        cevap = QMessageBox.question(self, "Silme Onayı", 
                                     f"'{urun.isim}' adlı ürünü silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if cevap == QMessageBox.Yes:
            try:
                self.session.delete(urun)
                self.session.commit()
                QMessageBox.information(self, "Başarılı", "Ürün başarıyla silindi.")
                self.load_urunler()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Hata", f"Ürün silinirken hata oluştu: {e}")