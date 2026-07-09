"""
WinProfileMigrator - Sidebar Navigasyonu
Modern sol panel navigasyonu.
"""
import customtkinter as ctk
from typing import Callable, Optional, Dict

from ui.components import Colors, Fonts


class SidebarButton(ctk.CTkFrame):
    """Sidebar navigasyon butonu."""

    def __init__(self, master, text: str, icon: str, page_id: str,
                 on_click: Optional[Callable] = None, **kwargs):
        super().__init__(
            master,
            fg_color="transparent",
            corner_radius=10,
            height=44,
            **kwargs
        )
        self.pack_propagate(False)

        self.page_id = page_id
        self._on_click = on_click
        self._active = False

        self.configure(cursor="hand2")
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._click)

        # İçerik
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=8, pady=4)
        content.bind("<Button-1>", self._click)

        # Aktif gösterge (sol kenarda ince çizgi)
        self.indicator = ctk.CTkFrame(
            content, width=3, fg_color="transparent",
            corner_radius=2
        )
        self.indicator.pack(side="left", fill="y", padx=(0, 8))

        # İkon
        self.icon_label = ctk.CTkLabel(
            content, text=icon, font=("Segoe UI Emoji", 16),
            text_color=Colors.TEXT_SECONDARY, width=24
        )
        self.icon_label.pack(side="left", padx=(0, 10))
        self.icon_label.bind("<Button-1>", self._click)

        # Metin
        self.text_label = ctk.CTkLabel(
            content, text=text, font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY, anchor="w"
        )
        self.text_label.pack(side="left", fill="x", expand=True)
        self.text_label.bind("<Button-1>", self._click)

    def set_active(self, active: bool):
        """Aktif durumu ayarla."""
        self._active = active
        if active:
            self.configure(fg_color=Colors.SIDEBAR_HOVER)
            self.indicator.configure(fg_color=Colors.ACCENT_PRIMARY)
            self.icon_label.configure(text_color=Colors.ACCENT_SECONDARY)
            self.text_label.configure(
                text_color=Colors.TEXT_PRIMARY,
                font=Fonts.BODY_BOLD
            )
        else:
            self.configure(fg_color="transparent")
            self.indicator.configure(fg_color="transparent")
            self.icon_label.configure(text_color=Colors.TEXT_SECONDARY)
            self.text_label.configure(
                text_color=Colors.TEXT_SECONDARY,
                font=Fonts.BODY
            )

    def _on_enter(self, event):
        if not self._active:
            self.configure(fg_color=Colors.SIDEBAR_HOVER)

    def _on_leave(self, event):
        if not self._active:
            self.configure(fg_color="transparent")

    def _click(self, event):
        if self._on_click:
            self._on_click(self.page_id)


class Sidebar(ctk.CTkFrame):
    """Sol panel navigasyonu."""

    NAV_ITEMS = [
        {"id": "home", "text": "Ana Sayfa", "icon": "🏠"},
        {"id": "export", "text": "Dışa Aktar", "icon": "📤"},
        {"id": "import", "text": "İçe Aktar", "icon": "📥"},
        {"id": "network", "text": "Ağ Transferi", "icon": "🌐"},
        {"id": "clone", "text": "Profil Klonla", "icon": "📋"},
        {"id": "programs", "text": "Program Taşıma", "icon": "💿"},
    ]

    BOTTOM_ITEMS = [
        {"id": "settings", "text": "Ayarlar", "icon": "⚙️"},
    ]

    def __init__(self, master, on_navigate: Callable, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.SIDEBAR_BG,
            width=240,
            corner_radius=0,
            **kwargs
        )
        self.pack_propagate(False)

        self._on_navigate = on_navigate
        self._buttons: Dict[str, SidebarButton] = {}

        # ── Logo/Başlık Alanı ──
        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=16, pady=(20, 6))
        header.pack_propagate(False)

        # Logo ikonu
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.pack(expand=True)

        ctk.CTkLabel(
            logo_frame, text="🔄", font=("Segoe UI Emoji", 30)
        ).pack(side="left", padx=(0, 8))

        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(
            title_frame, text="WinProfile",
            font=("Segoe UI", 17, "bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame, text="Migrator",
            font=("Segoe UI", 12),
            text_color=Colors.ACCENT_SECONDARY
        ).pack(anchor="w")

        # ── Ayırıcı ──
        separator = ctk.CTkFrame(
            self, fg_color=Colors.BORDER, height=1
        )
        separator.pack(fill="x", padx=20, pady=(8, 16))

        # ── Navigasyon Butonları ──
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10)

        for item in self.NAV_ITEMS:
            btn = SidebarButton(
                nav_frame,
                text=item["text"],
                icon=item["icon"],
                page_id=item["id"],
                on_click=self._handle_click
            )
            btn.pack(fill="x", pady=2)
            self._buttons[item["id"]] = btn

        # ── Alt Kısım ──
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 16))

        # Alt ayırıcı
        bottom_sep = ctk.CTkFrame(
            bottom_frame, fg_color=Colors.BORDER, height=1
        )
        bottom_sep.pack(fill="x", padx=10, pady=(0, 12))

        for item in self.BOTTOM_ITEMS:
            btn = SidebarButton(
                bottom_frame,
                text=item["text"],
                icon=item["icon"],
                page_id=item["id"],
                on_click=self._handle_click
            )
            btn.pack(fill="x", pady=2)
            self._buttons[item["id"]] = btn

        # Versiyon bilgisi
        ctk.CTkLabel(
            bottom_frame, text="v0.4 (Beta)",
            font=Fonts.TINY, text_color=Colors.TEXT_MUTED
        ).pack(pady=(8, 0))
        
        # Geliştirici bilgisi
        ctk.CTkLabel(
            bottom_frame, text="Developed by Ediz Ege Mercan",
            font=("Inter", 9), text_color="#30363d"
        ).pack(pady=(0, 0))

        # İlk seçimi yap
        self.set_active("home")

    def _handle_click(self, page_id: str):
        self.set_active(page_id)
        self._on_navigate(page_id)

    def set_active(self, page_id: str):
        """Aktif sayfayı ayarla."""
        for btn_id, btn in self._buttons.items():
            btn.set_active(btn_id == page_id)
