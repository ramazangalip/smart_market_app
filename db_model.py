

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import hashlib

Base = declarative_base()

class Kullanici(Base):
    __tablename__ = 'kullanicilar'
    id = Column(Integer, primary_key=True)
    kullanici_adi = Column(String, unique=True, nullable=False)
    sifre_hash = Column(String, nullable=False) 
    rol = Column(String, nullable=False) 
    

    calisan_bilgisi = relationship("CalisanBilgisi", uselist=False, back_populates="kullanici")
    siparisler = relationship("Siparis", back_populates="kullanici")
    satislar = relationship("Satis", back_populates="calisan") 

    def set_sifre(self, sifre):
        self.sifre_hash = hashlib.sha256(sifre.encode('utf-8')).hexdigest()
    
    def check_sifre(self, sifre):
        return self.sifre_hash == hashlib.sha256(sifre.encode('utf-8')).hexdigest()


class CalisanBilgisi(Base):
    __tablename__ = 'calisan_bilgileri'
    id = Column(Integer, primary_key=True)
    kullanici_id = Column(Integer, ForeignKey('kullanicilar.id'), unique=True)
    maas = Column(Float, default=0.0)
    pozisyon = Column(String) 

    kullanici = relationship("Kullanici", back_populates="calisan_bilgisi")


class Urun(Base):
    __tablename__ = 'urunler'
    id = Column(Integer, primary_key=True)
    barkod = Column(String, unique=True, nullable=False)
    isim = Column(String, nullable=False)
    stok = Column(Integer, default=0)
    fiyat = Column(Float)

class Siparis(Base):
    __tablename__ = 'siparisler'
    id = Column(Integer, primary_key=True)
    kullanici_id = Column(Integer, ForeignKey('kullanicilar.id')) 
    tarih = Column(DateTime, default=datetime.now)
    toplam_tutar = Column(Float, default=0.0)
    durum = Column(String, default='Bekleniyor') 

    kullanici = relationship("Kullanici", back_populates="siparisler")
    detaylar = relationship("SiparisDetay", back_populates="siparis")

class SiparisDetay(Base):
    __tablename__ = 'siparis_detaylari'
    id = Column(Integer, primary_key=True)
    siparis_id = Column(Integer, ForeignKey('siparisler.id'))
    urun_id = Column(Integer, ForeignKey('urunler.id'))
    adet = Column(Integer)
    birim_fiyat = Column(Float) 

    siparis = relationship("Siparis", back_populates="detaylar")
    urun = relationship("Urun")


class Satis(Base):
    __tablename__ = 'satislar'
    id = Column(Integer, primary_key=True)
    calisan_id = Column(Integer, ForeignKey('kullanicilar.id'))
    tarih = Column(DateTime, default=datetime.now)
    toplam_tutar = Column(Float, default=0.0)
    
    calisan = relationship("Kullanici", back_populates="satislar")
    detaylar = relationship("SatisDetay", back_populates="satis")

class SatisDetay(Base):
    __tablename__ = 'satis_detaylari'
    id = Column(Integer, primary_key=True)
    satis_id = Column(Integer, ForeignKey('satislar.id'))
    urun_id = Column(Integer, ForeignKey('urunler.id'))
    adet = Column(Integer)
    birim_fiyat = Column(Float) 

    satis = relationship("Satis", back_populates="detaylar")
    urun = relationship("Urun")



ENGINE = create_engine('sqlite:///akilli_market.db') 
Base.metadata.create_all(ENGINE) 

Session = sessionmaker(bind=ENGINE)