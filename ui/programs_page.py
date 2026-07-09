"""
WinProfileMigrator - Program Taşıma Sayfası
Kurulu programları listele, dışa aktar ve yeni PC'de otomatik kur.
"""
import threading
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import List

from ui.components import (
    Colors, Fonts, SectionHeader, GlassCard,
    AccentButton, SecondaryButton, ProgressCard, StatusBadge
)
from core.program_scanner import ProgramScanner, ProgramInstaller, InstalledProgram
from utils.helpers import add_recent_operation


class ProgramRow(ctk.CTkFrame):
    """Tek bir program satırı."""

    STATUS_COLORS = {
        "pending": Colors.TEXT_MUTED,
        "installing": Colors.WARNING,
        "installed": Colors.SUCCESS,
        "failed": Colors.ERROR,
        "skipped": Colors.TEXT_MUTED,
    }

    STATUS_ICONS = {
        "pending": "⏳",
        "installing": "⏳",
        "installed": "✅",
        "failed": "❌",
        "skipped": "⏭️",
    }

    STATUS_TEXT = {
        "pending": "Bekliyor",
        "installing": "Kuruluyor...",
        "installed": "Kuruldu",
        "failed": "Başarısız",
        "skipped": "Atlandı",
    }

    def __init__(self, master, program: InstalledProgram, show_checkbox: bool = True,
                 show_status: bool = False, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
            height=50,
            **kwargs
        )
        self.pack_propagate(False)

        self.program = program

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=6)

        # Sol: checkbox + isim
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="y")

        if show_checkbox:
            self.var = ctk.BooleanVar(value=program.selected)
            self.checkbox = ctk.CTkCheckBox(
                left, text="", variable=self.var,
                width=22, height=22,
                fg_color=Colors.ACCENT_PRIMARY,
                hover_color=Colors.ACCENT_SECONDARY,
                border_color=Colors.BORDER,
                checkmark_color=Colors.TEXT_PRIMARY,
                command=self._on_toggle
            )
            self.checkbox.pack(side="left", padx=(0, 8))

        # Winget ikonu
        if program.can_auto_install:
            ctk.CTkLabel(
                left, text="📦", font=("Segoe UI Emoji", 14)
            ).pack(side="left", padx=(0, 6))
        else:
            ctk.CTkLabel(
                left, text="📋", font=("Segoe UI Emoji", 14),
                text_color=Colors.TEXT_MUTED
            ).pack(side="left", padx=(0, 6))

        # İsim ve versiyon
        text_frame = ctk.CTkFrame(left, fg_color="transparent")
        text_frame.pack(side="left")

        ctk.CTkLabel(
            text_frame, text=program.name, font=Fonts.BODY_BOLD,
            text_color=Colors.TEXT_PRIMARY, anchor="w"
        ).pack(anchor="w")

        detail_parts = []
        if program.version:
            detail_parts.append(f"v{program.version}")
        if program.publisher:
            detail_parts.append(program.publisher)
        if program.id and program.source in ("winget", "msstore", ""):
            detail_parts.append(program.id)

        if detail_parts:
            ctk.CTkLabel(
                text_frame, text=" • ".join(detail_parts[:2]),
                font=Fonts.TINY, text_color=Colors.TEXT_MUTED, anchor="w"
            ).pack(anchor="w")

        # Sağ: durum veya etiket
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="right")

        if show_status:
            self.status_label = ctk.CTkLabel(
                right,
                text=f"{self.STATUS_ICONS.get(program.status, '⏳')} {self.STATUS_TEXT.get(program.status, '')}",
                font=Fonts.SMALL,
                text_color=self.STATUS_COLORS.get(program.status, Colors.TEXT_MUTED)
            )
            self.status_label.pack(side="right")

            if program.error_message and program.status in ("failed", "skipped"):
                ctk.CTkLabel(
                    right, text=program.error_message[:50],
                    font=Fonts.TINY, text_color=Colors.TEXT_MUTED
                ).pack(side="right", padx=(0, 8))
        else:
            if program.can_auto_install:
                StatusBadge(right, "Otomatik Kurulabilir", "success").pack(side="right")
            else:
                StatusBadge(right, "Manuel Kurulum", "warning").pack(side="right")

    def _on_toggle(self):
        self.program.selected = self.var.get()

    def update_status(self, status: str, error: str = ""):
        """Durumu güncelle."""
        self.program.status = status
        if hasattr(self, "status_label"):
            icon = self.STATUS_ICONS.get(status, "⏳")
            text = self.STATUS_TEXT.get(status, "")
            color = self.STATUS_COLORS.get(status, Colors.TEXT_MUTED)
            self.status_label.configure(text=f"{icon} {text}", text_color=color)


