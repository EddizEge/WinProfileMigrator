"""
WinProfileMigrator - Dışa Aktarma Sayfası
Profil bileşenlerini seçerek ZIP paketi olarak dışa aktarma.
"""
import threading
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import Callable

from ui.components import (
    Colors, Fonts, SectionHeader, ComponentCheckbox,
    AccentButton, SecondaryButton, ProgressCard, GlassCard
)
from core.profile_scanner import ProfileScanner, UserProfile
from core.profile_exporter import ProfileExporter
from utils.helpers import get_size_display, load_settings, save_settings, add_recent_operation


class ExportPage(ctk.CTkScrollableFrame):
    """Dışa aktarma sayfası."""

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
        self._scanner = ProfileScanner()
        self._exporter = ProfileExporter()
        self._selected_profile = None
        self._checkboxes = []
        self._exporting = False

        self._build_ui()

    def _build_ui(self):
        """UI'ı oluştur."""
        # ── Başlık ──
        SectionHeader(
            self, title="📤  Profil Dışa Aktarma",
            subtitle="Profil bileşenlerini seçin ve ZIP paketi olarak kaydedin"
        ).pack(fill="x", padx=30, pady=(24, 16))

        # ── Profil Seçimi ──
        profile_section = GlassCard(self, title="Kaynak Profil", icon="👤")
        profile_section.pack(fill="x", padx=30, pady=(0, 12))

        profile_inner = ctk.CTkFrame(profile_section, fg_color="transparent")
        profile_inner.pack(fill="x", padx=16, pady=(0, 16))

        self._profile_combo = ctk.CTkComboBox(
            profile_inner,
            values=["Taranıyor..."],
            font=Fonts.BODY,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            button_color=Colors.ACCENT_PRIMARY,
            button_hover_color=Colors.ACCENT_SECONDARY,
            dropdown_fg_color=Colors.BG_CARD,
            dropdown_hover_color=Colors.ACCENT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            text_color=Colors.TEXT_PRIMARY,
            width=400,
            command=self._on_profile_selected,
            state="readonly"
        )
        self._profile_combo.pack(side="left")

        self._scan_btn = SecondaryButton(
            profile_inner, text="Yeniden Tara", icon="🔄",
            command=self._scan_profiles, width=150
        )
        self._scan_btn.pack(side="left", padx=(12, 0))

        # ── Bileşen Seçimi ──
        self._components_header = SectionHeader(
            self, title="Taşınacak Bileşenler",
            subtitle="Dışa aktarmak istediğiniz bileşenleri seçin"
        )
        self._components_header.pack(fill="x", padx=30, pady=(16, 8))

        # Tümünü seç/kaldır butonları
        select_frame = ctk.CTkFrame(self, fg_color="transparent")
        select_frame.pack(fill="x", padx=30, pady=(0, 8))

        SecondaryButton(
            select_frame, text="Tümünü Seç", icon="☑️",
            command=self._select_all, width=130
        ).pack(side="left", padx=(0, 8))

        SecondaryButton(
            select_frame, text="Seçimi Kaldır", icon="⬜",
            command=self._deselect_all, width=140
        ).pack(side="left")

        self._size_label = ctk.CTkLabel(
            select_frame, text="Toplam: 0 B",
            font=Fonts.SMALL_BOLD, text_color=Colors.ACCENT_SECONDARY
        )
        self._size_label.pack(side="right")

        # Bileşen listesi container
        self._components_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._components_frame.pack(fill="x", padx=30)

        # ── Kategori başlıkları ile bileşenler ──
        # (Profil tarandıktan sonra doldurulacak)

        # ── Dışa Aktarma Ayarları ──
        settings_card = GlassCard(self, title="Dışa Aktarma Ayarları", icon="⚙️")
        settings_card.pack(fill="x", padx=30, pady=(16, 8))

        settings_inner = ctk.CTkFrame(settings_card, fg_color="transparent")
        settings_inner.pack(fill="x", padx=16, pady=(0, 16))

        # Kayıt yeri
        loc_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        loc_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            loc_frame, text="Kayıt Yeri:", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY
        ).pack(side="left")

        self._output_path = ctk.CTkEntry(
            loc_frame, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=300
        )
        self._output_path.pack(side="left", padx=8)
        self._output_path.insert(0, self._settings.get("export_location", str(Path.home() / "Desktop")))

        SecondaryButton(
            loc_frame, text="Gözat", icon="📂",
            command=self._browse_output, width=100
        ).pack(side="left")

        # Sıkıştırma seviyesi
        comp_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        comp_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            comp_frame, text="Sıkıştırma:", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY
        ).pack(side="left")

        self._compression_var = ctk.StringVar(
            value=self._settings.get("compression_level", "normal")
        )

        for text, value in [("Hızlı", "fast"), ("Normal", "normal"), ("Maksimum", "maximum")]:
            ctk.CTkRadioButton(
                comp_frame, text=text, variable=self._compression_var,
                value=value, font=Fonts.BODY,
                fg_color=Colors.ACCENT_PRIMARY,
                border_color=Colors.BORDER,
                hover_color=Colors.ACCENT_SECONDARY,
                text_color=Colors.TEXT_PRIMARY
            ).pack(side="left", padx=(16, 0))

        # ── İlerleme Kartı (gizli) ──
        self._progress_card = ProgressCard(self, title="Dışa Aktarılıyor...")
        # Başlangıçta gizli

        # ── Aksiyon Butonları ──
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=30, pady=(16, 24))

        self._export_btn = AccentButton(
            action_frame, text="Dışa Aktarmayı Başlat", icon="📤",
            command=self._start_export, width=250
        )
        self._export_btn.pack(side="right")

        self._cancel_btn = SecondaryButton(
            action_frame, text="İptal", icon="❌",
            command=self._cancel_export, width=120
        )
        # İptal butonu başlangıçta gizli

        # Alt boşluk
        ctk.CTkFrame(self, fg_color="transparent", height=20).pack()

        # Profilleri tara
        self._scan_profiles()

    def _scan_profiles(self):
        """Profilleri tara."""
        self._profile_combo.configure(values=["Taranıyor..."])
        self._profile_combo.set("Taranıyor...")

        def scan():
            profiles = self._scanner.scan_profiles()
            self.after(0, lambda: self._update_profiles(profiles))

        threading.Thread(target=scan, daemon=True).start()

    def _update_profiles(self, profiles):
        """Profil listesini güncelle."""
        if not profiles:
            self._profile_combo.configure(values=["Profil bulunamadı"])
            self._profile_combo.set("Profil bulunamadı")
            return

        names = []
        for p in profiles:
            suffix = " (Mevcut)" if p.is_current else ""
            names.append(f"{p.username}{suffix}")

        self._profile_combo.configure(values=names)
        self._profile_combo.set(names[0])
        self._on_profile_selected(names[0])

    def _on_profile_selected(self, selection: str):
        """Profil seçildiğinde bileşenleri göster."""
        username = selection.replace(" (Mevcut)", "").strip()

        for p in self._scanner.profiles:
            if p.username == username:
                self._selected_profile = p
                break

        if self._selected_profile:
            self._populate_components(self._selected_profile)

    def _populate_components(self, profile: UserProfile):
        """Bileşen checkbox'larını oluştur."""
        # Mevcut checkbox'ları temizle
        for widget in self._components_frame.winfo_children():
            widget.destroy()
        self._checkboxes.clear()

        # Kategorilere göre grupla
        categories = {
            "files": ("📁 Dosya Klasörleri", []),
            "settings": ("⚙️ Uygulama Ayarları", []),
            "system": ("🔧 Sistem Ayarları", []),
        }

        for comp in profile.components:
            cat = comp.category if comp.category in categories else "system"
            categories[cat][1].append(comp)

        for cat_id, (cat_title, components) in categories.items():
            if not components:
                continue

            # Kategori başlığı
            cat_label = ctk.CTkLabel(
                self._components_frame,
                text=cat_title,
                font=Fonts.BODY_BOLD,
                text_color=Colors.TEXT_ACCENT,
                anchor="w"
            )
            cat_label.pack(fill="x", pady=(12, 4))

            for comp in components:
                cb = ComponentCheckbox(
                    self._components_frame,
                    component_id=comp.id,
                    icon=comp.icon,
                    name=comp.name,
                    description=comp.description,
                    size_text="Hesaplanıyor..." if comp.path and comp.available else "",
                    available=comp.available,
                    requires_admin=comp.requires_admin
                )
                cb.pack(fill="x", pady=2)
                # Boyut değişikliği callback'i
                cb.var.trace_add("write", lambda *args: self._update_size())
                self._checkboxes.append(cb)

        self._update_size()

        # Arka planda boyutları hesapla
        self._calculate_sizes_async(profile)

    def _calculate_sizes_async(self, profile: UserProfile):
        """Bileşen boyutlarını arka planda hesapla ve UI'ı güncelle."""
        from utils.helpers import get_dir_size

        def calculate():
            for comp in profile.components:
                if comp.path and comp.available and not comp.requires_admin:
                    try:
                        size = get_dir_size(comp.path)
                        comp.size = size
                        # UI'daki ilgili checkbox'ı güncelle
                        self.after(0, lambda c=comp: self._update_checkbox_size(c))
                    except (PermissionError, OSError):
                        comp.size = -1
                        self.after(0, lambda c=comp: self._update_checkbox_size(c))

            # Toplam boyutu güncelle
            self.after(0, self._update_size)

        threading.Thread(target=calculate, daemon=True).start()

    def _update_checkbox_size(self, comp):
        """Tek bir checkbox'ın boyut bilgisini güncelle."""
        for cb in self._checkboxes:
            if cb.component_id == comp.id:
                size_text = get_size_display(comp.size) if comp.size > 0 else ""
                # size_label'ı güncelle (ComponentCheckbox içindeki sağdaki label)
                for widget in cb.winfo_children():
                    for sub in widget.winfo_children():
                        if hasattr(sub, 'cget'):
                            try:
                                current = sub.cget("text")
                                if current == "Hesaplanıyor..." or current.endswith(("B", "KB", "MB", "GB", "TB")):
                                    sub.configure(text=size_text)
                                    return
                            except Exception:
                                continue

    def _update_size(self):
        """Toplam seçili boyutu güncelle."""
        if not self._selected_profile:
            return

        selected_ids = [cb.component_id for cb in self._checkboxes if cb.is_selected]
        total_size = self._scanner.get_selected_components_size(
            self._selected_profile, selected_ids
        )
        self._size_label.configure(text=f"Toplam: {get_size_display(total_size)}")

    def _select_all(self):
        for cb in self._checkboxes:
            cb.is_selected = True

    def _deselect_all(self):
        for cb in self._checkboxes:
            cb.is_selected = False

    def _browse_output(self):
        """Çıktı dizini seç."""
        path = filedialog.askdirectory(
            title="Dışa Aktarma Konumu Seçin",
            initialdir=self._output_path.get()
        )
        if path:
            self._output_path.delete(0, "end")
            self._output_path.insert(0, path)

    def _start_export(self):
        """Dışa aktarmayı başlat."""
        if self._exporting:
            return

        selected_ids = [cb.component_id for cb in self._checkboxes if cb.is_selected]
        if not selected_ids:
            self._show_message("Lütfen en az bir bileşen seçin!", "warning")
            return

        if not self._selected_profile:
            return

        output_path = Path(self._output_path.get())

        self._exporting = True
        self._export_btn.configure(state="disabled")
        self._progress_card.pack(fill="x", padx=30, pady=(8, 0))
        self._cancel_btn.pack(side="left")

        def progress_cb(current, total, message):
            self.after(0, lambda: self._progress_card.update_progress(
                current / total, message,
                f"Adım {current}/{total}"
            ))

        def export_thread():
            result = self._exporter.export_profile(
                self._selected_profile, selected_ids,
                output_path,
                compression=self._compression_var.get(),
                progress_callback=progress_cb
            )
            self.after(0, lambda: self._export_complete(result))

        threading.Thread(target=export_thread, daemon=True).start()

    def _export_complete(self, result_path):
        """Dışa aktarma tamamlandı."""
        self._exporting = False
        self._export_btn.configure(state="normal")
        self._cancel_btn.pack_forget()

        if result_path:
            self._progress_card.set_complete(
                f"✅ Paket oluşturuldu: {result_path.name}"
            )
            # Son işlemlere ekle
            add_recent_operation(self._settings, {
                "type": "export",
                "description": f"Profil dışa aktarıldı: {self._selected_profile.username}",
                "file": str(result_path),
            })
        else:
            self._progress_card.set_error("❌ Dışa aktarma başarısız oldu!")

    def _cancel_export(self):
        """Dışa aktarmayı iptal et."""
        self._exporter.cancel()
        self._progress_card.set_error("İptal edildi")
        self._exporting = False
        self._export_btn.configure(state="normal")
        self._cancel_btn.pack_forget()

    def _show_message(self, message: str, msg_type: str = "info"):
        """Bilgi mesajı göster."""
        color_map = {
            "info": Colors.INFO,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
            "success": Colors.SUCCESS,
        }

        msg_frame = ctk.CTkFrame(
            self, fg_color=color_map.get(msg_type, Colors.INFO),
            corner_radius=8, height=40
        )
        msg_frame.pack(fill="x", padx=30, pady=4)
        msg_frame.pack_propagate(False)

        ctk.CTkLabel(
            msg_frame, text=f"  {message}",
            font=Fonts.BODY, text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=12)

        # 3 saniye sonra kaldır
        self.after(3000, msg_frame.destroy)
