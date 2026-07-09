"""
WinProfileMigrator - Profil Klonlama Sayfası
Mevcut profili kopyalayarak yeni yerel profil oluşturma.
"""
import threading
import subprocess
import customtkinter as ctk
from pathlib import Path

from ui.components import (
    Colors, Fonts, SectionHeader, GlassCard, ComponentCheckbox,
    AccentButton, SecondaryButton, ProgressCard, InfoRow
)
from core.profile_scanner import ProfileScanner
from core.profile_exporter import ProfileExporter
from core.profile_importer import ProfileImporter
from utils.helpers import is_admin, add_recent_operation


class ClonePage(ctk.CTkScrollableFrame):
    """Profil klonlama sayfası."""

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
        self._importer = ProfileImporter()
        self._selected_profile = None
        self._checkboxes = []
        self._cloning = False

        self._build_ui()

    def _build_ui(self):
        """UI'ı oluştur."""
        # ── Başlık ──
        SectionHeader(
            self, title="📋  Profil Klonlama",
            subtitle="Mevcut bir profili kopyalayarak yeni kullanıcı profili oluşturun"
        ).pack(fill="x", padx=30, pady=(24, 16))

        # Admin uyarısı
        if not is_admin():
            warn_frame = ctk.CTkFrame(
                self, fg_color="#78350f",
                corner_radius=8, height=44
            )
            warn_frame.pack(fill="x", padx=30, pady=(0, 12))
            warn_frame.pack_propagate(False)

            ctk.CTkLabel(
                warn_frame,
                text="⚠️  Profil klonlama yönetici yetkisi gerektirir. Bazı özellikler kısıtlı olabilir.",
                font=Fonts.BODY, text_color=Colors.WARNING
            ).pack(side="left", padx=12)

        # ── Kaynak Profil ──
        source_card = GlassCard(self, title="Kaynak Profil", icon="👤")
        source_card.pack(fill="x", padx=30, pady=(0, 12))

        source_inner = ctk.CTkFrame(source_card, fg_color="transparent")
        source_inner.pack(fill="x", padx=16, pady=(0, 16))

        self._profile_combo = ctk.CTkComboBox(
            source_inner,
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

        SecondaryButton(
            source_inner, text="Yeniden Tara", icon="🔄",
            command=self._scan_profiles, width=150
        ).pack(side="left", padx=(12, 0))

        # ── Hedef Profil Bilgileri ──
        target_card = GlassCard(self, title="Yeni Profil Bilgileri", icon="➕")
        target_card.pack(fill="x", padx=30, pady=(0, 12))

        target_inner = ctk.CTkFrame(target_card, fg_color="transparent")
        target_inner.pack(fill="x", padx=16, pady=(0, 16))

        # Kullanıcı adı
        name_frame = ctk.CTkFrame(target_inner, fg_color="transparent")
        name_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            name_frame, text="Kullanıcı Adı:", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY, width=120, anchor="w"
        ).pack(side="left")

        self._username_entry = ctk.CTkEntry(
            name_frame, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=300,
            placeholder_text="Yeni kullanıcı adını girin"
        )
        self._username_entry.pack(side="left", padx=(8, 0))

        # Şifre
        pass_frame = ctk.CTkFrame(target_inner, fg_color="transparent")
        pass_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            pass_frame, text="Şifre:", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY, width=120, anchor="w"
        ).pack(side="left")

        self._password_entry = ctk.CTkEntry(
            pass_frame, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=300,
            placeholder_text="Şifre (boş bırakılabilir)",
            show="●"
        )
        self._password_entry.pack(side="left", padx=(8, 0))

        # ── Kopyalanacak Bileşenler ──
        comp_header = SectionHeader(
            self, title="Kopyalanacak Bileşenler",
            subtitle="Yeni profile aktarılacak bileşenleri seçin"
        )
        comp_header.pack(fill="x", padx=30, pady=(16, 8))

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

        self._components_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._components_frame.pack(fill="x", padx=30)

        # ── İlerleme ──
        self._progress_card = ProgressCard(self, title="Profil Klonlanıyor...")

        # ── Aksiyon ──
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=30, pady=(16, 24))

        self._clone_btn = AccentButton(
            action_frame, text="Klonlamayı Başlat", icon="📋",
            accent=Colors.WARNING, hover="#d97706",
            command=self._start_clone, width=220
        )
        self._clone_btn.pack(side="right")

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
        """Profil seçildi."""
        username = selection.replace(" (Mevcut)", "").strip()
        for p in self._scanner.profiles:
            if p.username == username:
                self._selected_profile = p
                self._populate_components(p)
                break

    def _populate_components(self, profile):
        """Bileşen listesini doldur."""
        for widget in self._components_frame.winfo_children():
            widget.destroy()
        self._checkboxes.clear()

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

            ctk.CTkLabel(
                self._components_frame, text=cat_title,
                font=Fonts.BODY_BOLD, text_color=Colors.TEXT_ACCENT, anchor="w"
            ).pack(fill="x", pady=(12, 4))

            for comp in components:
                cb = ComponentCheckbox(
                    self._components_frame,
                    component_id=comp.id,
                    icon=comp.icon,
                    name=comp.name,
                    description=comp.description,
                    size_text=comp.size_display if comp.size > 0 else "",
                    available=comp.available,
                    requires_admin=comp.requires_admin
                )
                cb.pack(fill="x", pady=2)
                self._checkboxes.append(cb)

    def _select_all(self):
        for cb in self._checkboxes:
            cb.is_selected = True

    def _deselect_all(self):
        for cb in self._checkboxes:
            cb.is_selected = False

    def _start_clone(self):
        """Klonlama işlemini başlat."""
        if self._cloning or not self._selected_profile:
            return

        new_username = self._username_entry.get().strip()
        if not new_username:
            self._show_message("Lütfen bir kullanıcı adı girin!", "warning")
            return

        selected_ids = [cb.component_id for cb in self._checkboxes if cb.is_selected]
        if not selected_ids:
            self._show_message("Lütfen en az bir bileşen seçin!", "warning")
            return

        self._cloning = True
        self._clone_btn.configure(state="disabled")
        self._progress_card.pack(fill="x", padx=30, pady=(8, 0))

        password = self._password_entry.get()

        def progress_cb(current, total, message):
            self.after(0, lambda: self._progress_card.update_progress(
                current / total, message,
                f"Adım {current}/{total}"
            ))

        def clone():
            # Adım 1: Yeni kullanıcı oluştur (admin gerekli)
            self.after(0, lambda: self._progress_card.update_progress(
                0.1, "👤 Yeni kullanıcı oluşturuluyor...", "Adım 1/3"
            ))

            user_created = self._create_user(new_username, password)

            if not user_created:
                self.after(0, lambda: self._clone_complete(False,
                    "Kullanıcı oluşturulamadı. Yönetici yetkisi gerekebilir."))
                return

            # Adım 2: Profili dışa aktar
            import tempfile
            with tempfile.TemporaryDirectory(prefix="WPM_clone_") as temp_dir:
                temp_path = Path(temp_dir)

                self.after(0, lambda: self._progress_card.update_progress(
                    0.3, "📤 Kaynak profil dışa aktarılıyor...", "Adım 2/3"
                ))

                zip_path = self._exporter.export_profile(
                    self._selected_profile, selected_ids,
                    temp_path, compression="fast"
                )

                if not zip_path:
                    self.after(0, lambda: self._clone_complete(False,
                        "Profil dışa aktarılamadı."))
                    return

                # Adım 3: Yeni profile içe aktar
                self.after(0, lambda: self._progress_card.update_progress(
                    0.7, "📥 Ayarlar yeni profile aktarılıyor...", "Adım 3/3"
                ))

                new_profile_path = Path(f"C:/Users/{new_username}")
                result = self._importer.import_profile(
                    zip_path, selected_ids,
                    target_profile_path=new_profile_path,
                    auto_backup=False
                )

                self.after(0, lambda: self._clone_complete(result))

        threading.Thread(target=clone, daemon=True).start()

    def _create_user(self, username: str, password: str) -> bool:
        """Yeni Windows kullanıcısı oluştur."""
        try:
            cmd = f'net user "{username}" "{password}" /add'
            if not password:
                cmd = f'net user "{username}" "" /add'

            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    def _clone_complete(self, success: bool, error_msg: str = ""):
        """Klonlama tamamlandı."""
        self._cloning = False
        self._clone_btn.configure(state="normal")

        if success:
            self._progress_card.set_complete(
                f"✅ Profil başarıyla klonlandı: {self._username_entry.get()}"
            )
            add_recent_operation(self._settings, {
                "type": "clone",
                "description": f"Profil klonlandı: {self._selected_profile.username} → {self._username_entry.get()}"
            })
        else:
            msg = error_msg or "Klonlama başarısız oldu!"
            self._progress_card.set_error(f"❌ {msg}")

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
        msg_frame.pack(fill="x", padx=30, pady=4)
        msg_frame.pack_propagate(False)

        ctk.CTkLabel(
            msg_frame, text=f"  {message}",
            font=Fonts.BODY, text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=12)

        self.after(3000, msg_frame.destroy)
