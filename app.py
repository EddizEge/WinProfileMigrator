"""
WinProfileMigrator - Ana Uygulama
Modern Windows profil taşıma ve klonlama aracı.
"""
import customtkinter as ctk
from typing import Dict, Optional

from ui.components import Colors, Fonts
from ui.sidebar import Sidebar
from ui.home_page import HomePage
from ui.export_page import ExportPage
from ui.import_page import ImportPage
from ui.network_page import NetworkPage
from ui.clone_page import ClonePage
from ui.settings_page import SettingsPage
from ui.programs_page import ProgramsPage
from utils.helpers import load_settings


class WinProfileMigrator(ctk.CTk):
    """Ana uygulama penceresi."""

    APP_TITLE = "WinProfile Migrator"
    APP_VERSION = "0.5 (Beta)"
    MIN_WIDTH = 1100
    MIN_HEIGHT = 700

    def __init__(self):
        super().__init__()

        # Tema ayarları
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Pencere yapılandırması
        self.title(f"{self.APP_TITLE} v{self.APP_VERSION}")
        self.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}")
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.configure(fg_color=Colors.BG_DARK)

        # Pencereyi ortala
        self._center_window()

        # Simge ayarlama (opsiyonel)
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        # Ayarları yükle
        self._settings = load_settings()

        # Sayfalar
        self._pages: Dict[str, Optional[ctk.CTkFrame]] = {}
        self._current_page: Optional[str] = None

        # UI oluştur
        self._build_ui()

        # İlk sayfa
        self._navigate("home")

    def _center_window(self):
        """Pencereyi ekranın ortasına konumlandır."""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - self.MIN_WIDTH) // 2
        y = (screen_h - self.MIN_HEIGHT) // 2
        self.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}+{x}+{y}")

    def _build_ui(self):
        """Ana UI yapısını oluştur."""
        # Ana container
        self._main_container = ctk.CTkFrame(self, fg_color=Colors.BG_DARK)
        self._main_container.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = Sidebar(
            self._main_container,
            on_navigate=self._navigate
        )
        self._sidebar.pack(side="left", fill="y")

        # Ayırıcı çizgi
        separator = ctk.CTkFrame(
            self._main_container,
            fg_color=Colors.BORDER,
            width=1
        )
        separator.pack(side="left", fill="y")

        # İçerik alanı
        self._content_area = ctk.CTkFrame(
            self._main_container,
            fg_color=Colors.BG_PRIMARY,
            corner_radius=0
        )
        self._content_area.pack(side="left", fill="both", expand=True)

    def _navigate(self, page_id: str):
        """Sayfalar arası geçiş yap."""
        if self._current_page == page_id:
            return

        # Mevcut sayfayı gizle
        if self._current_page and self._current_page in self._pages:
            page = self._pages[self._current_page]
            if page:
                page.pack_forget()

        # Sidebar'ı güncelle
        self._sidebar.set_active(page_id)

        # Yeni sayfayı göster (lazily oluştur)
        if page_id not in self._pages or self._pages[page_id] is None:
            self._pages[page_id] = self._create_page(page_id)

        page = self._pages[page_id]
        if page:
            page.pack(fill="both", expand=True)

        self._current_page = page_id

    def _create_page(self, page_id: str) -> Optional[ctk.CTkFrame]:
        """Sayfa widget'ını oluştur."""
        page_map = {
            "home": lambda: HomePage(
                self._content_area,
                on_navigate=self._navigate,
                settings=self._settings
            ),
            "export": lambda: ExportPage(
                self._content_area,
                settings=self._settings
            ),
            "import": lambda: ImportPage(
                self._content_area,
                settings=self._settings
            ),
            "network": lambda: NetworkPage(
                self._content_area,
                settings=self._settings
            ),
            "clone": lambda: ClonePage(
                self._content_area,
                settings=self._settings
            ),
            "programs": lambda: ProgramsPage(
                self._content_area,
                settings=self._settings
            ),
            "settings": lambda: SettingsPage(
                self._content_area,
                settings=self._settings
            ),
        }

        creator = page_map.get(page_id)
        if creator:
            try:
                return creator()
            except Exception as e:
                # Hata sayfası göster
                error_frame = ctk.CTkFrame(
                    self._content_area,
                    fg_color=Colors.BG_PRIMARY
                )

                ctk.CTkLabel(
                    error_frame,
                    text=f"❌ Sayfa yüklenirken hata oluştu:\n\n{str(e)}",
                    font=Fonts.BODY,
                    text_color=Colors.ERROR,
                    wraplength=500
                ).pack(expand=True)

                return error_frame

        return None

    def refresh_page(self, page_id: str):
        """Bir sayfayı yeniden oluştur."""
        if page_id in self._pages and self._pages[page_id]:
            self._pages[page_id].destroy()
            self._pages[page_id] = None

        if self._current_page == page_id:
            self._navigate(page_id)
