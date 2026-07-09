"""
WinProfileMigrator - Yeniden Kullanılabilir UI Bileşenleri
Modern, şık ve tutarlı UI elementleri.
"""
import customtkinter as ctk
from typing import Callable, Optional


# ═══════════════════════════════════════════════════════
# Renk Paleti
# ═══════════════════════════════════════════════════════
class Colors:
    """Uygulama renk teması."""
    # Ana renkler
    BG_DARK = "#0d1117"
    BG_PRIMARY = "#161b22"
    BG_SECONDARY = "#1c2333"
    BG_CARD = "#21262d"
    BG_CARD_HOVER = "#292e36"
    BG_INPUT = "#0d1117"

    # Vurgu renkleri
    ACCENT_PRIMARY = "#7c3aed"      # Mor
    ACCENT_SECONDARY = "#a855f7"    # Açık mor
    ACCENT_GRADIENT_START = "#7c3aed"
    ACCENT_GRADIENT_END = "#3b82f6"

    # Durum renkleri
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"
    INFO = "#3b82f6"

    # Metin renkleri
    TEXT_PRIMARY = "#f0f6fc"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#484f58"
    TEXT_ACCENT = "#a855f7"

    # Kenarlık
    BORDER = "#30363d"
    BORDER_HOVER = "#484f58"

    # Sidebar
    SIDEBAR_BG = "#0d1117"
    SIDEBAR_ACTIVE = "#7c3aed"
    SIDEBAR_HOVER = "#1c2333"

    # Progress
    PROGRESS_BG = "#21262d"
    PROGRESS_FILL = "#7c3aed"


class Fonts:
    """Uygulama fontları."""
    TITLE = ("Segoe UI", 24, "bold")
    SUBTITLE = ("Segoe UI", 18, "bold")
    HEADING = ("Segoe UI", 16, "bold")
    BODY = ("Segoe UI", 13)
    BODY_BOLD = ("Segoe UI", 13, "bold")
    SMALL = ("Segoe UI", 11)
    SMALL_BOLD = ("Segoe UI", 11, "bold")
    TINY = ("Segoe UI", 10)
    ICON = ("Segoe UI Emoji", 20)
    ICON_LARGE = ("Segoe UI Emoji", 28)
    MONO = ("Cascadia Code", 12)


# ═══════════════════════════════════════════════════════
# Temel Bileşenler
# ═══════════════════════════════════════════════════════

class GlassCard(ctk.CTkFrame):
    """Cam efektli modern kart bileşeni."""

    def __init__(self, master, title: str = "", icon: str = "",
                 description: str = "", clickable: bool = False,
                 on_click: Optional[Callable] = None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
            **kwargs
        )

        self._on_click = on_click
        self._clickable = clickable

        if clickable:
            self.configure(cursor="hand2")
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<Button-1>", self._on_click_handler)

        if title or icon:
            header = ctk.CTkFrame(self, fg_color="transparent")
            header.pack(fill="x", padx=16, pady=(16, 4))

            if clickable:
                header.bind("<Button-1>", self._on_click_handler)

            if icon:
                icon_label = ctk.CTkLabel(
                    header, text=icon, font=Fonts.ICON_LARGE,
                    text_color=Colors.ACCENT_SECONDARY
                )
                icon_label.pack(side="left", padx=(0, 10))
                if clickable:
                    icon_label.bind("<Button-1>", self._on_click_handler)

            if title:
                title_label = ctk.CTkLabel(
                    header, text=title, font=Fonts.HEADING,
                    text_color=Colors.TEXT_PRIMARY, anchor="w"
                )
                title_label.pack(side="left", fill="x", expand=True)
                if clickable:
                    title_label.bind("<Button-1>", self._on_click_handler)

        if description:
            desc_label = ctk.CTkLabel(
                self, text=description, font=Fonts.SMALL,
                text_color=Colors.TEXT_SECONDARY, anchor="w",
                wraplength=350
            )
            desc_label.pack(fill="x", padx=16, pady=(0, 12))
            if clickable:
                desc_label.bind("<Button-1>", self._on_click_handler)

    def _on_enter(self, event):
        self.configure(
            fg_color=Colors.BG_CARD_HOVER,
            border_color=Colors.ACCENT_PRIMARY
        )

    def _on_leave(self, event):
        self.configure(
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER
        )

    def _on_click_handler(self, event):
        if self._on_click:
            self._on_click()


