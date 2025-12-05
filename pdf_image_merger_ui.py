# pdf_image_merger_ui.py
import os
import time
import threading
from queue import Queue, Empty
from tkinter import Tk, StringVar, IntVar, BooleanVar, END, filedialog, ttk, Text, Scrollbar, RIGHT, Y, LEFT, BOTH, Frame, Label
import webbrowser
from pdf_image_merger_core import gather_target_folders, process_single_folder  # core functions

class MergerApp:
    def open_github(self, event=None):
        webbrowser.open("https://github.com/AlexandreJustinRepia")  

    def __init__(self, root):
        self.root = root
        root.title("PDF & Image Merger — PENRO Bulacan")
        root.geometry("900x650")
        root.configure(bg="white")
        root.resizable(False, False)

        # Variables
        self.folder_var = StringVar()
        self.total_folders = IntVar(value=0)
        self.processed_folders = IntVar(value=0)
        self.merged_count = IntVar(value=0)
        self.running = BooleanVar(value=False)

        # ---------- Top branding frame ----------
        brand_frame = Frame(root, bg="#4CAF50", height=60)
        brand_frame.pack(fill='x')
        Label(brand_frame, text="📂 PDF & Image Merger", bg="#4CAF50", fg="white", font=("Helvetica", 18, "bold")).pack(side='left', padx=15)
        Label(brand_frame, text="PENRO Bulacan", bg="#4CAF50", fg="white", font=("Helvetica", 12, "italic")).pack(side='left', padx=10)

        # ---------- Folder selection ----------
        frm_top = Frame(root, bg="white", pady=10)
        frm_top.pack(fill='x', padx=15)

        Label(frm_top, text="Main Folder:", bg="white", fg="#1B5E20", font=("Helvetica", 10, "bold")).pack(side='left')
        self.entry_folder = ttk.Entry(frm_top, textvariable=self.folder_var, width=60, font=("Helvetica", 10))
        self.entry_folder.pack(side='left', padx=(8,6))
        ttk.Button(frm_top, text="Browse", command=self.browse_folder).pack(side='left', padx=2)
        ttk.Button(frm_top, text="Start", command=self.start_process).pack(side='left', padx=2)
        ttk.Button(frm_top, text="Stop", command=self.stop_process).pack(side='left', padx=2)

        # ---------- Info stats ----------
        frm_info = Frame(root, bg="white", pady=10)
        frm_info.pack(fill='x', padx=15)

        def create_stat(label_text, variable, col):
            Label(frm_info, text=label_text, bg="white", fg="#1B5E20", font=("Helvetica", 9, "bold")).grid(row=0, column=col*2, sticky='w')
            Label(frm_info, textvariable=variable, bg="white", fg="#4CAF50", font=("Helvetica", 9)).grid(row=0, column=col*2+1, sticky='w', padx=(5,15))

        create_stat("Folders to process:", self.total_folders, 0)
        create_stat("Processed:", self.processed_folders, 1)
        create_stat("Merged files:", self.merged_count, 2)
        # Elapsed and ETA
        Label(frm_info, text="Elapsed:", bg="white", fg="#1B5E20", font=("Helvetica", 9, "bold")).grid(row=1, column=0, sticky='w', pady=(5,0))
        self.lbl_elapsed = Label(frm_info, text="00:00:00", bg="white", fg="#4CAF50", font=("Helvetica", 9))
        self.lbl_elapsed.grid(row=1, column=1, sticky='w', pady=(5,0))

        Label(frm_info, text="ETA:", bg="white", fg="#1B5E20", font=("Helvetica", 9, "bold")).grid(row=1, column=2, sticky='w', pady=(5,0))
        self.lbl_eta = Label(frm_info, text="--:--:--", bg="white", fg="#4CAF50", font=("Helvetica", 9))
        self.lbl_eta.grid(row=1, column=3, sticky='w', pady=(5,0))

        # ---------- Progress bar ----------
        self.progress = ttk.Progressbar(root, orient='horizontal', mode='determinate', style="Green.Horizontal.TProgressbar")
        self.progress.pack(fill='x', padx=15, pady=(0,10))
        self.percent_var = StringVar(value="0%")
        Label(root, textvariable=self.percent_var, bg="white", fg="#1B5E20", font=("Helvetica", 10, "bold")).pack()

        # ---------- Log area ----------
        log_frame = Frame(root, bg="white", bd=1, relief="solid")
        log_frame.pack(fill=BOTH, expand=True, padx=15, pady=(5,15))

        self.log_text = Text(log_frame, wrap='word', bg="#F7F7F7", fg="#1B5E20", font=("Consolas", 10))
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # ---------- Internal ----------
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._log_queue = Queue()
        self._start_time = None

        root.after(200, self._poll_log_queue)
        root.after(1000, self._update_elapsed)

    # ---------- Functions ----------
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def log(self, *lines):
        for line in lines:
            self._log_queue.put(line)

    def _poll_log_queue(self):
        try:
            while True:
                line = self._log_queue.get_nowait()
                self.log_text.insert(END, line + "\n")
                self.log_text.see('end')
        except Empty:
            pass
        self.root.after(200, self._poll_log_queue)

    def _update_elapsed(self):
        if self.running.get():
            if self._start_time:
                elapsed = int(time.time() - self._start_time)
                self.lbl_elapsed.config(text=time.strftime('%H:%M:%S', time.gmtime(elapsed)))
                processed = self.processed_folders.get()
                total = self.total_folders.get()
                if processed > 0 and processed < total:
                    elapsed_per_folder = elapsed / processed
                    remaining = total - processed
                    eta_seconds = int(elapsed_per_folder * remaining)
                    self.lbl_eta.config(text=time.strftime('%H:%M:%S', time.gmtime(eta_seconds)))
                else:
                    self.lbl_eta.config(text="--:--:--")
        else:
            self.lbl_eta.config(text="00:00:00")
        self.root.after(1000, self._update_elapsed)

    def start_process(self):
        if self.running.get():
            self.log('Already running.')
            return
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self.log('Please choose a valid folder to proceed.')
            return
        self.log_text.delete('1.0', END)
        self.log(f"Starting scan in folder: {folder}")
        folders = gather_target_folders(folder)
        self.total_folders.set(len(folders))
        self.processed_folders.set(0)
        self.merged_count.set(0)
        self.progress['maximum'] = max(1, len(folders))
        self.progress['value'] = 0
        self.percent_var.set("0%")
        self._stop_event.clear()
        self._start_time = time.time()
        self.running.set(True)
        self._worker_thread = threading.Thread(target=self._worker, args=(folders,), daemon=True)
        self._worker_thread.start()

    def stop_process(self):
        if not self.running.get():
            self.log('Not running.')
            return
        self._stop_event.set()
        self.log('Stop requested. Finishing current folder then stopping...')

    def _worker(self, folders):
        created_total = 0
        for idx, folder_path in enumerate(folders, start=1):
            if self._stop_event.is_set():
                self.log('Stopping: user requested cancel.')
                break
            self.log(f'\nProcessing folder ({idx}/{len(folders)}): {folder_path}')
            local_log = []
            try:
                created = process_single_folder(folder_path, local_log)
            except Exception as e:
                local_log.append(f"❌ Error processing folder {folder_path}: {e}")
                created = False
            for L in local_log:
                self.log(L)
            if created:
                created_total += 1
                self.merged_count.set(created_total)
            self.processed_folders.set(idx)
            self.progress['value'] = idx
            percent = int((idx / self.total_folders.get()) * 100)
            self.percent_var.set(f"{percent}%")
        self.running.set(False)
        elapsed = int(time.time() - (self._start_time or time.time()))
        self.log(f"\nDONE. Processed {self.processed_folders.get()} folders. Merged files created: {created_total}. Elapsed: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")

# ---------- Main ----------
if __name__ == '__main__':
    root = Tk()
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except:
        pass
    style.configure("TButton", font=("Helvetica", 10, "bold"), foreground="white", background="#4CAF50")
    style.map("TButton", background=[('active', '#388E3C'), ('pressed', '#2E7D32')])
    style.configure("Green.Horizontal.TProgressbar", troughcolor="#E0E0E0", background="#4CAF50", thickness=20)

    app = MergerApp(root)

    # Frame for the developer credit
    frm_credit = ttk.Frame(root, style="TFrame")
    frm_credit.pack(pady=(10, 0))

    # Normal text
    lbl_text = ttk.Label(frm_credit, text="Developed by:", background="white", foreground="#1B5E20", font=("Helvetica", 10))
    lbl_text.pack(side="left")

    # Clickable GitHub link
    lbl_github = ttk.Label(
        frm_credit, 
        text="🔗 Alexandre Justin Repia",
        background="white",
        foreground="#1B5E20",
        font=("Helvetica", 10, "underline"),
        cursor="hand2"
    )
    lbl_github.pack(side="left", padx=(5,0))
    lbl_github.bind("<Button-1>", app.open_github)

    root.mainloop()