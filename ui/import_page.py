"""
WinProfileMigrator - İçe Aktarma Sayfası
ZIP paketinden profil bileşenlerini geri yükleme.
"""
import threading
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import Optional

from ui.components import (
    Colors, Fonts, SectionHeader, ComponentCheckbox,
    AccentButton, SecondaryButton, ProgressCard, GlassCard, InfoRow
)
from core.profile_importer import ProfileImporter
from utils.helpers import get_size_display, add_recent_operation


class ImportPage(ctk.CTkScrollableFrame):
    """İçe aktarma sayfası."""

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
        self._importer = ProfileImporter()
        self._manifest = None
        self._zip_path = None
        self._checkboxes = []
        self._importing = False

        self._build_ui()

    def _build_ui(self):
        """UI'ı oluştur."""
        # ── Başlık ──
        SectionHeader(
            self, title="📥  Profil İçe Aktarma",
            subtitle="Daha önce dışa aktarılan bir profil paketini seçin ve geri yükleyin"
        ).pack(fill="x", padx=30, pady=(24, 16))

        # ── Dosya Seçimi ──
        file_card = GlassCard(self, title="Paket Dosyası", icon="📦")
        file_card.pack(fill="x", padx=30, pady=(0, 12))

        file_inner = ctk.CTkFrame(file_card, fg_color="transparent")
        file_inner.pack(fill="x", padx=16, pady=(0, 16))

        self._file_entry = ctk.CTkEntry(
            file_inner, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=400,
            placeholder_text="Bir .wpkg dosyası seçin..."
        )
        self._file_entry.pack(side="left")

        AccentButton(
            file_inner, text="Dosya Seç", icon="📂",
            command=self._browse_file, width=140
        ).pack(side="left", padx=(12, 0))

        # ── Paket Bilgileri (başlangıçta gizli) ──
        self._info_card = GlassCard(self, title="Paket Bilgileri", icon="ℹ️")

        self._info_frame = ctk.CTkFrame(self._info_card, fg_color="transparent")
        self._info_frame.pack(fill="x", padx=16, pady=(0, 16))

        self._info_source_pc = InfoRow(self._info_frame, "Kaynak Bilgisayar", "-", icon="🏷️")
        self._info_source_pc.pack(fill="x", pady=2)

        self._info_source_user = InfoRow(self._info_frame, "Kaynak Kullanıcı", "-", icon="👤")
        self._info_source_user.pack(fill="x", pady=2)

        self._info_created = InfoRow(self._info_frame, "Oluşturulma Tarihi", "-", icon="📅")
        self._info_created.pack(fill="x", pady=2)

        self._info_size = InfoRow(self._info_frame, "Paket Boyutu", "-", icon="📦")
        self._info_size.pack(fill="x", pady=2)

        self._info_components = InfoRow(self._info_frame, "Bileşen Sayısı", "-", icon="🔧")
        self._info_components.pack(fill="x", pady=2)

        # ── Bileşen Seçimi (başlangıçta gizli) ──
        self._comp_header = SectionHeader(
            self, title="İçe Aktarılacak Bileşenler",
            subtitle="Geri yüklemek istediğiniz bileşenleri seçin"
        )

        self._select_frame = ctk.CTkFrame(self, fg_color="transparent")

        SecondaryButton(
            self._select_frame, text="Tümünü Seç", icon="☑️",
            command=self._select_all, width=130
        ).pack(side="left", padx=(0, 8))

        SecondaryButton(
            self._select_frame, text="Seçimi Kaldır", icon="⬜",
            command=self._deselect_all, width=140
        ).pack(side="left")

        self._components_frame = ctk.CTkFrame(self, fg_color="transparent")

        # ── Ayarlar ──
        self._settings_card = GlassCard(self, title="İçe Aktarma Ayarları", icon="⚙️")

        settings_inner = ctk.CTkFrame(self._settings_card, fg_color="transparent")
        settings_inner.pack(fill="x", padx=16, pady=(0, 16))

        self._auto_backup_var = ctk.BooleanVar(
            value=self._settings.get("auto_backup", True)
        )

        ctk.CTkCheckBox(
            settings_inner,
            text="İçe aktarmadan önce otomatik yedek oluştur",
            variable=self._auto_backup_var,
            font=Fonts.BODY,
            fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        ).pack(anchor="w", pady=4)

        # ── İlerleme Kartı (gizli) ──
        self._progress_card = ProgressCard(self, title="İçe Aktarılıyor...")

        # ── Aksiyon Butonları ──
        self._action_frame = ctk.CTkFrame(self, fg_color="transparent")

        self._import_btn = AccentButton(
            self._action_frame, text="İçe Aktarmayı Başlat", icon="📥",
            accent=Colors.INFO, hover="#2563eb",
            command=self._start_import, width=250
        )
        self._import_btn.pack(side="right")

        self._cancel_btn = SecondaryButton(
            self._action_frame, text="İptal", icon="❌",
            command=self._cancel_import, width=120
        )

        # Alt boşluk
        ctk.CTkFrame(self, fg_color="transparent", height=20).pack()

    def _browse_file(self):
        """Paket dosyası seç."""
        path = filedialog.askopenfilename(
            title="Profil Paketi Seçin",
            filetypes=[
                ("WinProfile Paketi", "*.wpkg"),
                ("ZIP Dosyası", "*.zip"),
                ("Tüm Dosyalar", "*.*"),
            ]
        )
        if path:
            self._file_entry.delete(0, "end")
            self._file_entry.insert(0, path)
            self._load_package(Path(path))

    def _load_package(self, zip_path: Path):
        """Paketi yükle ve bilgileri göster."""
        self._zip_path = zip_path
        self._manifest = self._importer.read_package(zip_path)

        if not self._manifest:
            self._show_message("Geçersiz veya bozuk paket dosyası!", "error")
            return

        # Bilgileri güncelle
        self._info_source_pc.set_value(
            self._manifest.get("source_computer", "Bilinmiyor")
        )
        self._info_source_user.set_value(
            self._manifest.get("source_user", "Bilinmiyor")
        )
        self._info_created.set_value(
            self._manifest.get("created", "Bilinmiyor")[:19].replace("T", " ")
        )
        self._info_size.set_value(
            self._manifest.get("package_size_display", "Bilinmiyor")
        )

        components = self._manifest.get("components", [])
        successful = [c for c in components if c.get("success", False)]
        self._info_components.set_value(f"{len(successful)}/{len(components)}")

        # UI elemanlarını göster
        self._info_card.pack(fill="x", padx=30, pady=(0, 12))
        self._comp_header.pack(fill="x", padx=30, pady=(16, 8))
        self._select_frame.pack(fill="x", padx=30, pady=(0, 8))
        self._components_frame.pack(fill="x", padx=30)
        self._settings_card.pack(fill="x", padx=30, pady=(16, 8))
        self._action_frame.pack(fill="x", padx=30, pady=(16, 24))

        # Bileşen checkbox'larını oluştur
        self._populate_components(successful)

    def _populate_components(self, components: list):
        """Bileşen checkbox'larını oluştur."""
        for widget in self._components_frame.winfo_children():
            widget.destroy()
        self._checkboxes.clear()

        icon_map = {
            "desktop": "🖥️", "documents": "📄", "downloads": "⬇️",
            "pictures": "🖼️", "music": "🎵", "videos": "🎬",
            "appdata_roaming": "⚙️", "appdata_local": "💾",
            "registry": "🔧", "wifi_profiles": "📶",
            "printers": "🖨️", "env_variables": "🔤",
            "wallpaper_theme": "🎨", "taskbar_startmenu": "📌",
        }

        for comp in components:
            comp_id = comp["id"]
            cb = ComponentCheckbox(
                self._components_frame,
                component_id=comp_id,
                icon=icon_map.get(comp_id, "📦"),
                name=comp.get("name", comp_id),
                description=f"Kategori: {comp.get('category', 'bilinmiyor')}",
                available=True
            )
            cb.pack(fill="x", pady=2)
            cb.is_selected = True  # Varsayılan olarak seçili
            self._checkboxes.append(cb)

    def _select_all(self):
        for cb in self._checkboxes:
            cb.is_selected = True

    def _deselect_all(self):
        for cb in self._checkboxes:
            cb.is_selected = False

    def _start_import(self):
        """İçe aktarmayı başlat."""
        if self._importing or not self._zip_path:
            return

        selected_ids = [cb.component_id for cb in self._checkboxes if cb.is_selected]
        if not selected_ids:
            self._show_message("Lütfen en az bir bileşen seçin!", "warning")
            return

        self._importing = True
        self._import_btn.configure(state="disabled")
        self._progress_card.pack(fill="x", padx=30, pady=(8, 0))
        self._cancel_btn.pack(side="left")

        def progress_cb(current, total, message):
            self.after(0, lambda: self._progress_card.update_progress(
                current / total, message,
                f"Adım {current}/{total}"
            ))

        def import_thread():
            result = self._importer.import_profile(
                self._zip_path, selected_ids,
                auto_backup=self._auto_backup_var.get(),
                progress_callback=progress_cb
            )
            self.after(0, lambda: self._import_complete(result))

        threading.Thread(target=import_thread, daemon=True).start()

    def _import_complete(self, success: bool):
        """İçe aktarma tamamlandı."""
        self._importing = False
        self._import_btn.configure(state="normal")
        self._cancel_btn.pack_forget()

        if success:
            self._progress_card.set_complete("✅ Profil başarıyla içe aktarıldı!")
            add_recent_operation(self._settings, {
                "type": "import",
                "description": f"Profil içe aktarıldı: {self._manifest.get('source_user', '')}",
                "file": str(self._zip_path),
            })
        else:
            self._progress_card.set_error("❌ İçe aktarma başarısız oldu!")

    def _cancel_import(self):
        """İçe aktarmayı iptal et."""
        self._importer.cancel()
        self._progress_card.set_error("İptal edildi")
        self._importing = False
        self._import_btn.configure(state="normal")
        self._cancel_btn.pack_forget()

    def _show_message(self, message: str, msg_type: str = "info"):
        """Bilgi mesajı göster."""
        color_map = {
            "info": Colors.INFO, "warning": Colors.WARNING,
            "error": Colors.ERROR, "success": Colors.SUCCESS,
        }

        msg_frame = ctk.CTkFrame(
            self, fg_color=color_map.get(msg_type, Colors.INFO),
            corner_radius=8, height=40
        )
        msg_frame.pack(fill="x", padx=30, pady=4, before=self._info_card
                        if self._info_card.winfo_manager() else None)
        msg_frame.pack_propagate(False)

        ctk.CTkLabel(
            msg_frame, text=f"  {message}",
            font=Fonts.BODY, text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=12)

        self.after(3000, msg_frame.destroy)
