"""
WinProfileMigrator - Ağ Transfer Sayfası
İki bilgisayar arasında doğrudan ağ üzerinden profil aktarma.
"""
import threading
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog

from ui.components import (
    Colors, Fonts, SectionHeader, GlassCard, InfoRow,
    AccentButton, SecondaryButton, ProgressCard, StatusBadge, ComponentCheckbox
)
from core.network_transfer import NetworkTransfer
from core.profile_scanner import ProfileScanner
from core.profile_exporter import ProfileExporter
from utils.helpers import get_size_display, add_recent_operation


class NetworkPage(ctk.CTkScrollableFrame):
    """Ağ transfer sayfası."""

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
        self._network = NetworkTransfer()
        self._scanner = ProfileScanner()
        self._exporter = ProfileExporter()
        self._mode = None  # "sender" veya "receiver"
        self._sending = False
        self._profiles = []
        self._selected_profile = None
        self._checkboxes = []

        self._build_ui()

    def _build_ui(self):
        """UI'ı oluştur."""
        # ── Başlık ──
        SectionHeader(
            self, title="🌐  Ağ Transferi",
            subtitle="İki bilgisayar arasında doğrudan profil paketi aktarın"
        ).pack(fill="x", padx=30, pady=(24, 16))

        # ── IP Bilgisi ──
        ip_info = GlassCard(self, title="Ağ Bilgileri", icon="📡")
        ip_info.pack(fill="x", padx=30, pady=(0, 16))

        local_ip = self._network.get_local_ip()
        InfoRow(ip_info, "Yerel IP Adresi", local_ip, icon="🔗").pack(
            fill="x", padx=16, pady=2)
        InfoRow(ip_info, "Transfer Portu", "52789", icon="🔌").pack(
            fill="x", padx=16, pady=2)
        ctk.CTkFrame(ip_info, fg_color="transparent", height=8).pack()

        # ── Mod Seçimi ──
        mode_header = SectionHeader(
            self, title="Transfer Modu",
            subtitle="Bu bilgisayarın rolünü seçin"
        )
        mode_header.pack(fill="x", padx=30, pady=(0, 12))

        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=30)
        mode_frame.columnconfigure((0, 1), weight=1, uniform="mode")

        # Gönderici kartı
        self._sender_card = GlassCard(
            mode_frame, title="Gönderici", icon="📤",
            description="Bu bilgisayardan profil paketi gönderin",
            clickable=True, on_click=lambda: self._set_mode("sender")
        )
        self._sender_card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        # Alıcı kartı
        self._receiver_card = GlassCard(
            mode_frame, title="Alıcı", icon="📥",
            description="Başka bir bilgisayardan profil paketi alın",
            clickable=True, on_click=lambda: self._set_mode("receiver")
        )
        self._receiver_card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        # ── Gönderici Panel ──
        self._sender_panel = ctk.CTkFrame(self, fg_color="transparent")

        # Gönderim türü
        type_frame = ctk.CTkFrame(self._sender_panel, fg_color="transparent")
        type_frame.pack(fill="x", pady=(0, 12))

        self._send_type_var = ctk.StringVar(value="file")
        
        ctk.CTkRadioButton(
            type_frame, text="Var Olan Dosyayı Gönder (.wpkg)", variable=self._send_type_var,
            value="file", font=Fonts.BODY, command=self._on_send_type_change,
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_SECONDARY
        ).pack(side="left", padx=(0, 16))

        ctk.CTkRadioButton(
            type_frame, text="Mevcut Profili Anında Gönder (Hızlı)", variable=self._send_type_var,
            value="stream", font=Fonts.BODY, command=self._on_send_type_change,
            fg_color=Colors.ACCENT_PRIMARY, hover_color=Colors.ACCENT_SECONDARY
        ).pack(side="left")

        # Dosya seçimi (Dosya modu)
        self._file_card = GlassCard(self._sender_panel, title="Gönderilecek Dosya", icon="📦")
        self._file_card.pack(fill="x", pady=(0, 12))

        file_inner = ctk.CTkFrame(self._file_card, fg_color="transparent")
        file_inner.pack(fill="x", padx=16, pady=(0, 16))

        self._send_file_entry = ctk.CTkEntry(
            file_inner, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=350,
            placeholder_text="Bir .wpkg dosyası seçin..."
        )
        self._send_file_entry.pack(side="left")

        SecondaryButton(
            file_inner, text="Gözat", icon="📂",
            command=self._browse_send_file, width=100
        ).pack(side="left", padx=(12, 0))

        # Hızlı Profil Aktarımı (Stream modu)
        self._stream_card = GlassCard(self._sender_panel, title="Profil Sıkıştır ve Gönder", icon="⚡")

        stream_inner = ctk.CTkFrame(self._stream_card, fg_color="transparent")
        stream_inner.pack(fill="x", padx=16, pady=(16, 16))

        ctk.CTkLabel(
            stream_inner, 
            text="Bu bilgisayardaki profil bileşenlerini seçin. Geçici dosya oluşturulmadan\ndoğrudan sıkıştırılarak karşı bilgisayara aktarılacaktır.",
            font=Fonts.BODY, text_color=Colors.TEXT_SECONDARY, justify="left"
        ).pack(anchor="w", pady=(0, 12))

        # Profil Seçici
        prof_frame = ctk.CTkFrame(stream_inner, fg_color="transparent")
        prof_frame.pack(fill="x", pady=(0, 12))
        
        ctk.CTkLabel(
            prof_frame, text="Profil:", font=Fonts.BODY, text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 8))
        
        self._profile_combo = ctk.CTkComboBox(
            prof_frame, values=["Taranıyor..."], font=Fonts.BODY,
            state="readonly", width=300, command=self._on_profile_selected
        )
        self._profile_combo.pack(side="left")

        # Tümünü Seç Butonları
        sel_frame = ctk.CTkFrame(stream_inner, fg_color="transparent")
        sel_frame.pack(fill="x", pady=(0, 8))
        
        SecondaryButton(
            sel_frame, text="Tümünü Seç", icon="☑️", command=self._select_all, width=120
        ).pack(side="left", padx=(0, 8))
        
        SecondaryButton(
            sel_frame, text="Seçimi Kaldır", icon="⬜", command=self._deselect_all, width=120
        ).pack(side="left")

        self._stream_size_label = ctk.CTkLabel(
            sel_frame, text="Toplam: 0 B", font=Fonts.SMALL_BOLD, text_color=Colors.ACCENT_SECONDARY
        )
        self._stream_size_label.pack(side="right")

        # Bileşenler listesi
        self._stream_components_frame = ctk.CTkFrame(stream_inner, fg_color="transparent")
        self._stream_components_frame.pack(fill="x")
        
        # Keşif ve diğer butonlar...
        self._discover_card = GlassCard(self._sender_panel, title="Alıcı Bilgisayar", icon="🔍")
        self._discover_card.pack(fill="x", pady=(0, 12))

        discover_inner = ctk.CTkFrame(self._discover_card, fg_color="transparent")
        discover_inner.pack(fill="x", padx=16, pady=(0, 12))

        self._discover_btn = AccentButton(
            discover_inner, text="Cihaz Ara", icon="🔍",
            command=self._discover_peers, width=150,
            accent=Colors.SUCCESS, hover="#059669"
        )
        self._discover_btn.pack(side="left")

        self._discover_status = ctk.CTkLabel(
            discover_inner, text="", font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY
        )
        self._discover_status.pack(side="left", padx=(12, 0))

        # Bulunan cihazlar
        self._peers_frame = ctk.CTkFrame(self._discover_card, fg_color="transparent")
        self._peers_frame.pack(fill="x", padx=16, pady=(0, 12))

        # Manuel IP girişi
        manual_frame = ctk.CTkFrame(self._discover_card, fg_color="transparent")
        manual_frame.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkLabel(
            manual_frame, text="veya IP adresi girin:",
            font=Fonts.SMALL, text_color=Colors.TEXT_MUTED
        ).pack(side="left")

        self._manual_ip = ctk.CTkEntry(
            manual_frame, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=180,
            placeholder_text="192.168.1.100"
        )
        self._manual_ip.pack(side="left", padx=(8, 0))

        # Gönder butonu
        send_action = ctk.CTkFrame(self._sender_panel, fg_color="transparent")
        send_action.pack(fill="x", pady=(0, 12))

        self._send_btn = AccentButton(
            send_action, text="Göndermeyi Başlat", icon="🚀",
            command=self._start_send, width=220
        )
        self._send_btn.pack(side="right")
        
        self._cancel_send_btn = SecondaryButton(
            send_action, text="İptal", icon="⏹️",
            command=self._cancel_send, width=120
        )

        # ── Alıcı Panel ──
        self._receiver_panel = ctk.CTkFrame(self, fg_color="transparent")

        # Kayıt yeri
        save_card = GlassCard(self._receiver_panel, title="Kayıt Konumu", icon="💾")
        save_card.pack(fill="x", pady=(0, 12))

        save_inner = ctk.CTkFrame(save_card, fg_color="transparent")
        save_inner.pack(fill="x", padx=16, pady=(0, 16))

        self._save_dir_entry = ctk.CTkEntry(
            save_inner, font=Fonts.BODY,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY, width=350,
        )
        self._save_dir_entry.pack(side="left")
        self._save_dir_entry.insert(0, str(Path.home() / "Desktop"))

        SecondaryButton(
            save_inner, text="Gözat", icon="📂",
            command=self._browse_save_dir, width=100
        ).pack(side="left", padx=(12, 0))

        # Dinleme durumu
        self._listen_card = GlassCard(
            self._receiver_panel, title="Bekleme Durumu", icon="📡"
        )
        self._listen_card.pack(fill="x", pady=(0, 12))

        self._listen_status = ctk.CTkLabel(
            self._listen_card, text="⏸️  Bekleme başlatılmadı",
            font=Fonts.BODY, text_color=Colors.TEXT_SECONDARY
        )
        self._listen_status.pack(padx=16, pady=(0, 12))

        listen_action = ctk.CTkFrame(self._receiver_panel, fg_color="transparent")
        listen_action.pack(fill="x", pady=(0, 12))

        self._listen_btn = AccentButton(
            listen_action, text="Beklemeyi Başlat", icon="📡",
            accent=Colors.INFO, hover="#2563eb",
            command=self._start_receiver, width=220
        )
        self._listen_btn.pack(side="right")

        self._stop_listen_btn = SecondaryButton(
            listen_action, text="Durdur", icon="⏹️",
            command=self._stop_receiver, width=120
        )

        # ── Ortak İlerleme Kartı ──
        self._progress_card = ProgressCard(self, title="Transfer İlerlemesi")

        # Alt boşluk
        ctk.CTkFrame(self, fg_color="transparent", height=20).pack()

    def _set_mode(self, mode: str):
        """Transfer modunu ayarla."""
        self._mode = mode

        # Aktif kartı vurgula
        if mode == "sender":
            self._sender_card.configure(border_color=Colors.ACCENT_PRIMARY)
            self._receiver_card.configure(border_color=Colors.BORDER)
            self._receiver_panel.pack_forget()
            self._sender_panel.pack(fill="x", padx=30, pady=(16, 0))
        else:
            self._sender_card.configure(border_color=Colors.BORDER)
            self._receiver_card.configure(border_color=Colors.INFO)
            self._sender_panel.pack_forget()
            self._receiver_panel.pack(fill="x", padx=30, pady=(16, 0))

    def _on_send_type_change(self):
        """Gönderim türü değiştiğinde UI'ı güncelle."""
        if self._send_type_var.get() == "file":
            self._stream_card.pack_forget()
            self._file_card.pack(fill="x", pady=(0, 12), before=self._discover_card)
        else:
            self._file_card.pack_forget()
            self._stream_card.pack(fill="x", pady=(0, 12), before=self._discover_card)
            if not self._profiles:
                self._scan_profiles()

    def _scan_profiles(self):
        self._profile_combo.set("Taranıyor...")
        self._profile_combo.configure(state="disabled")
        
        def scan_task():
            profiles = self._scanner.scan_profiles()
            self.after(0, lambda: self._update_profiles_list(profiles))
            
        threading.Thread(target=scan_task, daemon=True).start()

    def _update_profiles_list(self, profiles):
        self._profiles = profiles
        if not profiles:
            self._profile_combo.configure(values=["Profil bulunamadı"], state="disabled")
            self._profile_combo.set("Profil bulunamadı")
            return

        names = [f"{p.username} ({get_size_display(p.total_size)})" for p in profiles]
        self._profile_combo.configure(values=names, state="readonly")

        # Mevcut kullanıcıyı bul
        import os
        current_user = os.environ.get("USERNAME", "")
        idx = 0
        for i, p in enumerate(profiles):
            if p.username.lower() == current_user.lower():
                idx = i
                break

        self._profile_combo.set(names[idx])
        self._on_profile_selected(names[idx])

    def _on_profile_selected(self, selection):
        idx = self._profile_combo._values.index(selection)
        self._selected_profile = self._profiles[idx]
        self._build_components_ui()
        
    def _build_components_ui(self):
        for widget in self._stream_components_frame.winfo_children():
            widget.destroy()
            
        self._checkboxes.clear()
        
        if not self._selected_profile:
            return
            
        # Kategorilere göre grupla
        categories = {
            "files": ("📁 Dosya Klasörleri", []),
            "settings": ("⚙️ Uygulama Ayarları", []),
            "system": ("🔧 Sistem Ayarları", []),
        }

        for comp in self._selected_profile.components:
            cat = comp.category if comp.category in categories else "system"
            categories[cat][1].append(comp)

        for cat_id, (cat_title, components) in categories.items():
            if not components:
                continue

            cat_label = ctk.CTkLabel(
                self._stream_components_frame,
                text=cat_title,
                font=Fonts.BODY_BOLD,
                text_color=Colors.TEXT_ACCENT,
                anchor="w"
            )
            cat_label.pack(fill="x", pady=(12, 4))

            for comp in components:
                cb = ComponentCheckbox(
                    self._stream_components_frame,
                    component_id=comp.id,
                    icon=comp.icon,
                    name=comp.name,
                    description=comp.description,
                    size_text="Hesaplanıyor..." if comp.path and comp.available else "",
                    available=comp.available,
                    requires_admin=comp.requires_admin
                )
                cb.pack(fill="x", pady=2)
                cb.var.trace_add("write", lambda *args: self._update_size_label())
                self._checkboxes.append(cb)
                    
        self._update_size_label()
        self._calculate_sizes_async(self._selected_profile)

    def _calculate_sizes_async(self, profile):
        """Bileşen boyutlarını arka planda hesapla ve UI'ı güncelle."""
        from utils.helpers import get_dir_size

        def calculate():
            for comp in profile.components:
                if comp.path and comp.available and not comp.requires_admin:
                    try:
                        size = get_dir_size(comp.path)
                        comp.size = size
                        self.after(0, lambda c=comp: self._update_checkbox_size(c))
                    except (PermissionError, OSError):
                        comp.size = -1
                        self.after(0, lambda c=comp: self._update_checkbox_size(c))
            self.after(0, self._update_size_label)

        threading.Thread(target=calculate, daemon=True).start()

    def _update_checkbox_size(self, comp):
        """Tek bir checkbox'ın boyut bilgisini güncelle."""
        for cb in self._checkboxes:
            if cb.component_id == comp.id:
                size_text = get_size_display(comp.size) if comp.size > 0 else ""
                for widget in cb.winfo_children():
                    for sub in widget.winfo_children():
                        if hasattr(sub, 'cget'):
                            try:
                                current = sub.cget("text")
                                if current == "Hesaplanıyor..." or current.endswith(("B", "KB", "MB", "GB", "TB")):
                                    sub.configure(text=size_text)
                                    return
                            except Exception:
                                pass

    def _select_all(self):
        for cb in self._checkboxes:
            cb.is_selected = True
        self._update_size_label()
        
    def _deselect_all(self):
        for cb in self._checkboxes:
            cb.is_selected = False
        self._update_size_label()

    def _update_size_label(self):
        total = 0
        for cb in self._checkboxes:
            if cb.var.get():
                for comp in self._selected_profile.components:
                    if comp.id == cb.component_id and hasattr(comp, 'size') and comp.size > 0:
                        total += comp.size
                        break
        self._stream_size_label.configure(text=f"Toplam: {get_size_display(total)}")

    def _browse_send_file(self):
        """Gönderilecek dosyayı seç."""
        path = filedialog.askopenfilename(
            title="Profil Paketi Seçin",
            filetypes=[
                ("WinProfile Paketi", "*.wpkg"),
                ("ZIP Dosyası", "*.zip"),
                ("Tüm Dosyalar", "*.*"),
            ]
        )
        if path:
            self._send_file_entry.delete(0, "end")
            self._send_file_entry.insert(0, path)

    def _browse_save_dir(self):
        """Kayıt dizinini seç."""
        path = filedialog.askdirectory(title="Kayıt Konumu Seçin")
        if path:
            self._save_dir_entry.delete(0, "end")
            self._save_dir_entry.insert(0, path)

    def _discover_peers(self):
        """Ağdaki cihazları keşfet."""
        self._discover_status.configure(text="🔍 Aranıyor...")
        self._discover_btn.configure(state="disabled")

        # Mevcut peer'ları temizle
        for widget in self._peers_frame.winfo_children():
            widget.destroy()

        def discover():
            peers = self._network.discover_peers(timeout=5)
            self.after(0, lambda: self._update_peers(peers))

        threading.Thread(target=discover, daemon=True).start()

    def _update_peers(self, peers):
        """Bulunan cihazları göster."""
        self._peers = peers
        self._discover_btn.configure(state="normal")

        if not peers:
            self._discover_status.configure(
                text="❌ Hiç cihaz bulunamadı. Karşı tarafta uygulamayı başlatın."
            )
            return

        self._discover_status.configure(
            text=f"✅ {len(peers)} cihaz bulundu"
        )

        for peer in peers:
            peer_frame = ctk.CTkFrame(
                self._peers_frame,
                fg_color=Colors.BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=Colors.BORDER,
                height=44, cursor="hand2"
            )
            peer_frame.pack(fill="x", pady=2)
            peer_frame.pack_propagate(False)

            inner = ctk.CTkFrame(peer_frame, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=12, pady=6)

            ctk.CTkLabel(
                inner, text=f"💻  {peer['hostname']}",
                font=Fonts.BODY_BOLD, text_color=Colors.TEXT_PRIMARY
            ).pack(side="left")

            ctk.CTkLabel(
                inner, text=peer["ip"],
                font=Fonts.SMALL, text_color=Colors.TEXT_SECONDARY
            ).pack(side="right")

            # Tıklanınca IP'yi seç
            peer_frame.bind(
                "<Button-1>",
                lambda e, ip=peer["ip"]: self._select_peer(ip)
            )

            # Hover
            peer_frame.bind("<Enter>", lambda e, f=peer_frame:
                f.configure(border_color=Colors.ACCENT_PRIMARY))
            peer_frame.bind("<Leave>", lambda e, f=peer_frame:
                f.configure(border_color=Colors.BORDER))

    def _select_peer(self, ip: str):
        """Bir peer'ı seç."""
        self._manual_ip.delete(0, "end")
        self._manual_ip.insert(0, ip)
        
    def _get_target_ip(self):
        return self._manual_ip.get().strip()

    def _show_message(self, message, type):
        # A simple placeholder for UI alerts
        print(f"[{type.upper()}] {message}")

    def _start_send(self):
        """Gönderme işlemini başlat."""
        if self._sending:
            return

        is_stream = self._send_type_var.get() == "stream"

        if not is_stream:
            file_path = Path(self._send_file_entry.get())
            if not file_path.exists() or not file_path.is_file():
                self._show_message("Lütfen geçerli bir dosya seçin!", "warning")
                return

        target_ip = self._get_target_ip()
        if not target_ip:
            self._show_message("Lütfen alıcı cihaz seçin veya IP girin!", "warning")
            return

        self._sending = True
        self._send_btn.configure(state="disabled")
        self._progress_card.pack(fill="x", pady=(12, 0))
        self._cancel_send_btn.pack(side="left")

        def send_thread():
            if is_stream:
                if not self._selected_profile:
                    self.after(0, lambda: self._show_message("Lütfen bir profil seçin!", "warning"))
                    self.after(0, lambda: self._send_complete(False))
                    return
                    
                selected_ids = [cb.component_id for cb in self._checkboxes if cb.var.get()]
                if not selected_ids:
                    self.after(0, lambda: self._show_message("Lütfen en az bir bileşen seçin!", "warning"))
                    self.after(0, lambda: self._send_complete(False))
                    return

                self.after(0, lambda: self._progress_card.update_progress(
                    0, "🔍 Aktarım hazırlanıyor...", "Hazırlanıyor"
                ))
                # Toplam boyutu hesapla
                total_bytes = 0
                for cb in self._checkboxes:
                    if cb.var.get():
                        for comp in self._selected_profile.components:
                            if comp.id == cb.component_id and hasattr(comp, 'size') and comp.size > 0:
                                total_bytes += comp.size
                                break
                                
                def stream_progress_cb(sent, total, speed):
                    pct = sent / total if total > 0 else 0
                    msg = f"⚡ Gönderiliyor: {get_size_display(sent)} / {get_size_display(total)} — Hız: {speed:.1f} MB/s"
                    self.after(0, lambda: self._progress_card.update_progress(pct, msg, f"{int(pct*100)}%"))
                
                # Stream bağlantısı aç
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"WinProfile_{self._selected_profile.username}_{timestamp}_Stream.wpkg"
                
                sock, sock_writer = self._network.open_stream_connection(
                    target_ip, file_name, total_size=total_bytes, progress_cb=stream_progress_cb
                )
                if not sock or not sock_writer:
                    self.after(0, lambda: self._send_complete(False))
                    return
                    
                def progress_cb(current, total, message):
                    # Alt bilgi olarak tut, stream_progress_cb zaten ana progress barı güncelliyor
                    pass

                success = self._exporter.export_profile_stream(
                    self._selected_profile, selected_ids, sock_writer, progress_callback=progress_cb
                )
                
                # Bağlantıyı kapat
                try:
                    import socket
                    sock.settimeout(30)
                    response = sock.recv(2)
                    sock.close()
                    if success and response == b"OK":
                        success = True
                    else:
                        success = False
                except Exception:
                    success = False
                    
                self.after(0, lambda: self._send_complete(success))
                
            else:
                def progress_cb(sent, total, speed):
                    pct = sent / total if total > 0 else 0
                    msg = f"Gönderiliyor: {get_size_display(sent)} / {get_size_display(total)} — Hız: {speed:.1f} MB/s"
                    self.after(0, lambda: self._progress_card.update_progress(pct, msg, f"{int(pct*100)}%"))

                self.after(0, lambda: self._progress_card.update_progress(
                    0, "Bağlanıyor...", "Bekleniyor"
                ))
                
                success = self._network.send_file(file_path, target_ip, progress_cb)
                self.after(0, lambda: self._send_complete(success))

        threading.Thread(target=send_thread, daemon=True).start()

    def _send_complete(self, success: bool):
        """Gönderim tamamlandı."""
        self._sending = False
        self._send_btn.configure(state="normal")
        self._cancel_send_btn.pack_forget()
        if success:
            self._progress_card.set_complete("✅ Dosya başarıyla gönderildi!")
            add_recent_operation(self._settings, {
                "type": "network_send",
                "description": f"Ağ üzerinden gönderildi: {self._manual_ip.get()}"
            })
        else:
            self._progress_card.set_error("❌ Gönderme başarısız oldu!")

    def _start_receiver(self):
        """Alıcıyı başlat."""
        save_dir = Path(self._save_dir_entry.get().strip())

        # Keşif yanıtlayıcısını başlat
        self._network.start_discovery_responder()

        def progress_cb(received, total, speed):
            pct = received / total if total > 0 else 0
            self.after(0, lambda: self._progress_card.update_progress(
                pct,
                f"Alınıyor... {get_size_display(received)} / {get_size_display(total)}",
                f"Hız: {speed:.1f} MB/s"
            ))

        def complete_cb(file_path, success):
            self.after(0, lambda: self._receive_complete(file_path, success))

        self._network.start_receiver(save_dir, progress_cb, complete_cb)

        self._listen_status.configure(
            text="🟢  Bağlantı bekleniyor...",
            text_color=Colors.SUCCESS
        )
        self._listen_btn.configure(state="disabled")
        self._stop_listen_btn.pack(side="left")

    def _stop_receiver(self):
        """Alıcıyı durdur."""
        self._network.stop()
        self._listen_status.configure(
            text="⏸️  Durduruldu",
            text_color=Colors.TEXT_SECONDARY
        )
        self._listen_btn.configure(state="normal")
        self._stop_listen_btn.pack_forget()

    def _cancel_send(self):
        """Gönderimi iptal et."""
        if self._send_type_var.get() == "stream":
            self._exporter.cancel()
        self._network.stop()
        self._progress_card.set_error("İptal edildi")
        self._sending = False
        self._send_btn.configure(state="normal")
        self._cancel_send_btn.pack_forget()

    def _receive_complete(self, file_path, success):
        """Alma tamamlandı."""
        self._progress_card.pack(fill="x", padx=30, pady=(12, 0))
        if success:
            self._progress_card.set_complete(
                f"✅ Dosya alındı: {file_path.name}"
            )
            add_recent_operation(self._settings, {
                "type": "network_receive",
                "description": f"Ağ üzerinden alındı: {file_path.name}"
            })
        else:
            self._progress_card.set_error("❌ Alma başarısız oldu!")

    def destroy(self):
        """Temizlik."""
        self._network.stop()
        super().destroy()
