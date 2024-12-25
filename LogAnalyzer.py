import tkinter as tk
from tkinter import ttk, filedialog
import shelve
import os
import sys
import platform
if platform.system() == 'Darwin':
    from tkmacosx import Button
    gLeftButton = '<ButtonRelease-2>'
else:
    Button = tk.Button
    gLeftButton = '<ButtonRelease-3>'
import helpers as hl
from LogSource import LogSource, SQLLogSource

class LogAnalyzerApp:
    def __init__(self, root, config_path, data_path):
        self.root_ = root
        self.config_path_ = config_path
        self.data_path = data_path
        self.db_connection_ = None
        self.cursor_ = None
        self.root_.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root_.createcommand("::tk::mac::Quit", self.quit_app)
        self.config_path_ = config_path
        self.root_.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root_.createcommand("::tk::mac::Quit", self.quit_app)
        self.root_.title("Log Analyzer: knowledge weapon of winners")
        self.log_source_ : LogSource
        self.load_settings()
        self.init_source()
        self.show_main_screen()

    def init_source(self):
        file = os.path.join(self.data_source_dir, self.data_source_file.get())
        print(file)
        self.log_source_ = SQLLogSource(files=[file])
        if not self.log_source_.is_valid():
            hl.log('ERROR', f'{file} Invalid')

    def show_main_screen(self):
        self.root_.geometry(f"{self.ui_width}x{self.ui_height}")
        l_frame = ttk.LabelFrame(self.root_, text="Log source")
        l_frame.grid(row=0, column=0, padx=3, pady=3)
        r_frame = ttk.LabelFrame(self.root_, text="Stats")
        r_frame.grid(row=0, column=1, padx=3, pady=3)

        self.file_path_entry = ttk.Entry(l_frame, textvariable=self.data_source_file, width=30)
        self.file_path_entry.grid(row=0, column=0, padx=5, pady=5)
        self.file_select_button = Button(l_frame, text="Browse", command=self.select_source_file)
        self.file_select_button.grid(row=0, column=1, padx=5, pady=5)
        logs_frame = ttk.LabelFrame(l_frame, text="Logs", border=2)
        logs_frame.grid(row=1, column=0, columnspan=2)
        self.log_tree = ttk.Treeview(logs_frame, columns=('date', 'contest'), show='headings')
        def create_handler(sort_by):
            def handler():
                if self.sort_by == sort_by:
                    self.sort_inverted = not self.sort_inverted
                else:
                    self.sort_by = sort_by
                    self.sort_inverted = False
                self.populate_log_tree()
            return handler
        self.log_tree.heading('date', text='Date', command=create_handler('StartDate'))
        self.log_tree.heading('contest', text='Contest', command=create_handler('ContestName'))
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5 )

        scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_tree.bind('<ButtonRelease-1>', self.on_click)
#        self.log_tree.bind(gLeftButton, self.show_context_menu)
        self.populate_log_tree()

        # Stats frame
        self.stat_tree = ttk.Treeview(r_frame, columns=('stat', 'contest'), show='headings')
        self.stat_tree.heading('stat', text='Statistics')
        self.stat_tree.heading('contest', text='Contest')
        self.stat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5 )

        scrollbar = ttk.Scrollbar(r_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.stat_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        #self.stat_tree.bind('<ButtonRelease-1>', self.on_click)
#        self.log_tree.bind(gLeftButton, self.show_context_menu)
        self.populate_stats_tree()

    
    def populate_log_tree(self):
        if not self.log_source_.is_valid():
            return
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        if self.sort_inverted:
            dir = 'ASC'
        else:
            dir = 'DESC'
        logs = self.log_source_.get_contests(sorted_by=self.sort_by, dir=dir)
        for index, log in logs.iterrows():
            self.log_tree.insert('', tk.END, values=(log['StartDate'], log['ContestName'], log['ContestNR']))

    def populate_stats_tree(self):
        selected_items = self.log_tree.selection()  # Get selected item IDs
        for item_id in selected_items:
            item = self.log_tree.item(item_id)
            txt = item['values'][1]
            print(item['values'])
            self.stat_tree.heading('contest', text=txt)
        # for log in logs:
        #     self.log_tree.insert('', tk.END, values=(log[0], log[1], log[2]))

    def on_click(self, event):
        try:
            item = self.log_tree.focus()
            session_date = self.log_tree.item(item, 'values')[1]
            self.populate_stats_tree()
        except IndexError:
            pass # ignore heading click

    def display_stats(self):
        selected_items = self.log_tree.selection()  # Get selected item IDs
        for item_id in selected_items:
            item = self.log_tree.item(item_id)
            print(f"Selected date: {item_id}, Values: {item['values']}")


    def select_source_file(self):
        selected_file = filedialog.askopenfilename(
            title="Select a file",
            initialdir=self.data_source_dir,
            filetypes=(("DB files", "*.s3db *.db"), ("Cabrillo", "*.log *.txt"), ("All files", "*.*")),
            multiple=True
        )
        if selected_file:
            selected_dir, selected_file = os.path.split(selected_file[0])
            self.data_source_file.set(selected_file)
            self.data_source_dir = selected_dir
            self.save_settings()
            self.init_source()
            self.populate_log_tree()

    def quit_app(self):
        self.root_.quit()

    def load_settings(self):
        with shelve.open(os.path.join(self.config_path_,'settings')) as settings:
            self.data_source_file = tk.StringVar(value=settings.get('data_source_file', 'MASTER.SCP'))
            self.data_source_dir = settings.get('data_source_dir', self.data_path)
            self.ui_width = settings.get('ui_width',808)
            self.ui_height =settings.get('ui_height', 500)
            self.sort_by = settings.get('sort_by', 'StartDate')
            self.sort_inverted = settings.get('sort_inverted', False)

    def save_settings(self):
        with shelve.open(os.path.join(self.config_path_,'settings')) as settings:
            settings['data_source_file'] = self.data_source_file.get()
            settings['data_source_dir'] = self.data_source_dir
            settings['ui_width'] = self.ui_width
            settings['ui_height'] = self.ui_height
            settings['sort_by'] = self.sort_by
            settings['sort_inverted'] = self.sort_inverted

if getattr(sys, 'frozen', False): # application package
    bin_path = sys._MEIPASS
else: # python
    bin_path = os.path.abspath(".")

#icon_file = os.path.join(bin_path, 'MorseCodeX.ico')
# if platform.system() == 'Darwin':
#     base_path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MorseCodeX')
# elif platform.system() == 'Windows':
#     base_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'MorseCodeX')
# elif platform.system() == 'Linux':
#     base_path = os.path.join(os.path.expanduser('~'), '.MorseCodeX')
#     icon_file = ''
# else:
#     sys.exit()
base_path = './'
config_path = base_path
data_path = base_path

root = tk.Tk()
#root.iconbitmap(bitmap=icon_file)
app = LogAnalyzerApp(root, config_path=config_path, data_path=data_path)
root.mainloop()