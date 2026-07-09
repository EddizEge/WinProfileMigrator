"""
WinProfileMigrator - Profil Tarayıcı
Windows kullanıcı profillerini ve bileşenlerini tarar.
"""
import os
import logging
import winreg
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

from utils.helpers import get_dir_size, get_size_display, get_wifi_profiles

logger = logging.getLogger("WinProfileMigrator.scanner")


@dataclass
class ProfileComponent:
    """Profil bileşeni."""
    id: str
    name: str
    description: str
    icon: str
    path: Optional[Path] = None
    size: int = -1
    available: bool = True
    requires_admin: bool = False
    category: str = "files"  # files, settings, system

    @property
    def size_display(self) -> str:
        return get_size_display(self.size)


@dataclass
class UserProfile:
    """Windows kullanıcı profili."""
    username: str
    profile_path: Path
    sid: str = ""
    is_current: bool = False
    components: List[ProfileComponent] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        return sum(c.size for c in self.components if c.size > 0)

    @property
    def total_size_display(self) -> str:
        return get_size_display(self.total_size)


class ProfileScanner:
    """Windows profillerini tarar ve bileşenlerini listeler."""

    # Bilinen kullanıcı klasörleri
    KNOWN_FOLDERS = {
        "desktop": {"name": "Masaüstü", "icon": "🖥️", "shell_folder": "Desktop"},
        "documents": {"name": "Belgeler", "icon": "📄", "shell_folder": "Personal"},
        "downloads": {"name": "İndirilenler", "icon": "⬇️", "shell_folder": "{374DE290-123F-4565-9164-39C4925E467B}"},
        "pictures": {"name": "Resimler", "icon": "🖼️", "shell_folder": "My Pictures"},
        "music": {"name": "Müzik", "icon": "🎵", "shell_folder": "My Music"},
        "videos": {"name": "Videolar", "icon": "🎬", "shell_folder": "My Video"},
    }

    SETTINGS_COMPONENTS = {
        "appdata_roaming": {
            "name": "Uygulama Ayarları (Roaming)",
            "icon": "⚙️",
            "description": "Kullanıcıya özel uygulama yapılandırmaları",
            "category": "settings",
        },
        "appdata_local": {
            "name": "Yerel Uygulama Verileri",
            "icon": "💾",
            "description": "Tarayıcı profilleri, önbellekler ve yerel ayarlar",
            "category": "settings",
        },
        "registry": {
            "name": "Registry Ayarları (HKCU)",
            "icon": "🔧",
            "description": "Kullanıcı kayıt defteri ayarları",
            "category": "settings",
            "requires_admin": False,
        },
        "wifi_profiles": {
            "name": "Wi-Fi Profilleri",
            "icon": "📶",
            "description": "Kayıtlı kablosuz ağ profilleri ve şifreleri",
            "category": "system",
            "requires_admin": True,
        },
        "printers": {
            "name": "Yazıcı Ayarları",
            "icon": "🖨️",
            "description": "Yüklü yazıcı yapılandırmaları",
            "category": "system",
            "requires_admin": True,
        },
        "env_variables": {
            "name": "Ortam Değişkenleri",
            "icon": "🔤",
            "description": "Kullanıcı ortam değişkenleri (PATH vb.)",
            "category": "system",
        },
        "wallpaper_theme": {
            "name": "Duvar Kağıdı ve Tema",
            "icon": "🎨",
            "description": "Masaüstü arka planı, renk teması ve kişiselleştirme",
            "category": "settings",
        },
        "taskbar_startmenu": {
            "name": "Görev Çubuğu ve Başlat Menüsü",
            "icon": "📌",
            "description": "Sabitlenmiş uygulamalar ve menü düzeni",
            "category": "settings",
        },
    }

    def __init__(self):
        self.profiles: List[UserProfile] = []
        self.current_user = os.environ.get("USERNAME", "")

    def scan_profiles(self) -> List[UserProfile]:
        """Sistemdeki tüm kullanıcı profillerini tara."""
        self.profiles = []
        profiles_dir = Path(os.environ.get("SystemDrive", "C:") + os.sep) / "Users"

        # Hariç tutulacak sistem profilleri
        excluded = {"Public", "Default", "Default User", "All Users", "desktop.ini"}

        try:
            for entry in profiles_dir.iterdir():
                if entry.is_dir() and entry.name not in excluded:
                    try:
                        # NTUSER.DAT varlığını kontrol et (gerçek kullanıcı profili mi?)
                        is_current = (entry.name == self.current_user)
                        ntuser = entry / "NTUSER.DAT"

                        # NTUSER.DAT erişim izni olmayabilir, hata yutulmalı
                        try:
                            ntuser_exists = ntuser.exists()
                        except (PermissionError, OSError):
                            # Erişim engellendi ama klasör var = büyük ihtimalle gerçek profil
                            ntuser_exists = True

                        if ntuser_exists or is_current:
                            profile = UserProfile(
                                username=entry.name,
                                profile_path=entry,
                                is_current=is_current,
                            )
                            # SID'yi bul
                            profile.sid = self._get_user_sid(entry.name)
                            # Bileşenleri tara
                            profile.components = self._scan_components(entry)
                            self.profiles.append(profile)
                            logger.info("Profil bulundu: %s%s",
                                        entry.name, " (mevcut)" if is_current else "")

                    except (PermissionError, OSError) as e:
                        logger.warning("Profil taranamadı (%s): %s", entry.name, e)
                        # Mevcut kullanıcıysa yine de ekle (boş bileşenlerle)
                        if entry.name == self.current_user:
                            profile = UserProfile(
                                username=entry.name,
                                profile_path=entry,
                                is_current=True,
                            )
                            profile.components = self._scan_components(entry)
                            self.profiles.append(profile)
                    except Exception as e:
                        logger.error("Profil tarama hatası (%s): %s", entry.name, e)

        except PermissionError as e:
            logger.error("Profil dizini taranamadı: %s", e)
        except Exception as e:
            logger.error("Profil tarama hatası: %s", e)

        # Mevcut kullanıcıyı başa al
        self.profiles.sort(key=lambda p: (not p.is_current, p.username))
        return self.profiles

    def _get_user_sid(self, username: str) -> str:
        """Kullanıcının SID'sini al."""
        try:
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                i = 0
                while True:
                    try:
                        sid = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sid) as subkey:
                            profile_path, _ = winreg.QueryValueEx(subkey, "ProfileImagePath")
                            if profile_path.lower().endswith(f"\\{username.lower()}"):
                                return sid
                        i += 1
                    except OSError:
                        break
        except Exception as e:
            logger.debug("SID alınamadı (%s): %s", username, e)
        return ""

    def _safe_exists(self, path: Path) -> bool:
        """path.exists() çağrısını PermissionError'a karşı koru."""
        try:
            return path.exists()
        except (PermissionError, OSError):
            # Erişim engellendi ama yol geçerli olabilir
            return False

    def _scan_components(self, profile_path: Path) -> List[ProfileComponent]:
        """Bir profilin tüm bileşenlerini tara (hızlı, boyut hesaplamadan)."""
        components = []

        # Profil dizinine erişim var mı kontrol et
        try:
            can_access = profile_path.exists() and any(True for _ in profile_path.iterdir())
        except (PermissionError, OSError):
            can_access = False

        # Dosya klasörleri
        for folder_id, info in self.KNOWN_FOLDERS.items():
            if can_access:
                folder_path = self._resolve_folder_path(profile_path, folder_id, info)
                if folder_path:
                    components.append(ProfileComponent(
                        id=folder_id,
                        name=info["name"],
                        description=f"{folder_path}",
                        icon=info["icon"],
                        path=folder_path,
                        size=0,
                        available=True,
                        category="files",
                    ))
                else:
                    components.append(ProfileComponent(
                        id=folder_id,
                        name=info["name"],
                        description="Klasör bulunamadı",
                        icon=info["icon"],
                        available=False,
                        category="files",
                    ))
            else:
                # Erişim yok - standart yolu varsay
                standard_first = {"desktop": "Desktop", "documents": "Documents",
                                  "downloads": "Downloads", "pictures": "Pictures",
                                  "music": "Music", "videos": "Videos"}
                assumed_path = profile_path / standard_first.get(folder_id, folder_id.title())
                components.append(ProfileComponent(
                    id=folder_id,
                    name=info["name"],
                    description=f"{assumed_path} (yönetici yetkisi gerekli)",
                    icon=info["icon"],
                    path=assumed_path,
                    size=0,
                    available=True,
                    requires_admin=True,
                    category="files",
                ))

        # Ayar bileşenleri
        for comp_id, info in self.SETTINGS_COMPONENTS.items():
            comp = self._scan_settings_component(profile_path, comp_id, info)
            components.append(comp)

        return components

    def _resolve_folder_path(self, profile_path: Path, folder_id: str, info: dict) -> Optional[Path]:
        """Klasör yolunu çözümle."""
        # Standart klasör isimlerini dene
        standard_names = {
            "desktop": ["Desktop", "Masaüstü"],
            "documents": ["Documents", "Belgeler"],
            "downloads": ["Downloads", "İndirilenler"],
            "pictures": ["Pictures", "Resimler"],
            "music": ["Music", "Müzik"],
            "videos": ["Videos", "Videolar"],
        }

        for name in standard_names.get(folder_id, []):
            path = profile_path / name
            if self._safe_exists(path):
                return path

        # OneDrive yönlendirmesi kontrol et
        onedrive_path = profile_path / "OneDrive"
        if self._safe_exists(onedrive_path):
            for name in standard_names.get(folder_id, []):
                path = onedrive_path / name
                if self._safe_exists(path):
                    return path

        return None

    def _scan_settings_component(self, profile_path: Path, comp_id: str,
                                  info: dict) -> ProfileComponent:
        """Ayar bileşenini tara."""
        requires_admin = info.get("requires_admin", False)

        if comp_id == "appdata_roaming":
            path = profile_path / "AppData" / "Roaming"
            try:
                available = path.exists()
            except (PermissionError, OSError):
                available = False
            return ProfileComponent(
                id=comp_id, name=info["name"], description=info["description"],
                icon=info["icon"], path=path, size=0,
                available=available, category=info["category"],
            )

        elif comp_id == "appdata_local":
            path = profile_path / "AppData" / "Local"
            try:
                available = path.exists()
            except (PermissionError, OSError):
                available = False
            return ProfileComponent(
                id=comp_id, name=info["name"], description=info["description"],
                icon=info["icon"], path=path, size=0,
                available=available, category=info["category"],
            )

        elif comp_id == "registry":
            return ProfileComponent(
                id=comp_id, name=info["name"], description=info["description"],
                icon=info["icon"], size=0, available=True,
                requires_admin=requires_admin, category=info["category"],
            )

        elif comp_id == "wifi_profiles":
            wifi_list = get_wifi_profiles()
            desc = f"{len(wifi_list)} kayıtlı ağ" if wifi_list else "Kayıtlı ağ yok"
            return ProfileComponent(
                id=comp_id, name=info["name"], description=desc,
                icon=info["icon"], size=0, available=len(wifi_list) > 0,
                requires_admin=requires_admin, category=info["category"],
            )

        elif comp_id == "printers":
            return ProfileComponent(
                id=comp_id, name=info["name"], description=info["description"],
                icon=info["icon"], size=0, available=True,
                requires_admin=requires_admin, category=info["category"],
            )

        elif comp_id == "env_variables":
            return ProfileComponent(
                id=comp_id, name=info["name"], description=info["description"],
                icon=info["icon"], size=0, available=True,
                category=info["category"],
            )

        elif comp_id == "wallpaper_theme":
            return ProfileComponent(
                id=comp_id, name=info["name"], description=info["description"],
                icon=info["icon"], size=0, available=True,
                category=info["category"],
            )

        elif comp_id == "taskbar_startmenu":
            taskbar_path = profile_path / "AppData" / "Roaming" / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
            return ProfileComponent(
                id=comp_id, name=info["name"], description=info["description"],
                icon=info["icon"], path=taskbar_path, size=0,
                available=True, category=info["category"],
            )

        return ProfileComponent(
            id=comp_id, name=info["name"], description="Bilinmeyen bileşen",
            icon="❓", available=False, category="other",
        )

    def get_current_profile(self) -> Optional[UserProfile]:
        """Mevcut kullanıcının profilini döndür."""
        for profile in self.profiles:
            if profile.is_current:
                return profile
        return None

    def get_selected_components_size(self, profile: UserProfile,
                                      selected_ids: List[str]) -> int:
        """Seçili bileşenlerin toplam boyutunu hesapla."""
        total = 0
        for comp in profile.components:
            if comp.id in selected_ids and comp.size > 0:
                total += comp.size
        return total