class ActionCard(ctk.CTkFrame):
    """Ana sayfadaki hızlı eylem kartı."""

    def __init__(self, master, title: str, icon: str, description: str,
                 accent_color: str = Colors.ACCENT_PRIMARY,
                 on_click: Optional[Callable] = None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=Colors.BORDER,
            **kwargs
        )

        self._on_click = on_click
        self._accent = accent_color
        self.configure(cursor="hand2")

        # Tüm widget'lara click binding
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._click)

        # Accent bar (üst kenar renk şeridi)
        accent_bar = ctk.CTkFrame(
            self, fg_color=accent_color, height=3,
            corner_radius=0
        )
        accent_bar.pack(fill="x", padx=20, pady=(12, 0))
        accent_bar.bind("<Button-1>", self._click)

        # İkon
        icon_label = ctk.CTkLabel(
            self, text=icon, font=("Segoe UI Emoji", 36),
            text_color=accent_color
        )
        icon_label.pack(pady=(14, 6))
        icon_label.bind("<Button-1>", self._click)

        # Başlık
        title_label = ctk.CTkLabel(
            self, text=title, font=Fonts.BODY_BOLD,
            text_color=Colors.TEXT_PRIMARY
        )
        title_label.pack(pady=(0, 4))
        title_label.bind("<Button-1>", self._click)

        # Açıklama
        desc_label = ctk.CTkLabel(
            self, text=description, font=Fonts.TINY,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=150
        )
        desc_label.pack(pady=(0, 16))
        desc_label.bind("<Button-1>", self._click)

    def _on_enter(self, event):
        self.configure(
            fg_color=Colors.BG_CARD_HOVER,
            border_color=self._accent
        )

    def _on_leave(self, event):
        self.configure(
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER
        )

    def _click(self, event):
        if self._on_click:
            self._on_click()


class ComponentCheckbox(ctk.CTkFrame):
    """Profil bileşeni seçim checkbox'ı."""

    def __init__(self, master, component_id: str, icon: str, name: str,
                 description: str, size_text: str = "",
                 available: bool = True, requires_admin: bool = False,
                 **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
            height=56,
            **kwargs
        )
        self.pack_propagate(False)

        self.component_id = component_id
        self._available = available
        self.var = ctk.BooleanVar(value=False)

        # Ana içerik
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=8)

        # Sol: checkbox + ikon + isim
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="y")

        self.checkbox = ctk.CTkCheckBox(
            left, text="", variable=self.var,
            width=22, height=22,
            fg_color=Colors.ACCENT_PRIMARY,
            hover_color=Colors.ACCENT_SECONDARY,
            border_color=Colors.BORDER,
            checkmark_color=Colors.TEXT_PRIMARY,
            state="normal" if available else "disabled"
        )
        self.checkbox.pack(side="left", padx=(0, 8))

        icon_label = ctk.CTkLabel(
            left, text=icon, font=("Segoe UI Emoji", 18),
            text_color=Colors.ACCENT_SECONDARY if available else Colors.TEXT_MUTED
        )
        icon_label.pack(side="left", padx=(0, 8))

        # Metin bilgileri
        text_frame = ctk.CTkFrame(left, fg_color="transparent")
        text_frame.pack(side="left")

        name_text = name
        if requires_admin:
            name_text += " 🔒"

        name_label = ctk.CTkLabel(
            text_frame, text=name_text, font=Fonts.BODY_BOLD,
            text_color=Colors.TEXT_PRIMARY if available else Colors.TEXT_MUTED,
            anchor="w"
        )
        name_label.pack(anchor="w")

        if description:
            desc_label = ctk.CTkLabel(
                text_frame, text=description, font=Fonts.TINY,
                text_color=Colors.TEXT_SECONDARY if available else Colors.TEXT_MUTED,
                anchor="w"
            )
            desc_label.pack(anchor="w")

        # Sağ: boyut bilgisi
        if size_text:
            size_label = ctk.CTkLabel(
                content, text=size_text, font=Fonts.SMALL,
                text_color=Colors.TEXT_SECONDARY
            )
            size_label.pack(side="right", padx=(8, 0))

        # Hover efekti
        self.bind("<Enter>", lambda e: self.configure(
            border_color=Colors.ACCENT_PRIMARY if available else Colors.BORDER
        ))
        self.bind("<Leave>", lambda e: self.configure(
            border_color=Colors.BORDER
        ))

    @property
    def is_selected(self) -> bool:
        return self.var.get()

    @is_selected.setter
    def is_selected(self, value: bool):
        if self._available:
            self.var.set(value)


class ProgressCard(ctk.CTkFrame):
    """İlerleme göstergesi kartı."""

    def __init__(self, master, title: str = "İşlem devam ediyor...", **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
            **kwargs
        )

        # Başlık
        self.title_label = ctk.CTkLabel(
            self, text=title, font=Fonts.HEADING,
            text_color=Colors.TEXT_PRIMARY
        )
        self.title_label.pack(padx=20, pady=(20, 8))

        # İlerleme çubuğu
        self.progress = ctk.CTkProgressBar(
            self, width=400, height=8,
            fg_color=Colors.PROGRESS_BG,
            progress_color=Colors.ACCENT_PRIMARY,
            corner_radius=4
        )
        self.progress.pack(padx=20, pady=4)
        self.progress.set(0)

        # Durum metni
        self.status_label = ctk.CTkLabel(
            self, text="Hazırlanıyor...", font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY
        )
        self.status_label.pack(padx=20, pady=(4, 4))

        # Detay metni (hız, süre vb.)
        self.detail_label = ctk.CTkLabel(
            self, text="", font=Fonts.TINY,
            text_color=Colors.TEXT_MUTED
        )
        self.detail_label.pack(padx=20, pady=(0, 16))

    def update_progress(self, value: float, status: str = "",
                         detail: str = ""):
        """İlerleme durumunu güncelle."""
        self.progress.set(min(max(value, 0), 1))
        if status:
            self.status_label.configure(text=status)
        if detail:
            self.detail_label.configure(text=detail)

    def set_complete(self, message: str = "Tamamlandı!"):
        """İşlem tamamlandı durumuna geç."""
        self.progress.set(1)
        self.progress.configure(progress_color=Colors.SUCCESS)
        self.status_label.configure(
            text=message, text_color=Colors.SUCCESS
        )

    def set_error(self, message: str = "Hata oluştu!"):
        """Hata durumuna geç."""
        self.progress.configure(progress_color=Colors.ERROR)
        self.status_label.configure(
            text=message, text_color=Colors.ERROR
        )


