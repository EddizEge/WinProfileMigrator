"""
WinProfileMigrator - Program Tarayıcı ve Yükleyici
Kurulu programları tarar, listeler ve winget ile sessiz kurulum yapar.
"""
import json
import logging
import subprocess
import re
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

logger = logging.getLogger("WinProfileMigrator.programs")


@dataclass
class InstalledProgram:
    """Kurulu program bilgisi."""
    name: str
    id: str  # winget ID
    version: str = ""
    publisher: str = ""
    source: str = ""  # winget, registry
    install_location: str = ""
    can_auto_install: bool = False  # winget ile kurulabilir mi
    selected: bool = True
    status: str = "pending"  # pending, installing, installed, failed, skipped
    error_message: str = ""


class ProgramScanner:
    """Kurulu programları tarar."""

    def __init__(self):
        self.programs: List[InstalledProgram] = []
        self._winget_available = None

    def is_winget_available(self) -> bool:
        """winget kurulu mu kontrol et."""
        if self._winget_available is not None:
            return self._winget_available
        try:
            result = subprocess.run(
                ["winget", "--version"],
                capture_output=True, text=True, timeout=10
            )
            self._winget_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._winget_available = False
        return self._winget_available

    def scan_programs(self, progress_callback: Optional[Callable] = None) -> List[InstalledProgram]:
        """Kurulu programları tara."""
        self.programs = []

        if progress_callback:
            progress_callback("🔍 Kurulu programlar taranıyor (winget)...")

        if self.is_winget_available():
            self._scan_winget(progress_callback)
        else:
            if progress_callback:
                progress_callback("⚠️ winget bulunamadı, registry'den taranıyor...")
            self._scan_registry(progress_callback)

        # Alfabetik sırala
        self.programs.sort(key=lambda p: p.name.lower())

        if progress_callback:
            progress_callback(f"✅ {len(self.programs)} program bulundu")

        return self.programs

    def _scan_winget(self, progress_callback: Optional[Callable] = None):
        """winget ile kurulu programları tara."""
        try:
            result = subprocess.run(
                ["winget", "list", "--accept-source-agreements", "--disable-interactivity"],
                capture_output=True, text=True, timeout=120,
                encoding="utf-8", errors="replace"
            )

            if result.returncode != 0:
                logger.warning("winget list başarısız: %s", result.stderr)
                self._scan_registry(progress_callback)
                return

            lines = result.stdout.strip().split("\n")

            # Header satırını bul (Name, Id, Version içeren)
            header_idx = -1
            for i, line in enumerate(lines):
                if "Id" in line and ("Name" in line or "Ad" in line):
                    header_idx = i
                    break

            if header_idx == -1:
                logger.warning("winget çıktısı ayrıştırılamadı")
                self._scan_registry(progress_callback)
                return

            # Sütun pozisyonlarını header'daki boşluklardan bul
            header = lines[header_idx]

            # Separator satırını atla (----)
            data_start = header_idx + 1
            if data_start < len(lines) and lines[data_start].startswith("-"):
                data_start += 1

            # Sütun pozisyonlarını belirle
            id_pos = header.find("Id")
            ver_pos = header.find("Versi")  # Version veya Sürüm
            if ver_pos == -1:
                ver_pos = header.find("Version")
            if ver_pos == -1:
                ver_pos = header.find("Sürüm")
            source_pos = header.find("Source")
            if source_pos == -1:
                source_pos = header.find("Kaynak")

            # Filtrelenecek gereksiz paketler
            skip_patterns = [
                "microsoft.ui.", "microsoft.net.", "microsoft.vclibs",
                "microsoft.services.", "microsoft.directx",
                "microsoft.windows.", "microsoft.webp",
                "microsoft.heif", "microsoft.hevc",
                "microsoft.raw", "microsoft.vp9",
                "microsoft.av1", "microsoft.mpeg2",
                "{", "kb", "update for",
            ]

            for line in lines[data_start:]:
                line = line.strip()
                if not line or len(line) < 10:
                    continue

                try:
                    name = line[:id_pos].strip() if id_pos > 0 else line[:40].strip()
                    prog_id = ""
                    version = ""
                    source = ""

                    if id_pos > 0:
                        if ver_pos > id_pos:
                            prog_id = line[id_pos:ver_pos].strip()
                        else:
                            prog_id = line[id_pos:].strip().split()[0] if line[id_pos:].strip() else ""

                    if ver_pos > 0:
                        if source_pos > ver_pos:
                            version = line[ver_pos:source_pos].strip()
                        else:
                            version = line[ver_pos:].strip().split()[0] if line[ver_pos:].strip() else ""

                    if source_pos > 0:
                        source = line[source_pos:].strip()

                    # Boş veya çok kısa isimleri atla
                    if not name or len(name) < 2:
                        continue

                    # Gereksiz paketleri filtrele
                    name_lower = name.lower()
                    id_lower = prog_id.lower()
                    if any(skip in id_lower or skip in name_lower for skip in skip_patterns):
                        continue

                    # winget source varsa otomatik kurulabilir
                    can_install = bool(source and source.lower() in ("winget", "msstore"))

                    program = InstalledProgram(
                        name=name,
                        id=prog_id,
                        version=version,
                        source=source,
                        can_auto_install=can_install,
                    )
                    self.programs.append(program)

                except Exception as e:
                    logger.debug("Program satırı ayrıştırılamadı: %s - %s", line, e)

        except subprocess.TimeoutExpired:
            logger.error("winget list zaman aşımı")
            self._scan_registry(progress_callback)
        except Exception as e:
            logger.error("winget tarama hatası: %s", e)
            self._scan_registry(progress_callback)

    def _scan_registry(self, progress_callback: Optional[Callable] = None):
        """Registry'den kurulu programları tara."""
        import winreg

        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        seen_names = set()

        for root, path in reg_paths:
            try:
                with winreg.OpenKey(root, path) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                except OSError:
                                    i += 1
                                    continue

                                if not name or name in seen_names:
                                    i += 1
                                    continue

                                # Sistem güncellemelerini atla
                                name_lower = name.lower()
                                if any(x in name_lower for x in ["update for", "hotfix", "kb", "security update"]):
                                    i += 1
                                    continue

                                seen_names.add(name)

                                version = ""
                                publisher = ""
                                install_loc = ""

                                try:
                                    version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                                except OSError:
                                    pass
                                try:
                                    publisher, _ = winreg.QueryValueEx(subkey, "Publisher")
                                except OSError:
                                    pass
                                try:
                                    install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                except OSError:
                                    pass

                                program = InstalledProgram(
                                    name=name,
                                    id=subkey_name,
                                    version=version or "",
                                    publisher=publisher or "",
                                    install_location=install_loc or "",
                                    source="registry",
                                    can_auto_install=False,
                                )
                                self.programs.append(program)

                            i += 1
                        except OSError:
                            break
            except OSError:
                continue

    def export_program_list(self, programs: List[InstalledProgram],
                             output_path: Path) -> Path:
        """Program listesini JSON olarak dışa aktar."""
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / "installed_programs.json"

        data = {
            "version": "1.0",
            "total_count": len(programs),
            "auto_installable": sum(1 for p in programs if p.can_auto_install),
            "programs": [
                {
                    "name": p.name,
                    "id": p.id,
                    "version": p.version,
                    "publisher": p.publisher,
                    "source": p.source,
                    "can_auto_install": p.can_auto_install,
                }
                for p in programs
            ]
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("Program listesi kaydedildi: %s (%d program)", file_path, len(programs))
        return file_path

    def load_program_list(self, file_path: Path) -> List[InstalledProgram]:
        """JSON'dan program listesi yükle."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            programs = []
            for p in data.get("programs", []):
                programs.append(InstalledProgram(
                    name=p["name"],
                    id=p.get("id", ""),
                    version=p.get("version", ""),
                    publisher=p.get("publisher", ""),
                    source=p.get("source", ""),
                    can_auto_install=p.get("can_auto_install", False),
                ))
            return programs
        except Exception as e:
            logger.error("Program listesi yüklenemedi: %s", e)
            return []


class ProgramInstaller:
    """Programları winget ile sessiz kurulum yapar."""

    def __init__(self):
        self._cancelled = False
        self._results: List[InstalledProgram] = []

    def cancel(self):
        self._cancelled = True

    def install_programs(self, programs: List[InstalledProgram],
                          progress_callback: Optional[Callable] = None) -> List[InstalledProgram]:
        """
        Seçili programları winget ile sessiz kur.

        Args:
            programs: Kurulacak programlar
            progress_callback: callback(current, total, program_name, status)
        """
        self._cancelled = False
        self._results = []

        installable = [p for p in programs if p.selected and p.can_auto_install]
        skipped = [p for p in programs if p.selected and not p.can_auto_install]

        # Kurulamayan programları "skipped" olarak işaretle
        for p in skipped:
            p.status = "skipped"
            p.error_message = "winget ID bulunamadı, manuel kurulum gerekli"
            self._results.append(p)

        total = len(installable)

        for i, program in enumerate(installable):
            if self._cancelled:
                program.status = "skipped"
                program.error_message = "İptal edildi"
                self._results.append(program)
                continue

            if progress_callback:
                progress_callback(i + 1, total, program.name, "installing")

            program.status = "installing"
            success = self._install_single(program)

            if success:
                program.status = "installed"
                logger.info("Program kuruldu: %s", program.name)
            else:
                program.status = "failed"
                logger.warning("Program kurulamadı: %s - %s",
                               program.name, program.error_message)

            self._results.append(program)

            if progress_callback:
                progress_callback(i + 1, total, program.name, program.status)

        return self._results

    def _install_single(self, program: InstalledProgram) -> bool:
        """Tek bir programı winget ile kur."""
        try:
            cmd = [
                "winget", "install",
                "--id", program.id,
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--disable-interactivity",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=600,  # 10 dakika timeout
                encoding="utf-8", errors="replace"
            )

            if result.returncode == 0:
                return True

            # Zaten kuruluysa başarılı say
            output = (result.stdout + result.stderr).lower()
            if "already installed" in output or "zaten yüklü" in output or "no applicable" in output:
                program.status = "installed"
                program.error_message = "Zaten kurulu"
                return True

            program.error_message = result.stderr.strip()[:200] if result.stderr else "Bilinmeyen hata"
            return False

        except subprocess.TimeoutExpired:
            program.error_message = "Kurulum zaman aşımına uğradı (10 dk)"
            return False
        except Exception as e:
            program.error_message = str(e)[:200]
            return False

    @property
    def results(self) -> List[InstalledProgram]:
        return self._results

    def get_summary(self) -> Dict:
        """Kurulum özeti."""
        installed = sum(1 for p in self._results if p.status == "installed")
        failed = sum(1 for p in self._results if p.status == "failed")
        skipped = sum(1 for p in self._results if p.status == "skipped")
        return {
            "total": len(self._results),
            "installed": installed,
            "failed": failed,
            "skipped": skipped,
        }
