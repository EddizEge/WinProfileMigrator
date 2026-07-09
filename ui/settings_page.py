"""
WinProfileMigrator - Ayarlar Sayfası
Uygulama yapılandırma ayarları.
"""
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog

from ui.components import (
    Colors, Fonts, SectionHeader, GlassCard,
    AccentButton, SecondaryButton, StatusBadge
)
from utils.helpers import save_settings, is_admin, request_admin, get_app_data_dir


class SettingsPage(ctk.CTkScrollableFrame):
    """Ayarlar sayfası."""

    def __init__(self, master, settings: dict, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_PRIMARY,
            corner_radius=0,
            scrollbar_button_color=Colors.BG_CARD,
            scrollbar_button_hover_color=Colors.ACCENT_PRIMARY,
            **kwargs
        )

        self._settings = settings
        self._build_ui()

    def _build_ui(self):
        """UI'ı oluştur."""
        # ── Başlık ──
        SectionHeader(
            self, title="⚙️  Ayarlar",
            subtitle="Uygulama yapılandırma ve tercihler"
        ).pack(fill="x", padx=30, pady=(24, 16))

        # ── Genel Ayarlar ──
        general_card = GlassCard(self, title="Genel Ayarlar", icon="🔧")
        general_card.pack(fill="x", padx=30, pady=(0, 12))

        general_inner = ctk.CTkFrame(general_card, fg_color="transparent")
        general_inner.pack(fill="x", padx=16, pady=(0, 16))

        # Varsayılan dışa aktarma konumu
        loc_frame = ctk.CTkFrame(general_inner, fg_color="transparent")
        loc_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(
            loc_frame, text="Varsayılan Dışa Aktarma Konumu:",
            font=Fonts.BODY, text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w")

        loc_input = ctk.CTkFrame(loc_frame, fg_color="transparent")
        loc_input.pack(fill="x", pady=(4, 0))

        self._export_loc = ctk.CTkEntry(
            loc_input, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=400
        )
        self._export_loc.pack(side="left")
        self._export_loc.insert(
            0, self._settings.get("export_location", str(Path.home() / "Desktop"))
        )

        SecondaryButton(
            loc_input, text="Gözat", icon="📂",
            command=self._browse_location, width=100
        ).pack(side="left", padx=(12, 0))

        # Sıkıştırma seviyesi
        comp_frame = ctk.CTkFrame(general_inner, fg_color="transparent")
        comp_frame.pack(fill="x", pady=(12, 6))

        ctk.CTkLabel(
            comp_frame, text="Varsayılan Sıkıştırma Seviyesi:",
            font=Fonts.BODY, text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w")

        comp_input = ctk.CTkFrame(comp_frame, fg_color="transparent")
        comp_input.pack(fill="x", pady=(4, 0))

        self._compression_var = ctk.StringVar(
            value=self._settings.get("compression_level", "normal")
        )

        for text, value, desc in [
            ("Hızlı", "fast", "Sıkıştırmasız, hızlı aktarım"),
            ("Normal", "normal", "Dengeli sıkıştırma (önerilen)"),
            ("Maksimum", "maximum", "En yüksek sıkıştırma, yavaş"),
        ]:
            radio_frame = ctk.CTkFrame(comp_input, fg_color="transparent")
            radio_frame.pack(fill="x", pady=2)

            ctk.CTkRadioButton(
                radio_frame, text=text, variable=self._compression_var,
                value=value, font=Fonts.BODY,
                fg_color=Colors.ACCENT_PRIMARY,
                border_color=Colors.BORDER,
                hover_color=Colors.ACCENT_SECONDARY,
                text_color=Colors.TEXT_PRIMARY
            ).pack(side="left")

            ctk.CTkLabel(
                radio_frame, text=f"  —  {desc}",
                font=Fonts.TINY, text_color=Colors.TEXT_MUTED
            ).pack(side="left")

        # ── Güvenlik Ayarları ──
        security_card = GlassCard(self, title="Güvenlik", icon="🔒")
        security_card.pack(fill="x", padx=30, pady=(0, 12))

        security_inner = ctk.CTkFrame(security_card, fg_color="transparent")
        security_inner.pack(fill="x", padx=16, pady=(0, 16))

        # Otomatik yedekleme
        self._auto_backup_var = ctk.BooleanVar(
            value=self._settings.get("auto_backup", True)
        )

        ctk.CTkCheckBox(
            security_inner,
            text="İçe aktarmadan önce otomatik yedek oluştur",
            variable=self._auto_backup_var,
            font=Fonts.BODY,
            fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        ).pack(anchor="w", pady=4)

        # Yönetici yetkisi
        admin_frame = ctk.CTkFrame(security_inner, fg_color="transparent")
        admin_frame.pack(fill="x", pady=(12, 0))

        ctk.CTkLabel(
            admin_frame, text="Yönetici Yetkisi:",
            font=Fonts.BODY, text_color=Colors.TEXT_SECONDARY
        ).pack(side="left")

        if is_admin():
            StatusBadge(admin_frame, "✓ Aktif", "success").pack(side="left", padx=(12, 0))
        else:
            StatusBadge(admin_frame, "✗ Devre dışı", "warning").pack(side="left", padx=(12, 0))
            AccentButton(
                admin_frame, text="Yönetici Olarak Yeniden Başlat", icon="🔓",
                command=request_admin, width=280,
                accent=Colors.WARNING, hover="#d97706"
            ).pack(side="left", padx=(12, 0))

        # ── Loglama ──
        log_card = GlassCard(self, title="Loglama", icon="📝")
        log_card.pack(fill="x", padx=30, pady=(0, 12))

        log_inner = ctk.CTkFrame(log_card, fg_color="transparent")
        log_inner.pack(fill="x", padx=16, pady=(0, 16))

        log_level_frame = ctk.CTkFrame(log_inner, fg_color="transparent")
        log_level_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            log_level_frame, text="Log Seviyesi:",
            font=Fonts.BODY, text_color=Colors.TEXT_SECONDARY
        ).pack(side="left")

        self._log_level_var = ctk.StringVar(
            value=self._settings.get("log_level", "INFO")
        )

        self._log_combo = ctk.CTkComboBox(
            log_level_frame,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self._log_level_var,
            font=Fonts.BODY,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            button_color=Colors.ACCENT_PRIMARY,
            button_hover_color=Colors.ACCENT_SECONDARY,
            dropdown_fg_color=Colors.BG_CARD,
            dropdown_hover_color=Colors.ACCENT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            text_color=Colors.TEXT_PRIMARY,
            width=150,
            state="readonly"
        )
        self._log_combo.pack(side="left", padx=(12, 0))

        # Log dizini bilgisi
        log_dir = get_app_data_dir() / "logs"
        ctk.CTkLabel(
            log_inner,
            text=f"Log dizini: {log_dir}",
            font=Fonts.TINY, text_color=Colors.TEXT_MUTED
        ).pack(anchor="w", pady=(8, 0))

        # ── Hakkında ──
        about_card = GlassCard(self, title="Hakkında", icon="ℹ️")
        about_card.pack(fill="x", padx=30, pady=(0, 12))

        about_inner = ctk.CTkFrame(about_card, fg_color="transparent")
        about_inner.pack(fill="x", padx=16, pady=(0, 16))

        about_texts = [
            ("Uygulama", "WinProfile Migrator"),
            ("Sürüm", "0.4 (Beta)"),
            ("Geliştirici", "Ediz Ege Mercan"),
            ("Lisans", "MIT License"),
        ]

        for label, value in about_texts:
            row = ctk.CTkFrame(about_inner, fg_color="transparent", height=28)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row, text=label, font=Fonts.SMALL,
                text_color=Colors.TEXT_SECONDARY, anchor="w"
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=value, font=Fonts.SMALL_BOLD,
                text_color=Colors.TEXT_PRIMARY, anchor="e"
            ).pack(side="right")

        # ── Kaydet Butonu ──
        save_frame = ctk.CTkFrame(self, fg_color="transparent")
        save_frame.pack(fill="x", padx=30, pady=(16, 8))

        AccentButton(
            save_frame, text="Ayarları Kaydet", icon="💾",
            command=self._save, width=200
        ).pack(side="right")

        self._save_status = ctk.CTkLabel(
            save_frame, text="", font=Fonts.SMALL,
            text_color=Colors.SUCCESS
        )
        self._save_status.pack(side="right", padx=(0, 12))

        # ── Tehlikeli Bölge ──
        danger_card = GlassCard(self, title="Veri Yönetimi", icon="⚠️")
        danger_card.pack(fill="x", padx=30, pady=(12, 12))

        danger_inner = ctk.CTkFrame(danger_card, fg_color="transparent")
        danger_inner.pack(fill="x", padx=16, pady=(0, 16))

        SecondaryButton(
            danger_inner, text="Son İşlem Geçmişini Temizle", icon="🗑️",
            command=self._clear_history, width=260
        ).pack(anchor="w", pady=4)

        SecondaryButton(
            danger_inner, text="Yedekleri Temizle", icon="🗂️",
            command=self._clear_backups, width=200
        ).pack(anchor="w", pady=4)

        # Alt boşluk
        ctk.CTkFrame(self, fg_color="transparent", height=30).pack()

    def _browse_location(self):
        """Dışa aktarma konumu seç."""
        path = filedialog.askdirectory(
            title="Varsayılan Dışa Aktarma Konumu",
            initialdir=self._export_loc.get()
        )
        if path:
            self._export_loc.delete(0, "end")
            self._export_loc.insert(0, path)

    def _save(self):
        """Ayarları kaydet."""
        self._settings["export_location"] = self._export_loc.get()
        self._settings["compression_level"] = self._compression_var.get()
        self._settings["auto_backup"] = self._auto_backup_var.get()
        self._settings["log_level"] = self._log_level_var.get()

        save_settings(self._settings)

        self._save_status.configure(text="✅ Ayarlar kaydedildi!")
        self.after(3000, lambda: self._save_status.configure(text=""))

    def _clear_history(self):
        """İşlem geçmişini temizle."""
        self._settings["recent_operations"] = []
        save_settings(self._settings)

    def _clear_backups(self):
        """Yedekleri temizle."""
        import shutil
        backup_dir = get_app_data_dir() / "backups"
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