class InfoRow(ctk.CTkFrame):
    """Bilgi satırı (etiket: değer)."""

    def __init__(self, master, label: str, value: str,
                 icon: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", height=32, **kwargs)
        self.pack_propagate(False)

        left_text = f"{icon}  {label}" if icon else label

        label_widget = ctk.CTkLabel(
            self, text=left_text, font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY, anchor="w"
        )
        label_widget.pack(side="left")

        self.value_widget = ctk.CTkLabel(
            self, text=value, font=Fonts.SMALL_BOLD,
            text_color=Colors.TEXT_PRIMARY, anchor="e"
        )
        self.value_widget.pack(side="right")

    def set_value(self, value: str):
        self.value_widget.configure(text=value)


class SectionHeader(ctk.CTkFrame):
    """Bölüm başlığı."""

    def __init__(self, master, title: str, subtitle: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        title_label = ctk.CTkLabel(
            self, text=title, font=Fonts.SUBTITLE,
            text_color=Colors.TEXT_PRIMARY, anchor="w"
        )
        title_label.pack(fill="x", anchor="w")

        if subtitle:
            sub_label = ctk.CTkLabel(
                self, text=subtitle, font=Fonts.SMALL,
                text_color=Colors.TEXT_SECONDARY, anchor="w"
            )
            sub_label.pack(fill="x", anchor="w", pady=(2, 0))


class AccentButton(ctk.CTkButton):
    """Vurgulu aksiyon butonu."""

    def __init__(self, master, text: str, icon: str = "",
                 accent: str = Colors.ACCENT_PRIMARY,
                 hover: str = Colors.ACCENT_SECONDARY, **kwargs):
        display_text = f"{icon}  {text}" if icon else text
        super().__init__(
            master,
            text=display_text,
            font=Fonts.BODY_BOLD,
            fg_color=accent,
            hover_color=hover,
            text_color=Colors.TEXT_PRIMARY,
            corner_radius=10,
            height=42,
            **kwargs
        )


class SecondaryButton(ctk.CTkButton):
    """İkincil buton."""

    def __init__(self, master, text: str, icon: str = "", **kwargs):
        display_text = f"{icon}  {text}" if icon else text
        super().__init__(
            master,
            text=display_text,
            font=Fonts.BODY,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            border_width=1,
            border_color=Colors.BORDER,
            corner_radius=10,
            height=42,
            **kwargs
        )


class StatusBadge(ctk.CTkLabel):
    """Durum göstergesi badge."""

    STYLES = {
        "success": (Colors.SUCCESS, "#064e3b"),
        "warning": (Colors.WARNING, "#78350f"),
        "error": (Colors.ERROR, "#7f1d1d"),
        "info": (Colors.INFO, "#1e3a5f"),
    }

    def __init__(self, master, text: str, status: str = "info", **kwargs):
        text_color, bg_color = self.STYLES.get(status, self.STYLES["info"])
        super().__init__(
            master,
            text=f"  {text}  ",
            font=Fonts.TINY,
            text_color=text_color,
            fg_color=bg_color,
            corner_radius=6,
            **kwargs
        )


class DiskUsageBar(ctk.CTkFrame):
    """Disk kullanım çubuğu."""

    def __init__(self, master, used: int, total: int,
                 label: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        from utils.helpers import get_size_display

        if label:
            header = ctk.CTkFrame(self, fg_color="transparent")
            header.pack(fill="x")

            ctk.CTkLabel(
                header, text=label, font=Fonts.SMALL,
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left")

            pct = (used / total * 100) if total > 0 else 0
            ctk.CTkLabel(
                header, text=f"{get_size_display(used)} / {get_size_display(total)} ({pct:.0f}%)",
                font=Fonts.SMALL, text_color=Colors.TEXT_PRIMARY
            ).pack(side="right")

        bar = ctk.CTkProgressBar(
            self, width=300, height=6,
            fg_color=Colors.PROGRESS_BG,
            corner_radius=3
        )
        bar.pack(fill="x", pady=(4, 0))

        ratio = used / total if total > 0 else 0
        bar.set(ratio)

        # Renk ayarla
        if ratio > 0.9:
            bar.configure(progress_color=Colors.ERROR)
        elif ratio > 0.7:
            bar.configure(progress_color=Colors.WARNING)
        else:
            bar.configure(progress_color=Colors.ACCENT_PRIMARY)