class ProgramsPage(ctk.CTkScrollableFrame):
    """Program taşıma sayfası."""

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
        self._scanner = ProgramScanner()
        self._installer = ProgramInstaller()
        self._programs: List[InstalledProgram] = []
        self._program_rows: List[ProgramRow] = []
        self._mode = None  # "export" veya "import"

        self._build_ui()

    def _build_ui(self):
        """UI'ı oluştur."""
        SectionHeader(
            self, title="💿  Program Taşıma",
            subtitle="Kurulu programlarınızı yeni bilgisayara kolayca taşıyın"
        ).pack(fill="x", padx=30, pady=(24, 16))

        # ── Mod Seçimi ──
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=30, pady=(0, 16))
        mode_frame.columnconfigure((0, 1), weight=1, uniform="pmode")

        # Dışa aktar kartı
        from ui.components import ActionCard
        self._export_card = ActionCard(
            mode_frame,
            title="Program Listesi Çıkar",
            icon="📤",
            description="Bu PC'deki programları listele ve dışa aktar",
            accent_color="#7c3aed",
            on_click=lambda: self._set_mode("export")
        )
        self._export_card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self._import_card = ActionCard(
            mode_frame,
            title="Programları Kur",
            icon="📥",
            description="Listeden programları otomatik kur (winget)",
            accent_color="#3b82f6",
            on_click=lambda: self._set_mode("import")
        )
        self._import_card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        # ══════════════════════════════════════════
        # EXPORT PANELİ
        # ══════════════════════════════════════════
        self._export_panel = ctk.CTkFrame(self, fg_color="transparent")

        # Tarama durumu
        self._scan_status = ctk.CTkLabel(
            self._export_panel, text="", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY
        )
        self._scan_status.pack(fill="x", padx=0, pady=(0, 8))

        # Filtre ve butonlar
        filter_frame = ctk.CTkFrame(self._export_panel, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 8))

        self._search_entry = ctk.CTkEntry(
            filter_frame, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=300,
            placeholder_text="🔍 Program ara..."
        )
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", self._filter_programs)

        SecondaryButton(
            filter_frame, text="Tümünü Seç", icon="☑️",
            command=self._select_all, width=130
        ).pack(side="left", padx=(12, 4))

        SecondaryButton(
            filter_frame, text="Seçimi Kaldır", icon="⬜",
            command=self._deselect_all, width=140
        ).pack(side="left", padx=(4, 0))

        self._count_label = ctk.CTkLabel(
            filter_frame, text="", font=Fonts.SMALL_BOLD,
            text_color=Colors.ACCENT_SECONDARY
        )
        self._count_label.pack(side="right")

        # Program listesi container
        self._programs_frame = ctk.CTkFrame(self._export_panel, fg_color="transparent")
        self._programs_frame.pack(fill="x")

        # Dışa aktarma butonu
        export_action = ctk.CTkFrame(self._export_panel, fg_color="transparent")
        export_action.pack(fill="x", pady=(16, 8))

        self._export_btn = AccentButton(
            export_action, text="Listeyi Dışa Aktar", icon="💾",
            command=self._export_list, width=220
        )
        self._export_btn.pack(side="right")

        # ══════════════════════════════════════════
        # IMPORT PANELİ
        # ══════════════════════════════════════════
        self._import_panel = ctk.CTkFrame(self, fg_color="transparent")

        # Dosya seçimi
        file_card = GlassCard(self._import_panel, title="Program Listesi Dosyası", icon="📦")
        file_card.pack(fill="x", pady=(0, 12))

        file_inner = ctk.CTkFrame(file_card, fg_color="transparent")
        file_inner.pack(fill="x", padx=16, pady=(0, 16))

        self._import_file_entry = ctk.CTkEntry(
            file_inner, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=350,
            placeholder_text="installed_programs.json seçin..."
        )
        self._import_file_entry.pack(side="left")

        AccentButton(
            file_inner, text="Dosya Seç", icon="📂",
            command=self._browse_import_file, width=140
        ).pack(side="left", padx=(12, 0))

        # Winget bilgisi
        self._winget_info = ctk.CTkFrame(self._import_panel, fg_color="transparent")
        self._winget_info.pack(fill="x", pady=(0, 8))

        # İçe aktarılan program listesi
        self._import_filter = ctk.CTkFrame(self._import_panel, fg_color="transparent")

        self._import_search = ctk.CTkEntry(
            self._import_filter, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=300,
            placeholder_text="🔍 Program ara..."
        )
        self._import_search.pack(side="left")

        self._import_count = ctk.CTkLabel(
            self._import_filter, text="", font=Fonts.SMALL_BOLD,
            text_color=Colors.ACCENT_SECONDARY
        )
        self._import_count.pack(side="right")

        self._import_programs_frame = ctk.CTkFrame(self._import_panel, fg_color="transparent")

        # İlerleme kartı
        self._install_progress = ProgressCard(self._import_panel, title="Programlar Kuruluyor...")

        # Kurulum butonu
        install_action = ctk.CTkFrame(self._import_panel, fg_color="transparent")
        install_action.pack(fill="x", pady=(16, 8))

        self._install_btn = AccentButton(
            install_action, text="Kurulumu Başlat", icon="🚀",
            accent=Colors.SUCCESS, hover="#059669",
            command=self._start_install, width=220
        )
        self._install_btn.pack(side="right")

        self._cancel_install_btn = SecondaryButton(
            install_action, text="İptal", icon="❌",
            command=self._cancel_install, width=120
        )

        # Sonuç paneli
        self._results_frame = ctk.CTkFrame(self._import_panel, fg_color="transparent")

        # Alt boşluk
        ctk.CTkFrame(self, fg_color="transparent", height=30).pack()

    def _set_mode(self, mode: str):
        """Modu ayarla."""
        self._mode = mode

        if mode == "export":
            self._export_card.configure(border_color=Colors.ACCENT_PRIMARY)
            self._import_card.configure(border_color=Colors.BORDER)
            self._import_panel.pack_forget()
            self._export_panel.pack(fill="x", padx=30, pady=(8, 0))
            # Programları tara
            if not self._programs:
                self._scan_programs()
        else:
            self._export_card.configure(border_color=Colors.BORDER)
            self._import_card.configure(border_color=Colors.INFO)
            self._export_panel.pack_forget()
            self._import_panel.pack(fill="x", padx=30, pady=(8, 0))
            self._check_winget()

    def _scan_programs(self):
        """Programları arka planda tara."""
        self._scan_status.configure(text="🔍 Kurulu programlar taranıyor...")

        def scan():
            def progress(msg):
                self.after(0, lambda: self._scan_status.configure(text=msg))

            programs = self._scanner.scan_programs(progress_callback=progress)
            self.after(0, lambda: self._display_programs(programs))

        threading.Thread(target=scan, daemon=True).start()

    def _display_programs(self, programs: List[InstalledProgram]):
        """Program listesini göster."""
        self._programs = programs

        auto_count = sum(1 for p in programs if p.can_auto_install)
        self._scan_status.configure(
            text=f"✅ {len(programs)} program bulundu — {auto_count} tanesi otomatik kurulabilir"
        )
        self._count_label.configure(text=f"{len(programs)} program")

        self._populate_program_list(programs, self._programs_frame, show_checkbox=True)

    def _populate_program_list(self, programs: List[InstalledProgram],
                                container: ctk.CTkFrame,
                                show_checkbox: bool = True,
                                show_status: bool = False):
        """Program satırlarını oluştur."""
        for widget in container.winfo_children():
            widget.destroy()
        self._program_rows.clear()

        for prog in programs:
            row = ProgramRow(
                container, prog,
                show_checkbox=show_checkbox,
                show_status=show_status
            )
            row.pack(fill="x", pady=2)
            self._program_rows.append(row)

    def _filter_programs(self, event=None):
        """Program listesini filtrele."""
        query = self._search_entry.get().lower().strip()

        for row in self._program_rows:
            if not query or query in row.program.name.lower() or query in row.program.id.lower():
                row.pack(fill="x", pady=2)
            else:
                row.pack_forget()

    def _select_all(self):
        for row in self._program_rows:
            if hasattr(row, 'var'):
                row.var.set(True)
                row.program.selected = True

    def _deselect_all(self):
        for row in self._program_rows:
            if hasattr(row, 'var'):
                row.var.set(False)
                row.program.selected = False

    def _export_list(self):
        """Program listesini dışa aktar."""
        selected = [p for p in self._programs if p.selected]
        if not selected:
            return

        path = filedialog.askdirectory(
            title="Program Listesi Kayıt Konumu",
            initialdir=self._settings.get("export_location", str(Path.home() / "Desktop"))
        )
        if not path:
            return

        output_file = self._scanner.export_program_list(selected, Path(path))

        add_recent_operation(self._settings, {
            "type": "export",
            "description": f"Program listesi dışa aktarıldı ({len(selected)} program)",
            "file": str(output_file),
        })

        # Başarı mesajı
        msg = ctk.CTkFrame(self._export_panel, fg_color=Colors.SUCCESS, corner_radius=8, height=44)
        msg.pack(fill="x", pady=8)
        msg.pack_propagate(False)
        ctk.CTkLabel(
            msg, text=f"✅ {len(selected)} program listesi kaydedildi: {output_file.name}",
            font=Fonts.BODY, text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=12)
        self.after(5000, msg.destroy)

    def _browse_import_file(self):
        """İçe aktarılacak dosya seç."""
        path = filedialog.askopenfilename(
            title="Program Listesi Dosyası",
            filetypes=[("JSON", "*.json"), ("Tüm Dosyalar", "*.*")]
        )
        if path:
            self._import_file_entry.delete(0, "end")
            self._import_file_entry.insert(0, path)
            self._load_import_list(Path(path))

    def _load_import_list(self, file_path: Path):
        """İçe aktarılacak program listesini yükle."""
        programs = self._scanner.load_program_list(file_path)

        if not programs:
            return

        auto_count = sum(1 for p in programs if p.can_auto_install)
        self._import_count.configure(
            text=f"{len(programs)} program — {auto_count} otomatik kurulabilir"
        )

        self._import_filter.pack(fill="x", pady=(8, 8))
        self._import_programs_frame.pack(fill="x")
        self._populate_program_list(programs, self._import_programs_frame,
                                     show_checkbox=True, show_status=False)
        self._programs = programs

    def _check_winget(self):
        """Winget durumunu kontrol et."""
        for w in self._winget_info.winfo_children():
            w.destroy()

        if self._scanner.is_winget_available():
            StatusBadge(self._winget_info, "✓ winget kurulu — otomatik kurulum kullanılabilir",
                        "success").pack(anchor="w")
        else:
            warn = ctk.CTkFrame(self._winget_info, fg_color="#78350f", corner_radius=8, height=40)
            warn.pack(fill="x")
            warn.pack_propagate(False)
            ctk.CTkLabel(
                warn, text="⚠️ winget bulunamadı! Otomatik kurulum yapılamaz. Windows App Installer'ı kurun.",
                font=Fonts.BODY, text_color=Colors.WARNING
            ).pack(side="left", padx=12)

    def _start_install(self):
        """Kurulumu başlat."""
        selected = [p for p in self._programs if p.selected]
        if not selected:
            return

        self._install_btn.configure(state="disabled")
        self._install_progress.pack(fill="x", pady=(12, 0))
        self._cancel_install_btn.pack(side="left")

        def progress_cb(current, total, name, status):
            pct = current / total if total > 0 else 0
            self.after(0, lambda: self._install_progress.update_progress(
                pct, f"📦 {name}",
                f"{current}/{total} — {status}"
            ))

        def install():
            results = self._installer.install_programs(selected, progress_cb)
            self.after(0, lambda: self._install_complete(results))

        threading.Thread(target=install, daemon=True).start()

    def _install_complete(self, results: List[InstalledProgram]):
        """Kurulum tamamlandı."""
        self._install_btn.configure(state="normal")
        self._cancel_install_btn.pack_forget()

        summary = self._installer.get_summary()
        self._install_progress.set_complete(
            f"✅ Kuruldu: {summary['installed']} | "
            f"❌ Başarısız: {summary['failed']} | "
            f"⏭️ Atlandı: {summary['skipped']}"
        )

        # Sonuç listesini göster
        self._results_frame.pack(fill="x", pady=(16, 0))

        SectionHeader(
            self._results_frame, title="Kurulum Sonuçları",
            subtitle="Her programın kurulum durumu"
        ).pack(fill="x", pady=(0, 8))

        for widget in list(self._results_frame.winfo_children())[1:]:
            widget.destroy()

        for prog in results:
            row = ProgramRow(
                self._results_frame, prog,
                show_checkbox=False, show_status=True
            )
            row.pack(fill="x", pady=2)

        add_recent_operation(self._settings, {
            "type": "import",
            "description": f"Program kurulumu: {summary['installed']} kuruldu, {summary['failed']} başarısız",
        })

    def _cancel_install(self):
        """Kurulumu iptal et."""
        self._installer.cancel()
