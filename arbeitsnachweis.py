import calendar
import datetime
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import holidays
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ── Pfadverwaltung (PyInstaller-kompatibel) ────────────────────────────────

def _get_base_dir():
    """Gibt das Verzeichnis der Exe (gepackt) bzw. des Skripts zurück."""
    if getattr(sys, 'frozen', False):          # PyInstaller-Paket
        return os.path.dirname(sys.executable)
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()

# Konfigurationsdatei liegt immer sicher im Home-Verzeichnis des Nutzers
_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".arbeitsnachweis_config.json")

def _lade_daten_pfad():
    """
    Liest den gespeicherten Datenpfad aus der Konfigurationsdatei.
    Fallback-Reihenfolge:
      1. Gespeicherter Pfad aus ~/.arbeitsnachweis_config.json
      2. Verzeichnis neben der Exe / dem Skript (wenn beschreibbar)
      3. ~/Dokumente/Arbeitsnachweis  (immer beschreibbar)
    """
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            p = cfg.get("data_dir", "")
            if p and os.path.isdir(p):
                return p
    except Exception:
        pass

    base = _get_base_dir()
    try:
        test = os.path.join(base, ".schreibtest")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        return base
    except Exception:
        pass

    fallback = os.path.join(os.path.expanduser("~"), "Dokumente", "Arbeitsnachweis")
    os.makedirs(fallback, exist_ok=True)
    return fallback

def _speichere_daten_pfad(pfad):
    """Schreibt den gewählten Datenpfad in ~/.arbeitsnachweis_config.json."""
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"data_dir": pfad}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Konfiguration konnte nicht gespeichert werden: {e}")

DATA_DIR = _lade_daten_pfad()
DATA_FILE = os.path.join(DATA_DIR, "arbeitsnachweis_daten.json")
MITARBEITER_FILE = os.path.join(DATA_DIR, "mitarbeiter_daten.json")

class TimeTrackingLogic:
    """Klasse für Berechnungen, Datenhaltung und PDF-Export."""
    
    @staticmethod
    def lade_mitarbeiter():
        if not os.path.exists(MITARBEITER_FILE):
            # Erstelle eine Standard-Datei, wenn sie fehlt
            standard = {"Mauricio Dussin": {"wochenstunden": "30", "arbeitstage": "6"}}
            with open(MITARBEITER_FILE, "w", encoding="utf-8") as f:
                json.dump(standard, f, ensure_ascii=False, indent=4)
            return standard
        
        # Ansonsten laden
        try:
            with open(MITARBEITER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"Mauricio Dussin": {"wochenstunden": "30", "arbeitstage": "6"}}

    @staticmethod
    def speichere_mitarbeiter(daten):
        try:
            with open(MITARBEITER_FILE, "w", encoding="utf-8") as f:
                json.dump(daten, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Fehler beim Speichern der Mitarbeiter: {e}")

    @staticmethod
    def parse_stunden(von_str, bis_str):
        if not von_str or not bis_str:
            return 0.0
        try:
            h1, m1 = map(int, von_str.split(":"))
            h2, m2 = map(int, bis_str.split(":"))
            t1 = h1 + m1 / 60.0
            t2 = h2 + m2 / 60.0
            if t2 < t1:  # Schicht über Mitternacht hinaus
                t2 += 24.0
            return t2 - t1
        except ValueError:
            return 0.0

    @staticmethod
    def format_komma(wert):
        if wert == 0:
            return ""
        return f"{wert:.2f}".replace(".", ",")

    @staticmethod
    def generiere_pdf(filepath, name, monat, jahr, tage_daten, uestd_farbe="#000000"):
        doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, alignment=1)

        story.append(Paragraph("<b>Arbeitsnachweis Tonabteilung</b>", title_style))
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>Name:</b> {name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Monat/Jahr:</b> {monat}/{jahr}", styles['Normal']))
        story.append(Spacer(1, 15))

        table_data = [["Tag", "Vormittag", "Nachmittag", "Std.ges", "D.Plan", "A", "H", "Ü.Std", "Bemerkung"]]

        summe_ges = 0.0
        summe_plan = 0.0
        summe_ueber = 0.0

        for tag_str in sorted(tage_daten.keys(), key=lambda x: int(x)):
            d = tage_daten[tag_str]
            
            v_std = TimeTrackingLogic.parse_stunden(d.get("v_von", ""), d.get("v_bis", ""))
            n_std = TimeTrackingLogic.parse_stunden(d.get("n_von", ""), d.get("n_bis", ""))
            g = v_std + n_std
            
            try:
                p = float(d.get("d_plan", "0,00").replace(",", "."))
            except ValueError:
                p = 0.0
                
            u = max(0.0, g - p) if g > p else 0.0

            summe_ges += g
            summe_plan += p
            summe_ueber += u

            v_text = f"{d.get('v_von','')}-{d.get('v_bis','')}" if d.get('v_von','') else ""
            n_text = f"{d.get('n_von','')}-{d.get('n_bis','')}" if d.get('n_von','') else ""

            table_data.append([
                tag_str, v_text, n_text,
                TimeTrackingLogic.format_komma(g),
                TimeTrackingLogic.format_komma(p),
                d.get("a", ""), d.get("h", ""),
                TimeTrackingLogic.format_komma(u),
                d.get("bemerkung", "")
            ])

        table_data.append([
            "Summe", "", "",
            TimeTrackingLogic.format_komma(summe_ges),
            TimeTrackingLogic.format_komma(summe_plan),
            "", "",
            TimeTrackingLogic.format_komma(summe_ueber),
            ""
        ])

        t = Table(table_data, colWidths=[45, 85, 85, 50, 50, 30, 30, 45, 130])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.whitesmoke),
            # Ü.Std-Spalte (Index 7): gewählte Farbe für alle Daten- und Summenzeilen
            ('TEXTCOLOR', (7, 1), (7, -1), colors.HexColor(uestd_farbe)),
        ]))
        story.append(t)
        story.append(Spacer(1, 30))

        sig_data = [["_______________________", "_______________________", "_______________________"],
                    ["aufgestellt", "für die Richtigkeit", "geprüft"]]
        sig_table = Table(sig_data, colWidths=[180, 180, 180])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,1), (-1,1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,1), 10),
        ]))
        story.append(sig_table)

        doc.build(story)


class TimeTrackingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Arbeitsnachweis Tonabteilung")
        self.geometry("1250x900")
        
        # Scrollrad-Aktion in ttk.Comboboxen global deaktivieren (Verhindert versehentliches Ändern)
        self.unbind_class("TCombobox", "<MouseWheel>")
        self.unbind_class("TCombobox", "<Button-4>")
        self.unbind_class("TCombobox", "<Button-5>")

        # Variable, die uns hilft zu erkennen, ob wir die UI manuell bedienen oder gerade Ladevorgänge laufen
        self._is_loading = False

        # Datum-Variablen
        self.jahr_var = tk.StringVar(value=str(datetime.datetime.now().year))
        self.monat_var = tk.StringVar(value=f"{datetime.datetime.now().month:02d}")
        
        # Mitarbeiter-Datenbank laden
        self.mitarbeiter_daten = TimeTrackingLogic.lade_mitarbeiter()
        self.mitarbeiter_optionen = list(self.mitarbeiter_daten.keys())
        
        # Standard-Profil festlegen
        if "Mauricio Dussin" in self.mitarbeiter_optionen:
            default_name = "Mauricio Dussin"
        elif len(self.mitarbeiter_optionen) > 0:
            default_name = self.mitarbeiter_optionen[0]
        else:
            default_name = ""

        self.name_var = tk.StringVar(value=default_name)
        self._letzter_name = default_name

        # Sollarbeitszeit aus Profil laden
        std_val = self.mitarbeiter_daten[default_name]["wochenstunden"] if default_name else "0"
        tage_val = self.mitarbeiter_daten[default_name]["arbeitstage"] if default_name else "0"
        self.wochenstunden_var = tk.StringVar(value=std_val)
        self.arbeitsstage_var = tk.StringVar(value=tage_val)

        self.raster_30_min = True
        self.zeit_optionen = self.generiere_zeit_optionen()

        self.jahre_optionen = [str(y) for y in range(2025, 2035)]
        self.monate_optionen = [f"{m:02d}" for m in range(1, 13)]
        
        self.tage_speicher = {}
        self.comboboxen_speicher = {}

        # PDF-Farbe für Ü.Std aus Konfiguration laden (Standard: schwarz)
        self.pdf_uestd_farbe = "#000000"
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                self.pdf_uestd_farbe = json.load(f).get("pdf_uestd_farbe", "#000000")
        except Exception:
            pass

        self.setup_ui()
        
        self.wochenstunden_var.trace_add("write", lambda *args: self.aktualisiere_alle_berechnungen())
        self.arbeitsstage_var.trace_add("write", lambda *args: self.aktualisiere_alle_berechnungen())

        self.all_data = {}
        self.alle_daten_laden()
        
        self._aktueller_key = f"{self.name_var.get()}_{self.jahr_var.get()}-{self.monat_var.get()}"
        self.rebaue_monats_liste()

    def oeffne_mitarbeiter_verwaltung(self):
        mw = ctk.CTkToplevel(self)
        mw.title("Mitarbeiter verwalten")
        mw.geometry("450x420")
        mw.transient(self)
        mw.grab_set()

        list_frame = ctk.CTkScrollableFrame(mw, width=150)
        list_frame.pack(side="left", fill="y", padx=10, pady=10)

        form_frame = ctk.CTkFrame(mw)
        form_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        selected_emp_var = tk.StringVar()
        mw_name_var = tk.StringVar()
        mw_std_var = tk.StringVar()
        mw_tage_var = tk.StringVar()

        def load_list():
            for w in list_frame.winfo_children(): w.destroy()
            for emp in self.mitarbeiter_daten:
                rb = ctk.CTkRadioButton(list_frame, text=emp, variable=selected_emp_var, value=emp, command=on_select)
                rb.pack(anchor="w", pady=5)

        def on_select():
            emp = selected_emp_var.get()
            if emp in self.mitarbeiter_daten:
                mw_name_var.set(emp)
                mw_std_var.set(self.mitarbeiter_daten[emp]["wochenstunden"])
                mw_tage_var.set(self.mitarbeiter_daten[emp]["arbeitstage"])

        def on_save():
            name = mw_name_var.get().strip()
            if not name: return
            std = mw_std_var.get().strip()
            tage = mw_tage_var.get().strip()

            old_name = selected_emp_var.get()
            if old_name and old_name != name and old_name in self.mitarbeiter_daten:
                del self.mitarbeiter_daten[old_name]

            self.mitarbeiter_daten[name] = {"wochenstunden": std, "arbeitstage": tage}
            TimeTrackingLogic.speichere_mitarbeiter(self.mitarbeiter_daten)

            self.mitarbeiter_optionen = list(self.mitarbeiter_daten.keys())
            self.cb_name.configure(values=self.mitarbeiter_optionen)
            
            if self.name_var.get() == old_name:
                self.name_var.set(name)
                self.wechsel_state_event()

            load_list()
            selected_emp_var.set(name)
            messagebox.showinfo("Erfolg", f"Mitarbeiter '{name}' gespeichert.", parent=mw)

        def on_delete():
            name = selected_emp_var.get()
            if not name: return
            if messagebox.askyesno("Löschen", f"Soll '{name}' wirklich gelöscht werden?", parent=mw):
                if name in self.mitarbeiter_daten:
                    del self.mitarbeiter_daten[name]
                    TimeTrackingLogic.speichere_mitarbeiter(self.mitarbeiter_daten)
                    
                    self.mitarbeiter_optionen = list(self.mitarbeiter_daten.keys())
                    self.cb_name.configure(values=self.mitarbeiter_optionen)
                    
                    if self.name_var.get() == name:
                        neu_aktiv = self.mitarbeiter_optionen[0] if self.mitarbeiter_optionen else ""
                        self.name_var.set(neu_aktiv)
                        self.wechsel_state_event()

                    mw_name_var.set("")
                    mw_std_var.set("")
                    mw_tage_var.set("")
                    selected_emp_var.set("")
                    load_list()

        def on_new():
            selected_emp_var.set("")
            mw_name_var.set("")
            mw_std_var.set("")
            mw_tage_var.set("")

        load_list()

        ctk.CTkLabel(form_frame, text="Name:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,0), padx=10)
        ctk.CTkEntry(form_frame, textvariable=mw_name_var).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(form_frame, text="Wochenstunden:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,0), padx=10)
        ctk.CTkEntry(form_frame, textvariable=mw_std_var).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(form_frame, text="Arbeitstage/Woche:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,0), padx=10)
        ctk.CTkEntry(form_frame, textvariable=mw_tage_var).pack(fill="x", padx=10, pady=5)

        btn_box = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_box.pack(fill="x", pady=15, padx=10)

        ctk.CTkButton(btn_box, text="Profil leeren (Neu)", command=on_new).pack(side="top", fill="x", pady=4)
        ctk.CTkButton(btn_box, text="Speichern", fg_color="green", hover_color="darkgreen", command=on_save).pack(side="top", fill="x", pady=4)
        ctk.CTkButton(btn_box, text="Löschen", fg_color="red", hover_color="darkred", command=on_delete).pack(side="top", fill="x", pady=4)

    def generiere_zeit_optionen(self):
        opt = [""]
        schritte = (0, 30) if self.raster_30_min else (0, 15, 30, 45)
        for h in range(24):
            for m in schritte:
                opt.append(f"{h:02d}:{m:02d}")
        return opt

    def toggle_zeit_raster(self):
        self.raster_30_min = not self.raster_30_min
        self.zeit_optionen = self.generiere_zeit_optionen()
        self.btn_raster.configure(text="Zeitraster: 30 Min" if self.raster_30_min else "Zeitraster: 15 Min")

        for tag, cbs in self.comboboxen_speicher.items():
            for cb in cbs:
                val = cb.get()
                cb.configure(values=self.zeit_optionen)
                cb.set(val)

    def gib_tages_soll(self):
        try:
            w_std = float(self.wochenstunden_var.get().replace(",", "."))
            tage = float(self.arbeitsstage_var.get())
            return w_std / tage
        except (ValueError, ZeroDivisionError):
            return 0.0

    def ist_sonn_oder_feiertag(self, tag):
        try:
            jahr = int(self.jahr_var.get())
            monat = int(self.monat_var.get())
            datum = datetime.date(jahr, monat, tag)
            nrw_holidays = holidays.Germany(subdiv='NW', years=jahr)
            return datum.weekday() == 6 or datum in nrw_holidays
        except Exception:
            return False

    def setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=20, pady=15)

        z1 = ctk.CTkFrame(top_frame, fg_color="transparent")
        z1.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(z1, text="Mitarbeiter:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.cb_name = ttk.Combobox(z1, textvariable=self.name_var, values=self.mitarbeiter_optionen, width=18, state="readonly")
        self.cb_name.pack(side="left", padx=(5, 5))
        self.cb_name.bind("<<ComboboxSelected>>", self.wechsel_state_event)

        btn_ma = ctk.CTkButton(z1, text="⚙️ Verwaltung", width=40, command=self.oeffne_mitarbeiter_verwaltung, fg_color="#4b5563", hover_color="#374151")
        btn_ma.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(z1, text="Jahr:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.cb_jahr = ttk.Combobox(z1, textvariable=self.jahr_var, values=self.jahre_optionen, width=6, state="readonly")
        self.cb_jahr.pack(side="left", padx=5)
        self.cb_jahr.bind("<<ComboboxSelected>>", self.wechsel_state_event)

        ctk.CTkLabel(z1, text="Monat:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.cb_monat = ttk.Combobox(z1, textvariable=self.monat_var, values=self.monate_optionen, width=4, state="readonly")
        self.cb_monat.pack(side="left", padx=5)
        self.cb_monat.bind("<<ComboboxSelected>>", self.wechsel_state_event)

        self.btn_raster = ctk.CTkButton(z1, text="Zeitraster: 30 Min", command=self.toggle_zeit_raster, fg_color="#64748b", hover_color="#475569")
        self.btn_raster.pack(side="right", padx=5)

        ctk.CTkButton(z1, text="🎨 Ü.Std-Farbe (PDF)", command=self.aendere_pdf_uestd_farbe,
                      fg_color="#64748b", hover_color="#475569", width=160)  \
            .pack(side="right", padx=5)

        ctk.CTkButton(z1, text="📋 Dienstplan importieren", command=self.importiere_dienstplan,
                      fg_color="#0e7490", hover_color="#155e75", width=180) \
            .pack(side="right", padx=5)

        export_btn = ctk.CTkButton(z1, text="PDF Exportieren...", command=self.export_pdf, fg_color="green", hover_color="darkgreen")
        export_btn.pack(side="right", padx=5)

        z2 = ctk.CTkFrame(top_frame, fg_color="transparent")
        z2.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(z2, text="Wochenstunden:", font=("Arial", 11)).pack(side="left", padx=5)
        ctk.CTkEntry(z2, textvariable=self.wochenstunden_var, width=50, justify="center").pack(side="left", padx=5)

        ctk.CTkLabel(z2, text="Arbeitstage/Woche:", font=("Arial", 11)).pack(side="left", padx=5)
        ctk.CTkEntry(z2, textvariable=self.arbeitsstage_var, width=40, justify="center").pack(side="left", padx=5)

        self.lbl_soll_info = ctk.CTkLabel(z2, text="Tages-Soll: 0,00 Std.", font=("Arial", 11, "italic"), text_color="gray")
        self.lbl_soll_info.pack(side="left", padx=15)

        # Datenpfad-Anzeige und Schaltfläche zum Ändern
        btn_pfad = ctk.CTkButton(z2, text="📁 Datenpfad ändern", command=self.aendere_datenpfad,
                                 fg_color="#64748b", hover_color="#475569", width=160)
        btn_pfad.pack(side="right", padx=5)

        self.lbl_datenpfad = ctk.CTkLabel(z2, text=f"📁  {DATA_DIR}",
                                          font=("Arial", 10), text_color="gray")
        self.lbl_datenpfad.pack(side="right", padx=(15, 5))

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20)

        headers = [
            ("Tag", 40), ("Vormittag Von", 95), ("Vormittag Bis", 95),
            ("Nachmittag Von", 95), ("Nachmittag Bis", 95),
            ("Std.ges", 65), ("D.Plan", 60), ("A", 40), ("H", 40), ("Ü.Std", 60), ("Bemerkung", 180)
        ]
        for text, width in headers:
            lbl = ctk.CTkLabel(self.header_frame, text=text, width=width, anchor="center", font=("Arial", 11, "bold"))
            lbl.pack(side="left", padx=3)

        self.scroll_container = ctk.CTkScrollableFrame(self)
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=5)

        self.bottom_frame = ctk.CTkFrame(self, height=50)
        self.bottom_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_summen = ctk.CTkLabel(self.bottom_frame, text="Gesamtsummen | Std.ges: 0,00  |  D.Plan: 0,00  |  Ü.Std: 0,00", font=("Arial", 12, "bold"))
        self.lbl_summen.pack(side="left", padx=20, pady=10)

        save_btn = ctk.CTkButton(self.bottom_frame, text="Fortschritt Speichern", command=self.speichere_aktuellen_monat, fg_color="#3b82f6", hover_color="#1d4ed8")
        save_btn.pack(side="right", padx=10, pady=10)
        
        clear_btn = ctk.CTkButton(self.bottom_frame, text="Monat leeren", command=self.leeren_monat, fg_color="#ef4444", hover_color="#b91c1c")
        clear_btn.pack(side="right", padx=10, pady=10)

    def wechsel_state_event(self, event=None):
        self.update_idletasks()
        
        neuer_name = self.name_var.get()
        if neuer_name != self._letzter_name:
            if neuer_name in self.mitarbeiter_daten:
                self.wochenstunden_var.set(self.mitarbeiter_daten[neuer_name]["wochenstunden"])
                self.arbeitsstage_var.set(self.mitarbeiter_daten[neuer_name]["arbeitstage"])
            self._letzter_name = neuer_name

        neuer_key = f"{neuer_name}_{self.jahr_var.get()}-{self.monat_var.get()}"
        if neuer_key != self._aktueller_key:
            self.sichere_in_globalen_speicher()
            self._aktueller_key = neuer_key
            self.rebaue_monats_liste()

    def leeren_monat(self):
        if messagebox.askyesno("Tabelle leeren", f"Sollen wirklich alle eingetragenen Zeiten für '{self.name_var.get()}' im {self.monat_var.get()}/{self.jahr_var.get()} unwiderruflich gelöscht werden?"):
            self.all_data[self._aktueller_key] = {}
            self.rebaue_monats_liste()

    def auto_format_zeit(self, event, var, cb_widget):
        val = var.get().replace(":", "").replace(".", "").replace(",", "").strip()
        if not val:
            return
        if val.isdigit():
            try:
                if len(val) <= 2:
                    h = int(val)
                    if 0 <= h <= 23:
                        formatted = f"{h:02d}:00"
                        var.set(formatted)
                        cb_widget.set(formatted)
                elif len(val) == 3:
                    h, m = int(val[0]), int(val[1:])
                    if 0 <= h <= 23 and 0 <= m <= 59:
                        formatted = f"{h:02d}:{m:02d}"
                        var.set(formatted)
                        cb_widget.set(formatted)
                elif len(val) >= 4:
                    val = val[:4]
                    h, m = int(val[:2]), int(val[2:])
                    if 0 <= h <= 23 and 0 <= m <= 59:
                        formatted = f"{h:02d}:{m:02d}"
                        var.set(formatted)
                        cb_widget.set(formatted)
            except ValueError:
                pass

    def rebaue_monats_liste(self):
        for child in self.scroll_container.winfo_children():
            child.destroy()
            
        self.tage_speicher.clear()
        self.comboboxen_speicher.clear()

        jahr = int(self.jahr_var.get())
        monat = int(self.monat_var.get())
        
        _, anzahl_tage = calendar.monthrange(jahr, monat)
        nrw_holidays = holidays.Germany(subdiv='NW', years=jahr)

        tages_soll = self.gib_tages_soll()
        self.lbl_soll_info.configure(text=f"Tages-Soll: {tages_soll:.2f}".replace(".", ",") + " Std.")

        self._aktueller_key = f"{self.name_var.get()}_{self.jahr_var.get()}-{self.monat_var.get()}"
        gespeicherter_monat = self.all_data.get(self._aktueller_key, {})

        # Blockiert das versehentliche Überschreiben von D.Plan während des JSON Ladevorgangs
        self._is_loading = True

        for tag in range(1, anzahl_tage + 1):
            datum = datetime.date(jahr, monat, tag)
            ist_feiertag = datum in nrw_holidays
            standard_bemerkung = nrw_holidays.get(datum) if ist_feiertag else ""

            tag_daten = gespeicherter_monat.get(str(tag), {})

            row = ctk.CTkFrame(self.scroll_container, fg_color="transparent" if tag % 2 == 0 else ("#f9f9f9", "#2a2a2a"))
            row.pack(fill="x", pady=1)

            d = {
                "v_von": tk.StringVar(value=tag_daten.get("v_von", "")),
                "v_bis": tk.StringVar(value=tag_daten.get("v_bis", "")),
                "n_von": tk.StringVar(value=tag_daten.get("n_von", "")),
                "n_bis": tk.StringVar(value=tag_daten.get("n_bis", "")),
                "std_ges": tk.StringVar(value="0,00"),
                "d_plan": tk.StringVar(value=tag_daten.get("d_plan", "0,00")),
                "a": tk.StringVar(value=tag_daten.get("a", "")),
                "h": tk.StringVar(value=tag_daten.get("h", "")),
                "u_std": tk.StringVar(value="0,00"),
                "bemerkung": tk.StringVar(value=tag_daten.get("bemerkung", standard_bemerkung)),
                "is_urlaub": tag_daten.get("is_urlaub", False)
            }
            self.tage_speicher[tag] = d

            ctk.CTkLabel(row, text=f"{tag:02d}", width=40, font=("Arial", 11, "bold")).pack(side="left", padx=2)

            # Feste 95x28px-Wrapper für Comboboxen – garantiert pixelgenaue Ausrichtung mit Headern
            def _cb_in_frame(parent, var):
                frm = tk.Frame(parent, width=95, height=28)
                frm.pack_propagate(False)
                frm.pack(side="left", padx=3)
                cb = ttk.Combobox(frm, textvariable=var, values=self.zeit_optionen)
                cb.pack(fill="both", expand=True)
                return cb

            cb_v_von = _cb_in_frame(row, d["v_von"])
            cb_v_bis = _cb_in_frame(row, d["v_bis"])
            cb_n_von = _cb_in_frame(row, d["n_von"])
            cb_n_bis = _cb_in_frame(row, d["n_bis"])

            cb_v_von.set(d["v_von"].get())
            cb_v_bis.set(d["v_bis"].get())
            cb_n_von.set(d["n_von"].get())
            cb_n_bis.set(d["n_bis"].get())
            
            cb_v_von.bind("<FocusOut>", lambda e, v=d["v_von"], w=cb_v_von: self.auto_format_zeit(e, v, w))
            cb_v_bis.bind("<FocusOut>", lambda e, v=d["v_bis"], w=cb_v_bis: self.auto_format_zeit(e, v, w))
            cb_n_von.bind("<FocusOut>", lambda e, v=d["n_von"], w=cb_n_von: self.auto_format_zeit(e, v, w))
            cb_n_bis.bind("<FocusOut>", lambda e, v=d["n_bis"], w=cb_n_bis: self.auto_format_zeit(e, v, w))

            self.comboboxen_speicher[tag] = [cb_v_von, cb_v_bis, cb_n_von, cb_n_bis]

            # Trigger "zeit" signalisiert, dass die Arbeitszeit editiert wurde
            for var in [d["v_von"], d["v_bis"], d["n_von"], d["n_bis"]]:
                var.trace_add("write", lambda *args, t=tag: self.berechne_tag(t, ausloeser="zeit"))

            ent_ges = ctk.CTkEntry(row, textvariable=d["std_ges"], width=65, justify="center", state="disabled", fg_color=("#e2e8f0", "#1e293b"))
            ent_ges.pack(side="left", padx=3)

            ent_plan = ctk.CTkEntry(row, textvariable=d["d_plan"], width=60, justify="center")
            ent_plan.pack(side="left", padx=3)
            # Trigger "plan" signalisiert, dass der Nutzer den Planwert manuell anfasst
            d["d_plan"].trace_add("write", lambda *args, t=tag: self.berechne_tag(t, ausloeser="plan"))

            ctk.CTkEntry(row, textvariable=d["a"], width=40, justify="center").pack(side="left", padx=3)
            ctk.CTkEntry(row, textvariable=d["h"], width=40, justify="center").pack(side="left", padx=3)

            ent_ueber = ctk.CTkEntry(row, textvariable=d["u_std"], width=60, justify="center",
                                     state="disabled", fg_color=("#e2e8f0", "#1e293b"))
            ent_ueber.pack(side="left", padx=3)
            
            ctk.CTkEntry(row, textvariable=d["bemerkung"], width=180).pack(side="left", padx=3)

            btn_urlaub = ctk.CTkButton(row, text="Urlaub", width=50, height=24, font=("Arial", 11))
            if d["is_urlaub"]:
                btn_urlaub.configure(fg_color="#3b82f6", hover_color="#1d4ed8")
            else:
                btn_urlaub.configure(fg_color="#94a3b8", hover_color="#64748b")
                
            btn_urlaub.configure(command=lambda t=tag, b=btn_urlaub: self.toggle_urlaub(t, b))
            btn_urlaub.pack(side="left", padx=3)

            d["urlaub_btn"] = btn_urlaub

        self._is_loading = False
        self.aktualisiere_alle_berechnungen()

    def toggle_urlaub(self, tag, button):
        d = self.tage_speicher[tag]
        if not d["is_urlaub"]:
            d["is_urlaub"] = True
            button.configure(fg_color="#3b82f6", hover_color="#1d4ed8")
            
            if self.ist_sonn_oder_feiertag(tag):
                d["d_plan"].set("0,00")
            else:
                soll = self.gib_tages_soll()
                d["d_plan"].set(f"{soll:.2f}".replace(".", ","))
                
            d["bemerkung"].set("Urlaub")
            d["v_von"].set(""); d["v_bis"].set(""); d["n_von"].set(""); d["n_bis"].set("")
        else:
            d["is_urlaub"] = False
            button.configure(fg_color="#94a3b8", hover_color="#64748b")
            d["d_plan"].set("0,00")
            
            jahr = int(self.jahr_var.get())
            monat = int(self.monat_var.get())
            datum = datetime.date(jahr, monat, tag)
            nrw_holidays = holidays.Germany(subdiv='NW', years=jahr)
            
            if datum in nrw_holidays:
                d["bemerkung"].set(nrw_holidays.get(datum))
            else:
                d["bemerkung"].set("")
                
        self.berechne_tag(tag, ausloeser="plan")

    def berechne_tag(self, tag, ausloeser="plan"):
        if tag not in self.tage_speicher:
            return
        d = self.tage_speicher[tag]

        v_std = TimeTrackingLogic.parse_stunden(d["v_von"].get(), d["v_bis"].get())
        n_std = TimeTrackingLogic.parse_stunden(d["n_von"].get(), d["n_bis"].get())
        gesamt_std = v_std + n_std

        # AUTOMATIK: Zieht den D.Plan direkt der gearbeiteten Zeit nach, wenn du Zeiten eintippst!
        if ausloeser == "zeit" and not d["is_urlaub"] and not self._is_loading:
            neu_plan = f"{gesamt_std:.2f}".replace(".", ",")
            if d["d_plan"].get() != neu_plan:
                d["d_plan"].set(neu_plan)

        try:
            plan_std = float(d["d_plan"].get().replace(",", "."))
        except ValueError:
            plan_std = 0.0

        ueber_std = max(0.0, gesamt_std - plan_std) if gesamt_std > plan_std else 0.0

        # Bei Urlaub (keine Zeiten eingetragen): Std.ges zeigt den Planwert (Tages-Soll)
        if d["is_urlaub"] and gesamt_std == 0.0:
            d["std_ges"].set(d["d_plan"].get())
        else:
            d["std_ges"].set(f"{gesamt_std:.2f}".replace(".", ","))
        d["u_std"].set(f"{ueber_std:.2f}".replace(".", ","))

        self.aktualisiere_gesamtsummen()

    def aktualisiere_alle_berechnungen(self):
        for tag in self.tage_speicher.keys():
            if self.tage_speicher[tag]["is_urlaub"]:
                if self.ist_sonn_oder_feiertag(tag):
                    self.tage_speicher[tag]["d_plan"].set("0,00")
                else:
                    soll = self.gib_tages_soll()
                    self.tage_speicher[tag]["d_plan"].set(f"{soll:.2f}".replace(".", ","))
            self.berechne_tag(tag, ausloeser="plan")

    def aktualisiere_gesamtsummen(self):
        sum_ges = 0.0
        sum_plan = 0.0
        sum_ueber = 0.0

        for d in self.tage_speicher.values():
            try:
                sum_ges += float(d["std_ges"].get().replace(",", "."))
                sum_plan += float(d["d_plan"].get().replace(",", "."))
                sum_ueber += float(d["u_std"].get().replace(",", "."))
            except ValueError:
                pass

        self.lbl_summen.configure(
            text=f"Gesamtsummen | Std.ges: {sum_ges:.2f}  |  D.Plan: {sum_plan:.2f}  |  Ü.Std: {sum_ueber:.2f}".replace(".", ",")
        )

    def importiere_dienstplan(self):
        """Öffnet ein Dienstplan-PDF und zeigt einen Auswahldialog für alle Mitarbeiterzeilen."""
        try:
            import pdfplumber
        except ImportError:
            messagebox.showerror(
                "Fehlende Abhängigkeit",
                "Für den Dienstplan-Import wird 'pdfplumber' benötigt.\n\n"
                "Bitte installieren mit:\n  pip install pdfplumber"
            )
            return

        filepath = filedialog.askopenfilename(
            title="Dienstplan-PDF auswählen",
            filetypes=[("PDF-Dokumente", "*.pdf"), ("Alle Dateien", "*.*")]
        )
        if not filepath:
            return

        try:
            sektionen, woche_info = self._parse_alle_sektionen(filepath)
        except Exception as e:
            messagebox.showerror("Fehler beim Lesen", str(e))
            return

        if not sektionen:
            messagebox.showwarning("Keine Daten", "Keine Mitarbeiterzeilen im Dienstplan gefunden.")
            return

        self._zeige_auswahl_dialog(sektionen, woche_info)

    def _parse_alle_sektionen(self, filepath: str):
        """
        Parst ALLE Mitarbeitersektionen aus dem Dienstplan-PDF.
        Jede Sektion wird durch eine 'früh'-Zeile identifiziert.
        Rückgabe: (dict {anzeigenam: {iso_datum: zeiten}}, str woche_info)
        """
        import pdfplumber
        import re

        datum_re = re.compile(r'^\d{2}\.\d{2}\.\d{4}$')
        zeit_re  = re.compile(r'^\d{2}:\d{2}$')
        SKIP_LOWER = {"stunden"}

        with pdfplumber.open(filepath) as pdf:
            page = pdf.pages[0]
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)

        if not words:
            raise ValueError("Kein Text aus dem PDF extrahierbar.")

        # ── Tagesspalten anhand der Datumskopfzeile ermitteln ─────────────
        datum_woerter = sorted(
            [w for w in words if datum_re.match(w["text"])],
            key=lambda w: w["x0"]
        )
        if not datum_woerter:
            raise ValueError("Keine Datumsangaben (TT.MM.JJJJ) im Dienstplan gefunden.")

        woche_info = f"{datum_woerter[0]['text']} – {datum_woerter[-1]['text']}"

        spalten = []
        for i, d in enumerate(datum_woerter):
            lx = (datum_woerter[i-1]["x1"] + d["x0"]) / 2 if i > 0 else 0.0
            rx = (d["x1"] + datum_woerter[i+1]["x0"]) / 2 if i < len(datum_woerter)-1 else float("inf")
            spalten.append({"datum": d["text"], "lx": lx, "rx": rx})

        def datum_fuer_x(x: float):
            for s in spalten:
                if s["lx"] <= x < s["rx"]:
                    return s["datum"]
            return None

        # Grenze zwischen Beschriftungsspalte (Name, früh, spät, Stunden) und Tagesspalten
        label_grenze = datum_woerter[0]["x0"] - 1

        # ── Alle 'früh'-Zeilen als Sektionsanker verwenden ────────────────
        fruh_words = sorted(
            [w for w in words if w["text"].lower() in ("früh", "fruh") and w["x0"] < label_grenze],
            key=lambda w: w["top"]
        )
        if not fruh_words:
            raise ValueError("Keine 'früh'-Zeilen im Dienstplan gefunden.")

        tol = 6
        alle_sektionen = {}

        for i, fruh_w in enumerate(fruh_words):
            fruh_top = fruh_w["top"]
            naechste_top = fruh_words[i + 1]["top"] if i + 1 < len(fruh_words) else float("inf")

            # Spät-Zeile in dieser Sektion (zwischen fruh_top und naechste_top)
            spat_candidates = [
                w for w in words
                if fruh_top < w["top"] < naechste_top
                and w["text"].lower() in ("spät", "spat")
                and w["x0"] < label_grenze
            ]
            spat_y = min(spat_candidates, key=lambda w: w["top"])["top"] if spat_candidates else None

            # Mitarbeitername: letztes qualifiziertes Wort knapp oberhalb von 'früh'
            kandidaten = [
                w for w in words
                if w["top"] < fruh_top - 2
                and not zeit_re.match(w["text"])
                and not datum_re.match(w["text"])
                and w["text"].lower() not in SKIP_LOWER
                and len(w["text"]) > 1
                and w["x0"] < fruh_w["x0"] + 50
            ]
            emp_name = ""
            if kandidaten:
                emp_word = max(kandidaten, key=lambda w: w["top"])
                # Sicherstellen, dass das Wort zur aktuellen und nicht einer anderen Sektion gehört
                prev_fruh_top = fruh_words[i - 1]["top"] if i > 0 else 0
                if emp_word["top"] > prev_fruh_top:
                    emp_name = emp_word["text"]

            anzeigename = emp_name if emp_name else f"Zeile {i + 1}"

            # Zeiten für diese Sektion parsen
            sektion_words = [w for w in words if fruh_top - 3 <= w["top"] < naechste_top]

            def zeiten_pro_tag(target_y):
                if target_y is None:
                    return {}
                result = {}
                for w in sektion_words:
                    if abs(w["top"] - target_y) <= tol and zeit_re.match(w["text"]):
                        datum = datum_fuer_x((w["x0"] + w["x1"]) / 2)
                        if datum:
                            result.setdefault(datum, []).append(w["text"])
                return result

            fruh_pro_tag = zeiten_pro_tag(fruh_top)
            spat_pro_tag = zeiten_pro_tag(spat_y)

            zeiten_dict = {}
            for datum_str in set(list(fruh_pro_tag) + list(spat_pro_tag)):
                t = datum_str.split(".")
                iso = f"{t[2]}-{t[1]}-{t[0]}"
                eintrag = {}
                fruh = fruh_pro_tag.get(datum_str, [])
                spat = spat_pro_tag.get(datum_str, [])
                if len(fruh) >= 2:
                    eintrag["v_von"] = fruh[0]
                    eintrag["v_bis"] = fruh[1]
                if len(spat) >= 2:
                    eintrag["n_von"] = spat[0]
                    eintrag["n_bis"] = spat[1]
                if eintrag:
                    zeiten_dict[iso] = eintrag

            # Eindeutigen Schlüssel sicherstellen
            key = anzeigename
            counter = 2
            while key in alle_sektionen:
                key = f"{anzeigename} ({counter})"
                counter += 1
            alle_sektionen[key] = zeiten_dict

        return alle_sektionen, woche_info

    def _zeige_auswahl_dialog(self, sektionen: dict, woche_info: str):
        """Zeigt einen Dialog mit allen gefundenen Mitarbeiterzeilen zur Auswahl."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Dienstplan importieren – Mitarbeiter auswählen")
        dialog.geometry("720x480")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Kopfzeile
        ctk.CTkLabel(dialog, text=f"Woche: {woche_info}",
                     font=("Arial", 13, "bold")).pack(pady=(15, 2), padx=20, anchor="w")
        ctk.CTkLabel(dialog, text="Wähle die Zeile des gewünschten Mitarbeiters:",
                     font=("Arial", 11), text_color="gray").pack(padx=20, anchor="w")

        # Hauptbereich
        haupt = ctk.CTkFrame(dialog, fg_color="transparent")
        haupt.pack(fill="both", expand=True, padx=15, pady=10)

        # Linke Spalte – Auswahlliste
        left = ctk.CTkFrame(haupt, width=210)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        ctk.CTkLabel(left, text="Gefundene Zeilen:", font=("Arial", 11, "bold")).pack(pady=(10, 4), padx=10, anchor="w")
        list_frame = ctk.CTkScrollableFrame(left)
        list_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Rechte Spalte – Vorschau
        right = ctk.CTkFrame(haupt)
        right.pack(side="right", fill="both", expand=True)
        ctk.CTkLabel(right, text="Vorschau:", font=("Arial", 11, "bold")).pack(pady=(10, 4), padx=10, anchor="w")
        vorschau_box = ctk.CTkTextbox(right, font=("Courier", 11), state="disabled")
        vorschau_box.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        selected_var = tk.StringVar()
        namen = list(sektionen.keys())

        def zeige_vorschau(name):
            zeiten = sektionen.get(name, {})
            if not zeiten:
                text = "(Keine Zeiten gefunden)"
            else:
                lines = []
                for iso, z in sorted(zeiten.items()):
                    try:
                        d = datetime.date.fromisoformat(iso)
                        tag_str = d.strftime("%a %d.%m.")
                    except ValueError:
                        tag_str = iso
                    teile = []
                    if "v_von" in z:
                        teile.append(f"früh  {z['v_von']}–{z['v_bis']}")
                    if "n_von" in z:
                        teile.append(f"spät  {z['n_von']}–{z['n_bis']}")
                    lines.append(f"{tag_str}   {'   |   '.join(teile)}")
                text = "\n".join(lines)
            vorschau_box.configure(state="normal")
            vorschau_box.delete("1.0", "end")
            vorschau_box.insert("1.0", text)
            vorschau_box.configure(state="disabled")

        def on_select(name):
            selected_var.set(name)
            zeige_vorschau(name)

        # Vorauswahl: Nachname des aktuellen Mitarbeiters
        vollname = self.name_var.get()
        nachname = vollname.split()[-1].lower() if vollname else ""
        vorauswahl = namen[0] if namen else ""
        for n in namen:
            if nachname and nachname in n.lower():
                vorauswahl = n
                break

        for name in namen:
            ctk.CTkRadioButton(
                list_frame, text=name,
                variable=selected_var, value=name,
                command=lambda n=name: on_select(n)
            ).pack(anchor="w", pady=4, padx=5)

        if vorauswahl:
            selected_var.set(vorauswahl)
            zeige_vorschau(vorauswahl)

        # Schaltflächen
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        def on_import():
            name = selected_var.get()
            if not name or name not in sektionen:
                messagebox.showwarning("Keine Auswahl", "Bitte zuerst eine Zeile auswählen.", parent=dialog)
                return
            zeiten = sektionen[name]
            if not zeiten:
                messagebox.showwarning("Keine Zeiten", f"Für '{name}' wurden keine Zeiten gefunden.", parent=dialog)
                return
            dialog.destroy()
            self._fulle_aus_dienstplan(zeiten)

        ctk.CTkButton(btn_frame, text="Abbrechen",
                      fg_color="#64748b", hover_color="#475569",
                      command=dialog.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="✅ Importieren",
                      fg_color="green", hover_color="darkgreen",
                      command=on_import).pack(side="right", padx=5)

    def _fulle_aus_dienstplan(self, parsed: dict):
        """Trägt die geparsten Zeiten in die aktuelle Monatsansicht ein."""
        eingetragen = 0
        nicht_im_monat = []

        for datum_str, zeiten in parsed.items():
            try:
                datum = datetime.date.fromisoformat(datum_str)
            except ValueError:
                continue

            if datum.month != int(self.monat_var.get()) or datum.year != int(self.jahr_var.get()):
                nicht_im_monat.append(datum_str)
                continue

            tag = datum.day
            if tag not in self.tage_speicher:
                continue

            d = self.tage_speicher[tag]

            if d["is_urlaub"]:
                self.toggle_urlaub(tag, d["urlaub_btn"])

            for key in ("v_von", "v_bis", "n_von", "n_bis"):
                if key in zeiten:
                    d[key].set(zeiten[key])

            self.berechne_tag(tag, ausloeser="zeit")
            eingetragen += 1

        meldung = f"✅  {eingetragen} Tag(e) erfolgreich importiert."
        if nicht_im_monat:
            meldung += (
                f"\n\n{len(nicht_im_monat)} Tag(e) liegen nicht im aktuellen Monat "
                f"({self.monat_var.get()}/{self.jahr_var.get()}) und wurden übersprungen:\n"
                + ", ".join(nicht_im_monat)
            )
        messagebox.showinfo("Import abgeschlossen", meldung)

    def aendere_pdf_uestd_farbe(self):
        """Öffnet einen Farbwähler für die Ü.Std-Spalte in der exportierten PDF."""
        from tkinter import colorchooser
        farbe = colorchooser.askcolor(color=self.pdf_uestd_farbe, title="PDF-Farbe für Ü.Std wählen")
        if not (farbe and farbe[1]):
            return
        self.pdf_uestd_farbe = farbe[1]
        try:
            cfg = {}
            if os.path.exists(_CONFIG_FILE):
                with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["pdf_uestd_farbe"] = self.pdf_uestd_farbe
            with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Farbe konnte nicht gespeichert werden: {e}")
        messagebox.showinfo("Farbe gespeichert",
                            f"Ü.Std-Farbe in der PDF wurde gesetzt auf: {self.pdf_uestd_farbe}")

    def aendere_datenpfad(self):
        """Öffnet einen Ordner-Dialog, um den Datenspeicherort zu ändern."""
        global DATA_DIR, DATA_FILE, MITARBEITER_FILE

        neuer_pfad = filedialog.askdirectory(
            title="Ordner für Arbeitsnachweisdaten wählen",
            initialdir=DATA_DIR
        )
        if not neuer_pfad:
            return

        # Aktuellen Entwurf noch im alten Pfad sichern
        self.sichere_in_globalen_speicher()
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.all_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Daten nicht im bisherigen Pfad sichern:\n{e}")
            return

        # Globale Pfade aktualisieren und Konfiguration speichern
        DATA_DIR = neuer_pfad
        DATA_FILE = os.path.join(DATA_DIR, "arbeitsnachweis_daten.json")
        MITARBEITER_FILE = os.path.join(DATA_DIR, "mitarbeiter_daten.json")
        _speichere_daten_pfad(neuer_pfad)

        # Daten und Mitarbeiter aus neuem Pfad laden
        self.all_data = {}
        self.alle_daten_laden()
        self.mitarbeiter_daten = TimeTrackingLogic.lade_mitarbeiter()
        self.mitarbeiter_optionen = list(self.mitarbeiter_daten.keys())
        self.cb_name.configure(values=self.mitarbeiter_optionen)

        # Pfad-Anzeige in der UI aktualisieren
        if hasattr(self, 'lbl_datenpfad'):
            self.lbl_datenpfad.configure(text=f"📁  {DATA_DIR}")

        self.rebaue_monats_liste()
        messagebox.showinfo(
            "Datenpfad geändert",
            f"Datenpfad wurde erfolgreich geändert:\n{neuer_pfad}"
        )

    def alle_daten_laden(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                try:
                    self.all_data = json.load(f)
                except:
                    self.all_data = {}
        else:
            # Datei fehlt? Dann leeres dict erstellen und speichern
            self.all_data = {}
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def sichere_in_globalen_speicher(self):
        if not hasattr(self, 'tage_speicher') or not self.tage_speicher:
            return

        monats_schluessel = self._aktueller_key

        self.all_data[monats_schluessel] = {}
        for tag, d in self.tage_speicher.items():
            self.all_data[monats_schluessel][str(tag)] = {
                "v_von": d["v_von"].get(),
                "v_bis": d["v_bis"].get(),
                "n_von": d["n_von"].get(),
                "n_bis": d["n_bis"].get(),
                "d_plan": d["d_plan"].get(),
                "a": d["a"].get(),
                "h": d["h"].get(),
                "bemerkung": d["bemerkung"].get(),
                "is_urlaub": d["is_urlaub"]
            }
        
        self._aktueller_key = f"{self.name_var.get()}_{self.jahr_var.get()}-{self.monat_var.get()}"

    def speichere_aktuellen_monat(self):
        self.sichere_in_globalen_speicher()
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.all_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Gespeichert", "Der aktuelle Entwurf wurde erfolgreich gesichert!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")

    def export_pdf(self):
        self.sichere_in_globalen_speicher()
        monats_schluessel = f"{self.name_var.get()}_{self.jahr_var.get()}-{self.monat_var.get()}"
        
        standard_name = f"Arbeitsnachweis_{self.name_var.get()}_{self.monat_var.get()}_{self.jahr_var.get()}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF-Dokument", "*.pdf")],
            initialfile=standard_name,
            title="Arbeitsnachweis speichern unter"
        )
        if not filepath:
            return

        try:
            monats_daten = self.all_data.get(monats_schluessel, {})
            TimeTrackingLogic.generiere_pdf(
                filepath=filepath,
                name=self.name_var.get(),
                monat=self.monat_var.get(),
                jahr=self.jahr_var.get(),
                tage_daten=monats_daten,
                uestd_farbe=self.pdf_uestd_farbe
            )
            messagebox.showinfo("Erfolg", "PDF wurde erfolgreich exportiert!")
        except Exception as e:
            messagebox.showerror("Fehler", f"PDF Export fehlgeschlagen: {e}")


if __name__ == "__main__":
    app = TimeTrackingApp()
    app.mainloop()
