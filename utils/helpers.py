"""
WinProfileMigrator - Yardımcı fonksiyonlar
"""
import os
import sys
import ctypes
import logging
import platform
import subprocess
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("WinProfileMigrator")


def setup_logging(log_dir: Path = None, level: int = logging.INFO):
    """Loglama sistemini kur."""
    if log_dir is None:
        log_dir = Path.home() / ".WinProfileMigrator" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"migrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    root_logger = logging.getLogger("WinProfileMigrator")
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info("Loglama sistemi başlatıldı: %s", log_file)
    return log_file


def is_admin() -> bool:
    """Uygulamanın yönetici yetkisiyle çalışıp çalışmadığını kontrol et."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin():
    """Yönetici yetkisi ile yeniden başlat."""
    if is_admin():
        return True
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)
    except Exception as e:
        logger.error("Yönetici yetkisi alınamadı: %s", e)
        return False


def get_size_display(size_bytes: int) -> str:
    """Boyutu okunabilir formata çevir."""
    if size_bytes < 0:
        return "Bilinmiyor"
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.1f} {units[i]}"


def get_dir_size(path: Path) -> int:
    """Bir dizinin toplam boyutunu hesapla (Junctions, Symlinks, Reparse Points yoksayılır)."""
    total = 0
    try:
        if path.is_file():
            return path.stat().st_size
            
        stack = [str(path)]
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        FILE_ATTRIBUTE_SPARSE_FILE = 0x200
        FILE_ATTRIBUTE_OFFLINE = 0x1000
        
        while stack:
            current = stack.pop()
            try:
                for entry in os.scandir(current):
                    try:
                        # Reparse point (Junction, Symlink vb.), Sparse File veya Offline (Bulut) dosyası kontrolü
                        st = entry.stat(follow_symlinks=False)
                        attrs = getattr(st, 'st_file_attributes', 0)
                        if attrs & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_SPARSE_FILE | FILE_ATTRIBUTE_OFFLINE):
                            continue
                            
                        if entry.is_file(follow_symlinks=False):
                            total += st.st_size
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except OSError:
                        pass
            except OSError:
                pass
    except OSError:
        return -1
    return total


def get_system_info() -> dict:
    """Sistem bilgilerini topla."""
    import psutil

    info = {
        "bilgisayar_adi": platform.node(),
        "isletim_sistemi": f"{platform.system()} {platform.release()}",
        "isletim_sistemi_versiyon": platform.version(),
        "mimari": platform.machine(),
        "islemci": platform.processor(),
        "kullanici": os.environ.get("USERNAME", "Bilinmiyor"),
        "kullanici_profil": str(Path.home()),
    }

    # Disk bilgileri
    try:
        disk = psutil.disk_usage(str(Path.home().anchor))
        info["disk_toplam"] = disk.total
        info["disk_kullanilan"] = disk.used
        info["disk_bos"] = disk.free
        info["disk_yuzde"] = disk.percent
    except Exception:
        info["disk_toplam"] = 0
        info["disk_kullanilan"] = 0
        info["disk_bos"] = 0
        info["disk_yuzde"] = 0

    # RAM bilgileri
    try:
        ram = psutil.virtual_memory()
        info["ram_toplam"] = ram.total
        info["ram_kullanilan"] = ram.used
        info["ram_yuzde"] = ram.percent
    except Exception:
        info["ram_toplam"] = 0
        info["ram_kullanilan"] = 0
        info["ram_yuzde"] = 0

    return info


def get_wifi_profiles() -> list:
    """Kayıtlı Wi-Fi profil isimlerini listele."""
    profiles = []
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True, text=True, encoding="cp857", errors="replace"
        )
        for line in result.stdout.split("\n"):
            if "Tüm Kullanıcı Profili" in line or "All User Profile" in line:
                name = line.split(":", 1)[-1].strip()
                if name:
                    profiles.append(name)
    except Exception as e:
        logger.error("Wi-Fi profilleri alınamadı: %s", e)
    return profiles


def export_wifi_profile(profile_name: str, export_dir: Path) -> bool:
    """Bir Wi-Fi profilini XML olarak dışa aktar."""
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["netsh", "wlan", "export", "profile",
             f"name={profile_name}", f"folder={export_dir}", "key=clear"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error("Wi-Fi profili dışa aktarılamadı (%s): %s", profile_name, e)
        return False


def import_wifi_profile(xml_path: Path) -> bool:
    """Bir Wi-Fi profilini XML'den içe aktar."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "add", "profile", f"filename={xml_path}", "user=all"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error("Wi-Fi profili içe aktarılamadı (%s): %s", xml_path, e)
        return False


def get_environment_variables(user_only: bool = True) -> dict:
    """Ortam değişkenlerini al."""
    import winreg
    env_vars = {}
    try:
        if user_only:
            key_path = r"Environment"
            root = winreg.HKEY_CURRENT_USER
        else:
            key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
            root = winreg.HKEY_LOCAL_MACHINE

        with winreg.OpenKey(root, key_path) as key:
            i = 0
            while True:
                try:
                    name, value, reg_type = winreg.EnumValue(key, i)
                    env_vars[name] = {"value": value, "type": reg_type}
                    i += 1
                except OSError:
                    break
    except Exception as e:
        logger.error("Ortam değişkenleri alınamadı: %s", e)
    return env_vars


def get_app_data_dir() -> Path:
    """Uygulama ayar dizinini döndür."""
    app_dir = Path.home() / ".WinProfileMigrator"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def load_settings() -> dict:
    """Uygulama ayarlarını yükle."""
    import json
    settings_file = get_app_data_dir() / "settings.json"
    defaults = {
        "export_location": str(Path.home() / "Desktop"),
        "compression_level": "normal",  # fast, normal, maximum
        "auto_backup": True,
        "log_level": "INFO",
        "theme": "dark",
        "recent_operations": [],
    }
    try:
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
    except Exception as e:
        logger.error("Ayarlar yüklenemedi: %s", e)
    return defaults


def save_settings(settings: dict):
    """Uygulama ayarlarını kaydet."""
    import json
    settings_file = get_app_data_dir() / "settings.json"
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Ayarlar kaydedilemedi: %s", e)


def add_recent_operation(settings: dict, operation: dict):
    """Son işlemler listesine bir işlem ekle."""
    operation["tarih"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "recent_operations" not in settings:
        settings["recent_operations"] = []
    settings["recent_operations"].insert(0, operation)
    # Son 20 işlemi tut
    settings["recent_operations"] = settings["recent_operations"][:20]
    save_settings(settings)
