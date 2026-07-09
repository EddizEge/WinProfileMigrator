# WinProfileMigrator - Windows Profile Migration & Cloning Tool

WinProfileMigrator is a modern and lightweight utility designed to backup, restore, clone, and transfer Windows user profiles easily. It features direct network migration between two PCs, offline exporting, and profile cloning.

---

## 🚀 Features (EN)

- **Profile Export**: Export selected user profile components as a compressed package.
- **Profile Import**: Restore previously exported user profiles.
- **Network Transfer**: Transfer profiles directly between two computers over the network in real-time with speed and progress indicators.
- **Profile Cloning**: Copy an existing local user profile to create a new local user account on the same machine.
- **Auto Elevation**: Automatically prompts for Administrator privileges to ensure complete system access.

## 📦 Migratable Components (EN)

- User folders (Desktop, Documents, Downloads, Pictures, Music, Videos)
- App Settings (AppData - Local & Roaming)
- Registry Configurations (HKCU Registry Hive)
- Wi-Fi Profiles
- Printer Settings
- System Environment Variables
- Wallpaper & Theme Settings
- Taskbar & Start Menu Pins

## 📥 Getting Started / Installation (EN)

### Method 1: Pre-compiled Executable (Recommended)
You can download the latest standalone executable from [Releases](https://github.com/EddizEge/WinProfileMigrator/releases) page. No installation or Python setup is required. Just download and run it as Administrator.

### Method 2: Running from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/EddizEge/WinProfileMigrator.git
   cd WinProfileMigrator
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## 📋 Requirements (EN)

- Windows 10/11
- Python 3.9+ (if running from source)
- Administrator Privileges (required for registry, network, and profile directories access)

---

# WinProfileMigrator - Windows Profil Taşıma & Klonlama Aracı

WinProfileMigrator, Windows kullanıcı profillerini kolayca yedeklemek, geri yüklemek, klonlamak ve aktarmak için tasarlanmış modern ve hafif bir araçtır. İki bilgisayar arasında doğrudan ağ üzerinden aktarım, çevrimdışı dışa aktarma ve profil klonlama özelliklerine sahiptir.

---

## 🚀 Özellikler (TR)

- **Profil Dışa Aktarma**: Seçili profil bileşenlerini sıkıştırılmış paket olarak dışa aktarın.
- **Profil İçe Aktarma**: Daha önce dışa aktarılan profilleri geri yükleyin.
- **Ağ Transferi**: Hız ve ilerleme göstergeleriyle iki bilgisayar arasında doğrudan ağ üzerinden gerçek zamanlı profil aktarın.
- **Profil Klonlama**: Mevcut profili kopyalayarak aynı makinede yeni bir yerel kullanıcı hesabı oluşturun.
- **Otomatik Yetki Yükseltme**: Tam sistem erişimi sağlamak için otomatik olarak Yönetici (Administrator) yetkileri ister.

## 📦 Taşınabilir Bileşenler (TR)

- Kullanıcı klasörleri (Masaüstü, Belgeler, İndirilenler, Resimler, Müzik, Videolar)
- Uygulama Ayarları (AppData - Local & Roaming)
- Kayıt Defteri Ayarları (HKCU Registry kovanı)
- Kayıtlı Wi-Fi Profilleri
- Yazıcı Ayarları
- Sistem Ortam Değişkenleri
- Duvar Kağıdı ve Tema Ayarları
- Görev Çubuğu ve Başlat Menüsü Pinleri

## 📥 Kurulum ve Çalıştırma (TR)

### Yöntem 1: Hazır Derlenmiş Program (Önerilen)
En güncel tek parça `.exe` dosyasını [Releases (Sürümler)](https://github.com/EddizEge/WinProfileMigrator/releases) sayfasından indirebilirsiniz. Herhangi bir kurulum veya Python kurulumu gerektirmez. Sadece indirin ve Yönetici olarak çalıştırın.

### Yöntem 2: Kaynak Koddan Çalıştırma
1. Depoyu klonlayın:
   ```bash
   git clone https://github.com/EddizEge/WinProfileMigrator.git
   cd WinProfileMigrator
   ```
2. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. Uygulamayı çalıştırın:
   ```bash
   python main.py
   ```

## 📋 Gereksinimler (TR)

- Windows 10/11
- Python 3.9+ (kaynak koddan çalıştırılacaksa)
- Yönetici yetkileri (kayıt defteri, ağ ve profil dizinlerine erişim için gereklidir)

---
*Developed by Ediz Ege Mercan*
