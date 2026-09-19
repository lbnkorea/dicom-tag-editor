"""
DICOM Tag Editor
────────────────
필요 라이브러리 설치:
    pip install pydicom tkinterdnd2
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

try:
    import pydicom
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False


# ─── 색상 팔레트 ───────────────────────────────────────────────
C = {
    "bg":        "#10121A",
    "surface":   "#181B26",
    "surface2":  "#1E2233",
    "border":    "#2A2F45",
    "border_hi": "#4A6FD8",
    "accent":    "#4A6FD8",
    "accent_hi": "#6B8FFF",
    "text":      "#E2E6F3",
    "text_dim":  "#5A6080",
    "text_mid":  "#8B93B3",
    "success":   "#3ECF8E",
    "drop_bg":   "#141827",
    "drop_hi":   "#1A2240",
}

FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_LABEL = ("Segoe UI", 9,  "bold")
FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 8)
FONT_MONO  = ("Consolas", 8)
FONT_BTN   = ("Segoe UI", 12, "bold")


# ─── DICOM 처리 ────────────────────────────────────────────────
def find_dicom_files(root_dir):
    result = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            lower = fname.lower()
            if lower.endswith((".dcm", ".dicom", ".ima")) or "." not in fname:
                result.append(os.path.join(dirpath, fname))
    return result


def is_dicom(filepath):
    try:
        with open(filepath, "rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"
    except Exception:
        return False


def set_tag(ds, group, elem, vr, value):
    tag = (group, elem)
    try:
        ds[tag].value = value
    except KeyError:
        ds.add_new(tag, vr, value)


def process_dicom_files(folder, institution, patient_name,
                        progress_cb, done_cb, error_cb):
    if not PYDICOM_AVAILABLE:
        error_cb("pydicom 라이브러리가 없습니다.\n\n터미널에서 설치하세요:\n  pip install pydicom")
        return

    all_files = find_dicom_files(folder)
    if not all_files:
        error_cb("선택한 폴더에서 DICOM 파일을 찾을 수 없습니다.")
        return

    dicom_files = [f for f in all_files if is_dicom(f)] or all_files
    total = len(dicom_files)
    modified = skipped = 0

    for i, fpath in enumerate(dicom_files):
        progress_cb(i + 1, total, os.path.basename(fpath))
        try:
            ds = pydicom.dcmread(fpath, force=True)
            set_tag(ds, 0x0008, 0x0005, "CS", "ISO 2022 IR 149")
            if institution:
                set_tag(ds, 0x0008, 0x0080, "LO", institution)
            if patient_name:
                set_tag(ds, 0x0010, 0x0010, "PN", patient_name)
            pydicom.dcmwrite(fpath, ds)
            modified += 1
        except Exception:
            skipped += 1

    done_cb(modified, skipped, total)


# ─── 메인 앱 ──────────────────────────────────────────────────
class App(TkinterDnD.Tk if DND_AVAILABLE else tk.Tk):

    WIN_W = 540

    def __init__(self):
        super().__init__()
        self.title("DICOM Tag Editor")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self._folder = ""
        self._busy   = False
        self._build()
        self.update_idletasks()
        self._fit_and_center()

    def _fit_and_center(self):
        self.update_idletasks()
        content_h = self._inner.winfo_reqheight() + 52
        screen_h  = self.winfo_screenheight()
        win_h     = min(content_h, screen_h - 80)
        x = (self.winfo_screenwidth()  - self.WIN_W) // 2
        y = (screen_h - win_h) // 2
        self.geometry(f"{self.WIN_W}x{win_h}+{x}+{y}")
        if win_h < content_h:
            self._canvas.config(yscrollcommand=self._scrollbar.set)
            self._scrollbar.pack(side="right", fill="y")
            self.bind("<MouseWheel>", self._on_mousewheel)
            self.bind("<Button-4>", lambda e: self._canvas.yview_scroll(-1, "units"))
            self.bind("<Button-5>", lambda e: self._canvas.yview_scroll( 1, "units"))

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── UI 구성 ─────────────────────────────────────────────────
    def _build(self):
        container = tk.Frame(self, bg=C["bg"])
        container.pack(fill="both", expand=True)

        self._scrollbar = tk.Scrollbar(container, orient="vertical",
                                       bg=C["surface2"], troughcolor=C["bg"],
                                       highlightthickness=0, bd=0)
        self._canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0,
                                  width=self.WIN_W)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.config(command=self._canvas.yview)

        self._inner = tk.Frame(self._canvas, bg=C["bg"])
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw",
                                    width=self.WIN_W)
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(
                             scrollregion=self._canvas.bbox("all")))

        root = self._inner
        PAD  = dict(padx=30)

        # 헤더
        hdr = tk.Frame(root, bg=C["bg"])
        hdr.pack(fill="x", padx=30, pady=(28, 4))
        tk.Label(hdr, text="DICOM", font=FONT_TITLE,
                 fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Label(hdr, text=" Tag Editor", font=FONT_TITLE,
                 fg=C["text"], bg=C["bg"]).pack(side="left")

        tk.Label(root, text="DICOM 파일의 태그를 일괄 수정합니다  ·  하위 폴더 포함",
                 font=FONT_SMALL, fg=C["text_dim"], bg=C["bg"],
                 **PAD).pack(anchor="w")

        self._div(root, top=16, bot=18)

        # ── 폴더 드롭존 ──
        self._lbl(root, "대상 폴더", PAD)

        self.drop_frame = tk.Frame(root, bg=C["drop_bg"],
            highlightthickness=2, highlightbackground=C["border"], cursor="hand2")
        self.drop_frame.pack(fill="x", padx=30, ipady=20)

        inner_drop = tk.Frame(self.drop_frame, bg=C["drop_bg"])
        inner_drop.pack(expand=True)

        tk.Label(inner_drop, text="⬇", font=("Segoe UI", 24),
                 fg=C["border_hi"], bg=C["drop_bg"]).pack()

        self.drop_main = tk.Label(inner_drop,
            text="폴더를 여기에 드래그 & 드롭",
            font=("Segoe UI", 11, "bold"), fg=C["text_mid"], bg=C["drop_bg"])
        self.drop_main.pack(pady=(2, 0))

        self.drop_sub = tk.Label(inner_drop,
            text="또는 클릭하여 폴더 선택",
            font=FONT_SMALL, fg=C["text_dim"], bg=C["drop_bg"])
        self.drop_sub.pack(pady=(3, 0))

        self.drop_path = tk.Label(inner_drop, text="",
            font=("Consolas", 9), fg=C["success"], bg=C["drop_bg"])
        self.drop_path.pack(pady=(6, 0))

        for w in (self.drop_frame, inner_drop, self.drop_main, self.drop_sub):
            w.bind("<Button-1>", lambda e: self._pick_folder())
            w.bind("<Enter>",    lambda e: self._drop_hover(True))
            w.bind("<Leave>",    lambda e: self._drop_hover(False))

        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<DropEnter>>", self._on_drop_enter)
            self.drop_frame.dnd_bind("<<DropLeave>>", self._on_drop_leave)
            self.drop_frame.dnd_bind("<<Drop>>",      self._on_drop)

        self._div(root, top=20, bot=18)

        # ── Institution Name ──
        self._lbl(root, "Institution Name  (0008,0080)", PAD)
        self.inst_var = tk.StringVar()
        self._entry_field(root, self.inst_var, "예: Seoul Medical Center")

        self._div(root, top=16, bot=16)

        # ── Patient Name ──
        self._lbl(root, "Patient Name  (0010,0010)", PAD)
        self.name_var = tk.StringVar()
        self._entry_field(root, self.name_var, "예: 홍길동")

        self._div(root, top=20, bot=16)

        # ── 태그 요약 ──
        info = tk.Frame(root, bg=C["surface2"],
                        highlightthickness=1, highlightbackground=C["border"])
        info.pack(fill="x", padx=30)

        for i, (tag, name, desc) in enumerate([
            ("(0008,0005)", "Specific Character Set", "ISO 2022 IR 149  [고정]"),
            ("(0008,0080)", "Institution Name",        "입력값 적용"),
            ("(0010,0010)", "Patient Name",             "입력값 적용"),
        ]):
            row = tk.Frame(info, bg=C["surface2"])
            row.pack(fill="x", padx=14,
                     pady=(10 if i == 0 else 3, 10 if i == 2 else 0))
            tk.Label(row, text=tag,  font=FONT_MONO,  fg=C["accent"],
                     bg=C["surface2"], width=12, anchor="w").pack(side="left")
            tk.Label(row, text=name, font=FONT_SMALL, fg=C["text"],
                     bg=C["surface2"], width=24, anchor="w").pack(side="left")
            tk.Label(row, text=f"→  {desc}", font=FONT_SMALL,
                     fg=C["text_dim"], bg=C["surface2"]).pack(side="left")

        self._div(root, top=20, bot=6)

        # ── 진행바 ──
        self.prog_text = tk.StringVar(value="")
        tk.Label(root, textvariable=self.prog_text,
                 font=FONT_SMALL, fg=C["text_dim"], bg=C["bg"],
                 **PAD).pack(anchor="w")

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("D.Horizontal.TProgressbar",
                        troughcolor=C["surface2"], background=C["accent"],
                        bordercolor=C["border"], lightcolor=C["accent"],
                        darkcolor=C["accent"], thickness=5)
        self.progress = ttk.Progressbar(root, style="D.Horizontal.TProgressbar",
                                        orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=30, pady=(4, 0))

        # ── 수정 버튼 ──
        self._div(root, top=20, bot=0)

        self.run_btn = tk.Button(
            root,
            text="수정 시작",
            font=FONT_BTN,
            fg="white",
            bg=C["accent"],
            activeforeground="white",
            activebackground=C["accent_hi"],
            relief="flat",
            bd=0,
            pady=16,
            cursor="hand2",
            command=self._run,
        )
        self.run_btn.pack(fill="x", padx=30, pady=(0, 30))

    # ── 헬퍼 ─────────────────────────────────────────────────────
    def _div(self, parent, top=12, bot=12):
        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", padx=30, pady=(top, bot))

    def _lbl(self, parent, text, pad):
        tk.Label(parent, text=text, font=FONT_LABEL,
                 fg=C["text_mid"], bg=C["bg"],
                 **pad).pack(anchor="w", pady=(0, 6))

    def _entry_field(self, parent, var, placeholder):
        frame = tk.Frame(parent, bg=C["surface"],
                         highlightthickness=1, highlightbackground=C["border"])
        frame.pack(fill="x", padx=30)

        e = tk.Entry(frame, textvariable=var,
                     font=FONT_BODY, fg=C["text_dim"], bg=C["surface"],
                     insertbackground=C["accent"], relief="flat", bd=0)
        e.pack(fill="x", padx=14, pady=11)
        e.insert(0, placeholder)
        e._ph = placeholder

        def focus_in(ev):
            if e.get() == e._ph:
                e.delete(0, "end")
                e.config(fg=C["text"])
            frame.config(highlightbackground=C["border_hi"])

        def focus_out(ev):
            if not e.get():
                e.insert(0, e._ph)
                e.config(fg=C["text_dim"])
            frame.config(highlightbackground=C["border"])

        e.bind("<FocusIn>",  focus_in)
        e.bind("<FocusOut>", focus_out)

    def _get_val(self, var, placeholder):
        v = var.get().strip()
        return "" if v == placeholder else v

    # ── 드롭존 이벤트 ────────────────────────────────────────────
    def _drop_hover(self, on):
        bg  = C["drop_hi"]   if on else C["drop_bg"]
        bdr = C["border_hi"] if on else C["border"]
        self.drop_frame.config(bg=bg, highlightbackground=bdr)
        self._set_bg_r(self.drop_frame, bg)

    def _set_bg_r(self, w, bg):
        try: w.config(bg=bg)
        except Exception: pass
        for c in w.winfo_children():
            self._set_bg_r(c, bg)

    def _on_drop_enter(self, e): self._drop_hover(True)
    def _on_drop_leave(self, e): self._drop_hover(False)

    def _on_drop(self, event):
        self._drop_hover(False)
        raw = event.data.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        path = raw.split("} {")[0].strip()
        if os.path.isdir(path):
            self._set_folder(path)
        else:
            messagebox.showwarning("폴더 오류", "폴더를 드롭해 주세요.")

    def _pick_folder(self):
        if self._busy: return
        folder = filedialog.askdirectory(title="DICOM 파일이 있는 폴더 선택")
        if folder:
            self._set_folder(folder)

    def _set_folder(self, path):
        self._folder = path
        display = path if len(path) <= 54 else "…" + path[-51:]
        self.drop_path.config(text=display)
        self.drop_main.config(text="✓  폴더 선택됨", fg=C["success"])
        self.drop_sub.config(text="클릭하여 다시 선택")
        self.drop_frame.config(highlightbackground=C["success"])

    # ── 실행 ─────────────────────────────────────────────────────
    def _run(self):
        if self._busy: return
        if not self._folder or not os.path.isdir(self._folder):
            messagebox.showwarning("폴더 선택", "유효한 폴더를 선택해 주세요.")
            return

        institution  = self._get_val(self.inst_var, "예: Seoul Medical Center")
        patient_name = self._get_val(self.name_var, "예: 홍길동")

        self._busy = True
        self.run_btn.config(text="처리 중...", state="disabled",
                            bg=C["text_dim"], cursor="watch")
        self.progress["value"] = 0
        self.prog_text.set("")

        threading.Thread(
            target=process_dicom_files,
            args=(self._folder, institution, patient_name,
                  self._on_progress, self._on_done, self._on_error),
            daemon=True,
        ).start()

    def _on_progress(self, cur, total, fname):
        self.after(0, lambda c=cur, t=total, f=fname: (
            self.progress.__setitem__("value", int(c / t * 100)),
            self.prog_text.set(f"[{c}/{t}]  {f}"),
        ))

    def _on_done(self, modified, skipped, total):
        self.after(0, lambda: self._finish(modified, skipped, total))

    def _finish(self, modified, skipped, total):
        self._busy = False
        self.run_btn.config(text="수정 시작", state="normal",
                            bg=C["accent"], cursor="hand2")
        self.progress["value"] = 100
        self.prog_text.set(
            f"완료  —  {total}개 발견 / {modified}개 수정 / {skipped}개 건너뜀")
        messagebox.showinfo("Finished",
            f"✅  처리가 완료되었습니다.\n\n"
            f"  발견된 파일 : {total}개\n"
            f"  수정 완료   : {modified}개\n"
            f"  건너뜀      : {skipped}개\n\n"
            f"폴더: {self._folder}")

    def _on_error(self, msg):
        self.after(0, lambda: self._show_error(msg))

    def _show_error(self, msg):
        self._busy = False
        self.run_btn.config(text="수정 시작", state="normal",
                            bg=C["accent"], cursor="hand2")
        messagebox.showerror("오류", msg)


# ─── 실행 ─────────────────────────────────────────────────────
def main():
    if not PYDICOM_AVAILABLE:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("라이브러리 없음",
            "pydicom이 설치되어 있지 않습니다.\n\n"
            "터미널에서 실행하세요:\n  pip install pydicom tkinterdnd2")
        return

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
