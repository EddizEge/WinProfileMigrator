"""
WinProfileMigrator - Profil İçe Aktarıcı
ZIP paketinden profil bileşenlerini geri yükler.
"""
import os
import json
import shutil
import logging
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable, Optional

from core.registry_handler import RegistryHandler
from utils.helpers import import_wifi_profile, get_size_display

logger = logging.getLogger("WinProfileMigrator.importer")


class ProfileImporter:
    """ZIP paketinden profil bileşenlerini içe aktarır."""

    def __init__(self):
        self.registry_handler = RegistryHandler()
        self._cancelled = False

    def cancel(self):
        """İçe aktarma işlemini iptal et."""
        self._cancelled = True

    def read_package(self, zip_path: Path) -> Optional[Dict]:
        """ZIP paketinin manifest bilgisini oku."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                if "manifest.json" not in zf.namelist():
                    logger.error("Geçersiz paket: manifest.json bulunamadı")
                    return None

                with zf.open("manifest.json") as mf:
                    manifest = json.load(mf)

                # Paket boyutu ekle
                manifest["package_size"] = zip_path.stat().st_size
                manifest["package_size_display"] = get_size_display(zip_path.stat().st_size)
                manifest["package_path"] = str(zip_path)

                return manifest

        except zipfile.BadZipFile:
            logger.error("Bozuk ZIP dosyası: %s", zip_path)
            return None
        except Exception as e:
            logger.error("Paket okuma hatası: %s", e)
            return None

    def import_profile(self, zip_path: Path, selected_ids: List[str],
                        target_profile_path: Path = None,
                        auto_backup: bool = True,
                        progress_callback: Optional[Callable] = None) -> bool:
        """
        ZIP paketinden seçili bileşenleri içe aktar.

        Args:
            zip_path: Kaynak ZIP dosyası
            selected_ids: İçe aktarılacak bileşen ID'leri
            target_profile_path: Hedef profil dizini (None = mevcut kullanıcı)
            auto_backup: İçe aktarmadan önce otomatik yedek al
            progress_callback: İlerleme callback(current, total, message)
        """
        self._cancelled = False

        if target_profile_path is None:
            target_profile_path = Path.home()

        # Manifest oku
        manifest = self.read_package(zip_path)
        if not manifest:
            return False

        available_components = [c for c in manifest.get("components", [])
                                if c["id"] in selected_ids and c.get("success", False)]

        if not available_components:
            logger.warning("İçe aktarılacak başarılı bileşen bulunamadı")
            return False

        total_steps = len(available_components) + (1 if auto_backup else 0)
        current_step = 0

        # Otomatik yedek
        if auto_backup:
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "🔄 Yedek oluşturuluyor...")
            self._create_backup(target_profile_path, selected_ids)

        # ZIP'i geçici dizine aç
        with tempfile.TemporaryDirectory(prefix="WPM_import_") as temp_dir:
            temp_path = Path(temp_dir)

            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(temp_path)
            except Exception as e:
                logger.error("ZIP açma hatası: %s", e)
                return False

            success_count = 0

            for comp_info in available_components:
                if self._cancelled:
                    logger.info("İçe aktarma iptal edildi")
                    return False

                current_step += 1
                comp_id = comp_info["id"]
                comp_name = comp_info["name"]

                if progress_callback:
                    progress_callback(current_step, total_steps,
                                       f"📥 {comp_name} içe aktarılıyor...")

                comp_dir = temp_path / comp_id
                if not comp_dir.exists():
                    logger.warning("Bileşen dizini bulunamadı: %s", comp_id)
                    continue

                try:
                    success = False

                    if comp_info.get("category") == "files":
                        success = self._import_folder(comp_dir, target_profile_path, comp_id)
                    elif comp_id == "appdata_roaming":
                        target = target_profile_path / "AppData" / "Roaming"
                        success = self._import_appdata(comp_dir, target)
                    elif comp_id == "appdata_local":
                        target = target_profile_path / "AppData" / "Local"
                        success = self._import_appdata(comp_dir, target)
                    elif comp_id == "registry":
                        success = self.registry_handler.import_registry(comp_dir)
                    elif comp_id == "wifi_profiles":
                        success = self._import_wifi(comp_dir)
                    elif comp_id == "env_variables":
                        success = self.registry_handler.import_env_variables(comp_dir)
                    elif comp_id == "wallpaper_theme":
                        success = self.registry_handler.import_theme_settings(comp_dir)
                    elif comp_id == "taskbar_startmenu":
                        success = self._import_taskbar_startmenu(comp_dir, target_profile_path)
                    elif comp_id == "printers":
                        success = self._import_printers(comp_dir)

                    if success:
                        success_count += 1
                        logger.info("Bileşen içe aktarıldı: %s", comp_name)
                    else:
                        logger.warning("Bileşen içe aktarılamadı: %s", comp_name)

                except Exception as e:
                    logger.error("Bileşen içe aktarma hatası (%s): %s", comp_id, e)

        logger.info("İçe aktarma tamamlandı: %d/%d başarılı",
                     success_count, len(available_components))
        return success_count > 0

    def _create_backup(self, profile_path: Path, component_ids: List[str]):
        """Mevcut profil bileşenlerinin yedeğini al."""
        from utils.helpers import get_app_data_dir

        backup_dir = (get_app_data_dir() / "backups" /
                      datetime.now().strftime("%Y%m%d_%H%M%S"))
        backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Yedek oluşturuluyor: %s", backup_dir)

        # Registry yedeği
        if "registry" in component_ids:
            self.registry_handler.backup_current_registry(backup_dir / "registry")

        # Env variables yedeği
        if "env_variables" in component_ids:
            self.registry_handler.export_env_variables(backup_dir / "env_variables")

        logger.info("Yedek oluşturuldu: %s", backup_dir)

    def _import_folder(self, source: Path, profile_path: Path, comp_id: str) -> bool:
        """Klasör bileşenini içe aktar."""
        folder_map = {
            "desktop": ["Desktop", "Masaüstü"],
            "documents": ["Documents", "Belgeler"],
            "downloads": ["Downloads", "İndirilenler"],
            "pictures": ["Pictures", "Resimler"],
            "music": ["Music", "Müzik"],
            "videos": ["Videos", "Videolar"],
        }

        target_names = folder_map.get(comp_id, [])
        target_dir = None

        for name in target_names:
            path = profile_path / name
            if path.exists():
                target_dir = path
                break

        if target_dir is None and target_names:
            target_dir = profile_path / target_names[0]
            target_dir.mkdir(parents=True, exist_ok=True)

        if target_dir is None:
            return False

        try:
            file_count = 0
            for item in source.rglob("*"):
                if self._cancelled:
                    return False
                if item.is_file():
                    rel_path = item.relative_to(source)
                    target = target_dir / rel_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(item, target)
                        file_count += 1
                    except (PermissionError, OSError) as e:
                        logger.debug("Dosya kopyalanamadı: %s - %s", item, e)
            return file_count > 0
        except Exception as e:
            logger.error("Klasör içe aktarma hatası: %s", e)
            return False

    def _import_appdata(self, source: Path, target: Path) -> bool:
        """AppData içe aktar."""
        try:
            file_count = 0
            for item in source.rglob("*"):
                if self._cancelled:
                    return False
                if item.is_file():
                    rel_path = item.relative_to(source)
                    dest = target / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(item, dest)
                        file_count += 1
                    except (PermissionError, OSError) as e:
                        logger.debug("AppData dosyası kopyalanamadı: %s - %s", item, e)
            return file_count > 0
        except Exception as e:
            logger.error("AppData içe aktarma hatası: %s", e)
            return False

    def _import_wifi(self, source: Path) -> bool:
        """Wi-Fi profillerini içe aktar."""
        wifi_dir = source / "wifi"
        if not wifi_dir.exists():
            wifi_dir = source  # Direkt source dizini kontrol et

        xml_files = list(wifi_dir.glob("*.xml"))
        if not xml_files:
            return False

        success_count = 0
        for xml_file in xml_files:
            if import_wifi_profile(xml_file):
                success_count += 1

        return success_count > 0

    def _import_taskbar_startmenu(self, source: Path, profile_path: Path) -> bool:
        """Görev çubuğu ve başlat menüsü içe aktar."""
        success = False

        # Görev çubuğu
        taskbar_src = source / "TaskBar"
        if taskbar_src.exists():
            target = (profile_path / "AppData" / "Roaming" /
                      "Microsoft" / "Internet Explorer" /
                      "Quick Launch" / "User Pinned" / "TaskBar")
            try:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copytree(taskbar_src, target, dirs_exist_ok=True)
                success = True
            except Exception as e:
                logger.warning("Görev çubuğu pinleri içe aktarılamadı: %s", e)

        # Başlat menüsü
        start_src = source / "StartMenu"
        if start_src.exists():
            target = (profile_path / "AppData" / "Roaming" /
                      "Microsoft" / "Windows" / "Start Menu")
            try:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copytree(start_src, target, dirs_exist_ok=True)
                success = True
            except Exception as e:
                logger.warning("Başlat menüsü içe aktarılamadı: %s", e)

        return success

    def _import_printers(self, source: Path) -> bool:
        """Yazıcı ayarlarını içe aktar (bilgilendirme amaçlı)."""
        printer_file = source / "printers.json"
        if not printer_file.exists():
            return False

        try:
            with open(printer_file, "r", encoding="utf-8") as f:
                printers = json.load(f)
            logger.info("Yazıcı bilgileri okundu: %s", printers)
            # Not: Yazıcı kurulumu genelde driver gerektirir, burada sadece bilgilendirme
            return True
        except Exception as e:
            logger.error("Yazıcı bilgileri okunamadı: %s", e)
            return False
