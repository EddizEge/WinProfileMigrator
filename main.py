"""
WinProfile Migrator - Windows Profil Taşıma & Klonlama Aracı
Ana giriş noktası.
"""
import sys
import os

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.helpers import setup_logging, is_admin, request_admin


def main():
    """Uygulamayı başlat."""
    # Yönetici yetkisi kontrolü ve talebi
    if not is_admin():
        print("Yönetici yetkisi isteniyor...")
        request_admin()
        # request_admin başarılı olursa programı yeniden başlatıp sys.exit(0) çağırır.
        # Eğer buraya ulaşırsa kullanıcı UAC (Evet/Hayır) ekranında Hayır demiştir.
        print("Yönetici yetkisi verilmedi, normal kullanıcı olarak devam ediliyor.")

    # Loglama sistemini kur
    log_file = setup_logging()
    print(f"Log dosyası: {log_file}")

    # Ana uygulamayı başlat
    from app import WinProfileMigrator

    app = WinProfileMigrator()
    app.mainloop()


if __name__ == "__main__":
    main()
