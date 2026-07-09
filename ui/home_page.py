"""
WinProfileMigrator - Ana Sayfa
Dashboard görünümü ile sistem bilgileri ve hızlı eylemler.
"""
import customtkinter as ctk
from typing import Callable

from ui.components import (
    Colors, Fonts, GlassCard, ActionCard, InfoRow,
    SectionHeader, DiskUsageBar, StatusBadge
)
from utils.helpers import get_system_info, get_size_display, is_admin


class HomePage(ctk.CTkScrollableFrame):
    """Ana sayfa / Dashboard."""

    def __init__(self, master, on_navigate: Callable, settings: dict, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_PRIMARY,
            corner_radius=0,
            scrollbar_button_color=Colors.BG_CARD,
            scrollbar_button_hover_color=Colors.ACCENT_PRIMARY,
            **kwargs
        )

        self._on_navigate = on_navigate
        self._settings = settings

        self._build_ui()

    def _build_ui(self):
        """UI'ı oluştur."""
        # ── Hoş Geldiniz Başlığı ──
        welcome_frame = ctk.CTkFrame(self, fg_color="transparent")
        welcome_frame.pack(fill="x", padx=30, pady=(24, 0))

        sys_info = get_system_info()

        ctk.CTkLabel(
            welcome_frame,
            text=f"Hoş Geldiniz, {sys_info['kullanici']} 👋",
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            welcome_frame,
            text="Windows profil ayarlarınızı kolayca taşıyın, yedekleyin ve klonlayın.",
            font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x", pady=(4, 0))

        # Admin durumu
        admin_status = ctk.CTkFrame(welcome_frame, fg_color="transparent")
        admin_status.pack(fill="x", pady=(8, 0))

        if is_admin():
            StatusBadge(admin_status, "✓ Yönetici Yetkisi Aktif", "success").pack(side="left")
        else:
            StatusBadge(admin_status, "⚠ Sınırlı Yetki", "warning").pack(side="left")

        # ── Hızlı Eylemler ──
        actions_header = SectionHeader(
            self, title="Hızlı Eylemler",
            subtitle="Profil taşıma işlemlerinize hemen başlayın"
        )
        actions_header.pack(fill="x", padx=30, pady=(28, 12))

        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(fill="x", padx=30)
        actions_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="action")

        actions = [
            {
                "title": "Dışa Aktar",
                "icon": "📤",
                "desc": "Profil ayarlarını paketleyerek dışa aktarın",
                "color": "#7c3aed",
                "page": "export",
            },
            {
                "title": "İçe Aktar",
                "icon": "📥",
                "desc": "Daha önce dışa aktarılan profili geri yükleyin",
                "color": "#3b82f6",
                "page": "import",
            },
            {
                "title": "Ağ Transferi",
                "icon": "🌐",
                "desc": "İki bilgisayar arasında doğrudan aktarım yapın",
                "color": "#10b981",
                "page": "network",
            },
            {
                "title": "Profil Klonla",
                "icon": "📋",
                "desc": "Mevcut profili kopyalayarak yeni profil oluşturun",
                "color": "#f59e0b",
                "page": "clone",
            },
        ]

        for i, action in enumerate(actions):
            card = ActionCard(
                actions_frame,
                title=action["title"],
                icon=action["icon"],
                description=action["desc"],
                accent_color=action["color"],
                on_click=lambda p=action["page"]: self._on_navigate(p)
            )
            card.grid(row=0, column=i, padx=6, pady=4, sticky="nsew")

        # ── Sistem Bilgileri ──
        info_header = SectionHeader(
            self, title="Sistem Bilgileri",
            subtitle="Mevcut bilgisayar ve profil özeti"
        )
        info_header.pack(fill="x", padx=30, pady=(28, 12))

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=30)
        info_frame.columnconfigure((0, 1), weight=1, uniform="info")

        # Sol: Bilgisayar bilgileri
        pc_card = GlassCard(info_frame, title="Bilgisayar", icon="💻")
        pc_card.grid(row=0, column=0, padx=(0, 8), pady=4, sticky="nsew")

        InfoRow(pc_card, "Bilgisayar Adı", sys_info["bilgisayar_adi"],
                icon="🏷️").pack(fill="x", padx=16, pady=2)
        InfoRow(pc_card, "İşletim Sistemi", sys_info["isletim_sistemi"],
                icon="🖥️").pack(fill="x", padx=16, pady=2)
        InfoRow(pc_card, "Mimari", sys_info["mimari"],
                icon="⚡").pack(fill="x", padx=16, pady=2)
        InfoRow(pc_card, "Kullanıcı", sys_info["kullanici"],
                icon="👤").pack(fill="x", padx=16, pady=2)

        spacer = ctk.CTkFrame(pc_card, fg_color="transparent", height=8)
        spacer.pack()

        # Sağ: Disk ve RAM bilgileri
        storage_card = GlassCard(info_frame, title="Depolama", icon="💾")
        storage_card.grid(row=0, column=1, padx=(8, 0), pady=4, sticky="nsew")

        DiskUsageBar(
            storage_card,
            used=sys_info["disk_kullanilan"],
            total=sys_info["disk_toplam"],
            label="Disk Kullanımı"
        ).pack(fill="x", padx=16, pady=(0, 8))

        InfoRow(storage_card, "Boş Alan",
                get_size_display(sys_info["disk_bos"]),
                icon="📂").pack(fill="x", padx=16, pady=2)

        DiskUsageBar(
            storage_card,
            used=sys_info["ram_kullanilan"],
            total=sys_info["ram_toplam"],
            label="RAM Kullanımı"
        ).pack(fill="x", padx=16, pady=(8, 8))

        spacer2 = ctk.CTkFrame(storage_card, fg_color="transparent", height=8)
        spacer2.pack()

        # ── Son İşlemler ──
        recent_header = SectionHeader(
            self, title="Son İşlemler",
            subtitle="Son profil taşıma işlemleriniz"
        )
        recent_header.pack(fill="x", padx=30, pady=(28, 12))

        recent_ops = self._settings.get("recent_operations", [])

        if recent_ops:
            for op in recent_ops[:5]:
                op_card = ctk.CTkFrame(
                    self, fg_color=Colors.BG_CARD,
                    corner_radius=8, height=48
                )
                op_card.pack(fill="x", padx=30, pady=3)
                op_card.pack_propagate(False)

                inner = ctk.CTkFrame(op_card, fg_color="transparent")
                inner.pack(fill="both", expand=True, padx=12, pady=8)

                op_type_icons = {
                    "export": "📤",
                    "import": "📥",
                    "network_send": "🌐",
                    "network_receive": "🌐",
                    "clone": "📋",
                }
                icon = op_type_icons.get(op.get("type", ""), "📝")

                ctk.CTkLabel(
                    inner, text=f'{icon}  {op.get("description", "İşlem")}',
                    font=Fonts.BODY, text_color=Colors.TEXT_PRIMARY
                ).pack(side="left")

                ctk.CTkLabel(
                    inner, text=op.get("tarih", ""),
                    font=Fonts.TINY, text_color=Colors.TEXT_MUTED
                ).pack(side="right")
        else:
            empty_frame = ctk.CTkFrame(
                self, fg_color=Colors.BG_CARD,
                corner_radius=10, height=80
            )
            empty_frame.pack(fill="x", padx=30, pady=4)
            empty_frame.pack_propagate(False)

            ctk.CTkLabel(
                empty_frame,
                text="📭  Henüz hiç işlem yapılmadı. Başlamak için yukarıdaki eylemlerden birini seçin.",
                font=Fonts.BODY,
                text_color=Colors.TEXT_MUTED
            ).pack(expand=True)

        # Alt boşluk
        ctk.CTkFrame(self, fg_color="transparent", height=30).pack()
