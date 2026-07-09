"""
WinProfileMigrator - Registry İşleyici
Windows Registry yedekleme ve geri yükleme işlemleri.
"""
import os
import json
import logging
import subprocess
import winreg
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("WinProfileMigrator.registry")


class RegistryHandler:
    """Windows Registry işlemleri."""

    # Yedeklenecek önemli HKCU alt anahtarları
    IMPORTANT_KEYS = [
        r"Software\Microsoft\Windows\CurrentVersion\Explorer",
        r"Software\Microsoft\Windows\CurrentVersion\Themes",
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
        r"Control Panel\Desktop",
        r"Control Panel\Colors",
        r"Control Panel\Mouse",
        r"Control Panel\Keyboard",
        r"Control Panel\International",
        r"Environment",
        r"Software\Microsoft\Windows\CurrentVersion\Applets",
        r"Console",
        r"Software\Microsoft\Notepad",
        r"Software\Microsoft\Calc",
    ]

    THEME_KEYS = [
        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        r"Software\Microsoft\Windows\DWM",
        r"Control Panel\Desktop",
        r"Control Panel\Colors",
    ]

    ENV_KEY = r"Environment"

    def __init__(self):
        pass

    def export_registry(self, export_path: Path, keys: List[str] = None,
                         callback=None) -> bool:
        """Registry anahtarlarını .reg dosyası olarak dışa aktar."""
        if keys is None:
            keys = self.IMPORTANT_KEYS

        export_path.mkdir(parents=True, exist_ok=True)
        success_count = 0
        total = len(keys)

        for i, key_path in enumerate(keys):
            try:
                safe_name = key_path.replace("\\", "_").replace(" ", "_")
                reg_file = export_path / f"{safe_name}.reg"

                full_key = f"HKEY_CURRENT_USER\\{key_path}"
                result = subprocess.run(
                    ["reg", "export", full_key, str(reg_file), "/y"],
                    capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0:
                    success_count += 1
                    logger.info("Registry dışa aktarıldı: %s", key_path)
                else:
                    logger.warning("Registry dışa aktarılamadı: %s - %s",
                                   key_path, result.stderr.strip())

                if callback:
                    callback(i + 1, total, key_path)

            except subprocess.TimeoutExpired:
                logger.error("Registry dışa aktarma zaman aşımı: %s", key_path)
            except Exception as e:
                logger.error("Registry dışa aktarma hatası (%s): %s", key_path, e)

        logger.info("Registry dışa aktarma tamamlandı: %d/%d başarılı",
                     success_count, total)
        return success_count > 0

    def import_registry(self, import_path: Path, callback=None) -> bool:
        """Registry anahtarlarını .reg dosyalarından içe aktar."""
        if not import_path.exists():
            logger.error("Registry içe aktarma dizini bulunamadı: %s", import_path)
            return False

        reg_files = list(import_path.glob("*.reg"))
        if not reg_files:
            logger.warning("İçe aktarılacak .reg dosyası bulunamadı")
            return False

        success_count = 0
        total = len(reg_files)

        for i, reg_file in enumerate(reg_files):
            try:
                result = subprocess.run(
                    ["reg", "import", str(reg_file)],
                    capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0:
                    success_count += 1
                    logger.info("Registry içe aktarıldı: %s", reg_file.name)
                else:
                    logger.warning("Registry içe aktarılamadı: %s - %s",
                                   reg_file.name, result.stderr.strip())

                if callback:
                    callback(i + 1, total, reg_file.name)

            except subprocess.TimeoutExpired:
                logger.error("Registry içe aktarma zaman aşımı: %s", reg_file.name)
            except Exception as e:
                logger.error("Registry içe aktarma hatası (%s): %s", reg_file.name, e)

        logger.info("Registry içe aktarma tamamlandı: %d/%d başarılı",
                     success_count, total)
        return success_count > 0

    def export_theme_settings(self, export_path: Path) -> bool:
        """Tema ve duvar kağıdı ayarlarını dışa aktar."""
        return self.export_registry(export_path / "theme", self.THEME_KEYS)

    def import_theme_settings(self, import_path: Path) -> bool:
        """Tema ve duvar kağıdı ayarlarını içe aktar."""
        return self.import_registry(import_path / "theme")

    def export_env_variables(self, export_path: Path) -> bool:
        """Kullanıcı ortam değişkenlerini JSON olarak dışa aktar."""
        env_vars = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.ENV_KEY) as key:
                i = 0
                while True:
                    try:
                        name, value, reg_type = winreg.EnumValue(key, i)
                        env_vars[name] = {
                            "value": value,
                            "type": reg_type,
                        }
                        i += 1
                    except OSError:
                        break

            export_path.mkdir(parents=True, exist_ok=True)
            env_file = export_path / "env_variables.json"
            with open(env_file, "w", encoding="utf-8") as f:
                json.dump(env_vars, f, ensure_ascii=False, indent=2)

            logger.info("Ortam değişkenleri dışa aktarıldı: %d değişken", len(env_vars))
            return True

        except Exception as e:
            logger.error("Ortam değişkenleri dışa aktarılamadı: %s", e)
            return False

    def import_env_variables(self, import_path: Path) -> bool:
        """Kullanıcı ortam değişkenlerini JSON'dan içe aktar."""
        env_file = import_path / "env_variables.json"
        if not env_file.exists():
            logger.error("Ortam değişkenleri dosyası bulunamadı: %s", env_file)
            return False

        try:
            with open(env_file, "r", encoding="utf-8") as f:
                env_vars = json.load(f)

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.ENV_KEY,
                                0, winreg.KEY_SET_VALUE) as key:
                for name, info in env_vars.items():
                    try:
                        winreg.SetValueEx(key, name, 0, info["type"], info["value"])
                        logger.info("Ortam değişkeni ayarlandı: %s", name)
                    except Exception as e:
                        logger.warning("Ortam değişkeni ayarlanamadı (%s): %s", name, e)

            logger.info("Ortam değişkenleri içe aktarıldı: %d değişken", len(env_vars))
            return True

        except Exception as e:
            logger.error("Ortam değişkenleri içe aktarılamadı: %s", e)
            return False

    def export_wallpaper_info(self, export_path: Path) -> bool:
        """Duvar kağıdı bilgisini dışa aktar."""
        try:
            wallpaper_info = {}

            # Mevcut duvar kağıdı yolu
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Control Panel\Desktop") as key:
                try:
                    wallpaper_path, _ = winreg.QueryValueEx(key, "Wallpaper")
                    wallpaper_info["wallpaper_path"] = wallpaper_path

                    # Duvar kağıdı dosyasını kopyala
                    if wallpaper_path and Path(wallpaper_path).exists():
                        import shutil
                        wp_dir = export_path / "wallpaper"
                        wp_dir.mkdir(parents=True, exist_ok=True)
                        dest = wp_dir / Path(wallpaper_path).name
                        shutil.copy2(wallpaper_path, dest)
                        wallpaper_info["wallpaper_file"] = Path(wallpaper_path).name
                except OSError:
                    pass

                try:
                    style, _ = winreg.QueryValueEx(key, "WallpaperStyle")
                    wallpaper_info["wallpaper_style"] = style
                except OSError:
                    pass

                try:
                    tile, _ = winreg.QueryValueEx(key, "TileWallpaper")
                    wallpaper_info["tile_wallpaper"] = tile
                except OSError:
                    pass

            export_path.mkdir(parents=True, exist_ok=True)
            wp_info_file = export_path / "wallpaper_info.json"
            with open(wp_info_file, "w", encoding="utf-8") as f:
                json.dump(wallpaper_info, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            logger.error("Duvar kağıdı bilgisi dışa aktarılamadı: %s", e)
            return False

    def backup_current_registry(self, backup_path: Path) -> bool:
        """Mevcut registry ayarlarının yedeğini al."""
        backup_path.mkdir(parents=True, exist_ok=True)
        return self.export_registry(backup_path, self.IMPORTANT_KEYS)
