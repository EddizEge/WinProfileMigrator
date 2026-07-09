"""
WinProfileMigrator - Profil Dışa Aktarıcı
Seçili profil bileşenlerini ZIP paketi olarak dışa aktarır.
"""
import os
import json
import shutil
import logging
import zipfile
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Optional

from core.profile_scanner import ProfileComponent, UserProfile
from core.registry_handler import RegistryHandler
from utils.helpers import (
    export_wifi_profile, get_wifi_profiles, get_environment_variables,
    get_size_display
)

logger = logging.getLogger("WinProfileMigrator.exporter")


class ProfileExporter:
    """Profil bileşenlerini ZIP paketi olarak dışa aktarır."""

    def __init__(self):
        self.registry_handler = RegistryHandler()
        self._cancelled = False

    def cancel(self):
        """Dışa aktarma işlemini iptal et."""
        self._cancelled = True

    def export_profile(self, profile: UserProfile, selected_ids: List[str],
                        output_path: Path, compression: str = "normal",
                        progress_callback: Optional[Callable] = None) -> Optional[Path]:
        """
        Seçili bileşenleri ZIP olarak dışa aktar.

        Args:
            profile: Kaynak profil
            selected_ids: Seçili bileşen ID'leri
            output_path: Çıktı ZIP dosyası yolu
            compression: Sıkıştırma seviyesi (fast/normal/maximum)
            progress_callback: İlerleme callback(current_step, total_steps, message)

        Returns:
            Oluşturulan ZIP dosyasının yolu veya None
        """
        self._cancelled = False

        # Sıkıştırma seviyesi
        compression_map = {
            "fast": zipfile.ZIP_STORED,
            "normal": zipfile.ZIP_DEFLATED,
            "maximum": zipfile.ZIP_LZMA,
        }
        comp_type = compression_map.get(compression, zipfile.ZIP_DEFLATED)

        # Toplam adım sayısını hesapla
        selected_components = [c for c in profile.components if c.id in selected_ids]
        total_steps = len(selected_components) + 1  # +1 manifest için

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"WinProfile_{profile.username}_{timestamp}.wpkg"
        zip_path = output_path / zip_name

        # Geçici dizin oluştur
        with tempfile.TemporaryDirectory(prefix="WPM_") as temp_dir:
            temp_path = Path(temp_dir)
            manifest = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "source_computer": os.environ.get("COMPUTERNAME", "Bilinmiyor"),
                "source_user": profile.username,
                "source_os": os.environ.get("OS", "Bilinmiyor"),
                "components": [],
                "compression": compression,
            }

            current_step = 0

            for comp in selected_components:
                if self._cancelled:
                    logger.info("Dışa aktarma iptal edildi")
                    return None

                current_step += 1
                if progress_callback:
                    progress_callback(
                        current_step, total_steps,
                        f"{comp.icon} {comp.name} dışa aktarılıyor..."
                    )

                comp_dir = temp_path / comp.id
                comp_dir.mkdir(parents=True, exist_ok=True)

                success = False
                try:
                    if comp.category == "files" and comp.path:
                        success = self._export_folder(comp.path, comp_dir)
                    elif comp.id == "appdata_roaming":
                        success = self._export_appdata_roaming(comp.path, comp_dir)
                    elif comp.id == "appdata_local":
                        success = self._export_appdata_local(comp.path, comp_dir)
                    elif comp.id == "registry":
                        success = self.registry_handler.export_registry(comp_dir)
                    elif comp.id == "wifi_profiles":
                        success = self._export_wifi(comp_dir)
                    elif comp.id == "env_variables":
                        success = self.registry_handler.export_env_variables(comp_dir)
                    elif comp.id == "wallpaper_theme":
                        success = self.registry_handler.export_wallpaper_info(comp_dir)
                        theme_success = self.registry_handler.export_theme_settings(comp_dir)
                        success = success or theme_success
                    elif comp.id == "taskbar_startmenu":
                        success = self._export_taskbar_startmenu(profile.profile_path, comp_dir)
                    elif comp.id == "printers":
                        success = self._export_printers(comp_dir)
                    else:
                        logger.warning("Bilinmeyen bileşen: %s", comp.id)
                except Exception as e:
                    logger.error("Bileşen dışa aktarma hatası (%s): %s", comp.id, e)

                manifest["components"].append({
                    "id": comp.id,
                    "name": comp.name,
                    "category": comp.category,
                    "success": success,
                })

            # Manifest dosyasını yaz
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "📋 Paket oluşturuluyor...")

            manifest_file = temp_path / "manifest.json"
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            # ZIP oluştur
            try:
                output_path.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, "w", comp_type) as zf:
                    for root, dirs, files in os.walk(temp_path):
                        for file in files:
                            if self._cancelled:
                                return None
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(temp_path)
                            try:
                                zf.write(file_path, arcname)
                            except (PermissionError, OSError) as e:
                                logger.warning("Dosya ZIP'e eklenemedi: %s - %s", file_path, e)

                logger.info("Profil paketi oluşturuldu: %s (%s)",
                             zip_path, get_size_display(zip_path.stat().st_size))
                return zip_path

            except Exception as e:
                logger.error("ZIP oluşturma hatası: %s", e)
                if zip_path.exists():
                    zip_path.unlink()
                return None

    def export_profile_stream(self, profile: UserProfile, selected_ids: List[str],
                              fileobj, progress_callback: Optional[Callable] = None) -> bool:
        """
        Seçili bileşenleri tar.gz formatında doğrudan bir akışa (socket) yazar.
        Sadece gerekli meta dosyalar için geçici dizin kullanır, büyük dosyaları doğrudan okur.
        """
        self._cancelled = False
        selected_components = [c for c in profile.components if c.id in selected_ids]
        total_steps = len(selected_components) + 1
        current_step = 0

        manifest = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "source_computer": os.environ.get("COMPUTERNAME", "Bilinmiyor"),
            "source_user": profile.username,
            "source_os": os.environ.get("OS", "Bilinmiyor"),
            "components": [],
            "compression": "network_stream",
        }

        try:
            with tarfile.open(fileobj=fileobj, mode="w|gz") as tar:
                with tempfile.TemporaryDirectory(prefix="WPM_meta_") as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    for comp in selected_components:
                        if self._cancelled:
                            return False
                            
                        current_step += 1
                        if progress_callback:
                            progress_callback(current_step, total_steps, f"{comp.icon} {comp.name} aktarılıyor...")
                            
                        success = False
                        try:
                            # Dosya klasörlerini (Masaüstü vs.) KOPYALAMADAN doğrudan tar'a ekle
                            if comp.category == "files" and comp.path:
                                def tar_filter(tarinfo):
                                    if self._cancelled: return None
                                    return tarinfo
                                
                                try:
                                    tar.add(comp.path, arcname=comp.id, filter=tar_filter)
                                    success = True
                                except Exception as e:
                                    logger.error("Klasör tar'a eklenemedi: %s", e)
                                    
                            # Diğer küçük meta dosyalar için temp_dir kullan ve ardından tar'a ekle
                            else:
                                comp_dir = temp_path / comp.id
                                comp_dir.mkdir(parents=True, exist_ok=True)
                                
                                if comp.id == "appdata_roaming":
                                    success = self._export_appdata_roaming(comp.path, comp_dir)
                                elif comp.id == "appdata_local":
                                    success = self._export_appdata_local(comp.path, comp_dir)
                                elif comp.id == "registry":
                                    success = self.registry_handler.export_registry(comp_dir)
                                elif comp.id == "wifi_profiles":
                                    success = self._export_wifi(comp_dir)
                                elif comp.id == "env_variables":
                                    success = self.registry_handler.export_env_variables(comp_dir)
                                elif comp.id == "wallpaper_theme":
                                    success = self.registry_handler.export_wallpaper_info(comp_dir)
                                    theme_success = self.registry_handler.export_theme_settings(comp_dir)
                                    success = success or theme_success
                                elif comp.id == "taskbar_startmenu":
                                    success = self._export_taskbar_startmenu(profile.profile_path, comp_dir)
                                elif comp.id == "printers":
                                    success = self._export_printers(comp_dir)
                                    
                                if success:
                                    tar.add(comp_dir, arcname=comp.id)
                                    
                        except Exception as e:
                            logger.error("Bileşen aktarım hatası (%s): %s", comp.id, e)
                            
                        manifest["components"].append({
                            "id": comp.id,
                            "name": comp.name,
                            "category": comp.category,
                            "success": success,
                        })

                    # Son adım: Manifest'i ekle
                    current_step += 1
                    if progress_callback:
                        progress_callback(current_step, total_steps, "📋 Tamamlanıyor...")
                        
                    manifest_file = temp_path / "manifest.json"
                    with open(manifest_file, "w", encoding="utf-8") as f:
                        json.dump(manifest, f, ensure_ascii=False, indent=2)
                        
                    tar.add(manifest_file, arcname="manifest.json")
            return not self._cancelled
        except Exception as e:
            logger.error("Stream export hatası: %s", e)
            return False

    def _export_folder(self, source: Path, dest: Path) -> bool:
        """Bir klasörü hedef dizine kopyala."""
        try:
            if not source.exists():
                return False

            file_count = 0
            error_count = 0

            for item in source.rglob("*"):
                if self._cancelled:
                    return False
                if item.is_file():
                    try:
                        rel_path = item.relative_to(source)
                        target = dest / rel_path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target)
                        file_count += 1
                    except (PermissionError, OSError) as e:
                        error_count += 1
                        logger.debug("Dosya kopyalanamadı: %s - %s", item, e)

            logger.info("Klasör dışa aktarıldı: %s (%d dosya, %d hata)",
                         source, file_count, error_count)
            return file_count > 0

        except Exception as e:
            logger.error("Klasör dışa aktarma hatası (%s): %s", source, e)
            return False

    def _export_appdata_roaming(self, source: Path, dest: Path) -> bool:
        """AppData/Roaming klasörünü seçici olarak dışa aktar."""
        if not source or not source.exists():
            return False

        # Önemli uygulama dizinleri
        important_dirs = [
            "Microsoft\\Windows\\Start Menu",
            "Microsoft\\Windows\\Recent",
            "Microsoft\\Windows\\SendTo",
            "Microsoft\\Windows\\Templates",
            "Microsoft\\Sticky Notes",
            "Code",  # VS Code
            "Mozilla\\Firefox",
            "Notepad++",
            "obs-studio",
            "vlc",
        ]

        file_count = 0
        for rel_dir in important_dirs:
            dir_path = source / rel_dir
            if dir_path.exists():
                try:
                    target_dir = dest / rel_dir
                    shutil.copytree(dir_path, target_dir, dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns(
                                        "*.tmp", "*.log", "Cache*", "cache*",
                                        "GPUCache", "Code Cache", "*.lock"
                                    ))
                    file_count += 1
                except (PermissionError, OSError) as e:
                    logger.debug("AppData dizini kopyalanamadı: %s - %s", rel_dir, e)

        return file_count > 0

    def _export_appdata_local(self, source: Path, dest: Path) -> bool:
        """AppData/Local klasörünü seçici olarak dışa aktar."""
        if not source or not source.exists():
            return False

        # Tarayıcı profilleri ve önemli ayarlar
        important_dirs = [
            "Google\\Chrome\\User Data\\Default\\Bookmarks",
            "Google\\Chrome\\User Data\\Default\\Preferences",
            "Google\\Chrome\\User Data\\Local State",
            "Microsoft\\Edge\\User Data\\Default\\Bookmarks",
            "Microsoft\\Edge\\User Data\\Default\\Preferences",
            "Packages",  # UWP app data - seçici
        ]

        file_count = 0
        for rel_path in important_dirs:
            item_path = source / rel_path
            if item_path.exists():
                try:
                    target = dest / rel_path
                    if item_path.is_file():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item_path, target)
                    else:
                        shutil.copytree(item_path, target, dirs_exist_ok=True,
                                        ignore=shutil.ignore_patterns(
                                            "*.tmp", "Cache*", "cache*",
                                            "GPUCache", "*.lock"
                                        ))
                    file_count += 1
                except (PermissionError, OSError) as e:
                    logger.debug("Local AppData kopyalanamadı: %s - %s", rel_path, e)

        return file_count > 0

    def _export_wifi(self, dest: Path) -> bool:
        """Wi-Fi profillerini dışa aktar."""
        profiles = get_wifi_profiles()
        if not profiles:
            return False

        wifi_dir = dest / "wifi"
        success_count = 0
        for name in profiles:
            if export_wifi_profile(name, wifi_dir):
                success_count += 1

        return success_count > 0

    def _export_taskbar_startmenu(self, profile_path: Path, dest: Path) -> bool:
        """Görev çubuğu ve başlat menüsü pinlerini dışa aktar."""
        success = False

        # Görev çubuğu pinleri
        taskbar_path = (profile_path / "AppData" / "Roaming" /
                        "Microsoft" / "Internet Explorer" /
                        "Quick Launch" / "User Pinned" / "TaskBar")
        if taskbar_path.exists():
            try:
                target = dest / "TaskBar"
                shutil.copytree(taskbar_path, target, dirs_exist_ok=True)
                success = True
            except Exception as e:
                logger.warning("Görev çubuğu pinleri kopyalanamadı: %s", e)

        # Başlat menüsü
        start_menu_path = (profile_path / "AppData" / "Roaming" /
                           "Microsoft" / "Windows" / "Start Menu")
        if start_menu_path.exists():
            try:
                target = dest / "StartMenu"
                shutil.copytree(start_menu_path, target, dirs_exist_ok=True)
                success = True
            except Exception as e:
                logger.warning("Başlat menüsü kopyalanamadı: %s", e)

        return success

    def _export_printers(self, dest: Path) -> bool:
        """Yazıcı ayarlarını dışa aktar."""
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-Printer | Select-Object Name, DriverName, PortName, Shared, ShareName | ConvertTo-Json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                dest.mkdir(parents=True, exist_ok=True)
                printer_file = dest / "printers.json"
                with open(printer_file, "w", encoding="utf-8") as f:
                    f.write(result.stdout)
                return True
        except Exception as e:
            logger.error("Yazıcı ayarları dışa aktarılamadı: %s", e)
        return False
