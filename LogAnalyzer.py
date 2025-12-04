import tkinter as tk
from tkinter import ttk, filedialog
import shelve
import os
import sys
from datetime import datetime
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
        self.log_source_ = SQLLogSource(files=[file])
        if not self.log_source_.is_valid():
            hl.log('ERROR', f'{file} Invalid')

    def show_main_screen(self):
        self.root_.geometry(f"{self.ui_width}x{self.ui_height}")
        l_frame = ttk.LabelFrame(self.root_, text="Log source")
        l_frame.grid(row=0, column=0, padx=3, pady=3)
        r_frame = ttk.LabelFrame(self.root_, text="Results")
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
        self.log_tree.heading('date', text='Date', command=create_handler(['StartDate', 'ContestName']))
        self.log_tree.heading('contest', text='Contest', command=create_handler(['ContestName', 'StartDate']))
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5 )

        scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_tree.bind('<ButtonRelease-1>', self.on_click)
        self.log_tree.bind("<KeyRelease-Up>", self.on_click)
        self.log_tree.bind("<KeyRelease-Down>", self.on_click)
#        self.log_tree.bind(gLeftButton, self.show_context_menu)
        self.populate_log_tree()

        # Stats frame
        r_frame.columnconfigure(0, weight=1)
        r_frame.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(r_frame)
        notebook.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        stat_frame = ttk.Frame(notebook)
        stat_frame.grid(sticky="nsew")
        self.stat_tree = ttk.Treeview(stat_frame, columns=('stat', 'contest'), show='headings', height=15)
        self.stat_tree.heading('stat', text='Statistics')
        self.stat_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(stat_frame, orient=tk.VERTICAL, command=self.stat_tree.yview)
        self.stat_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, padx=3, pady=5, sticky="ns")

        save_stats = Button(stat_frame, text="Save Stats", 
                            command=lambda: save_tree_to_formatted_file(
                                [("SUMMARY", self.stat_tree),
                                 ("PERFORMANCE", self.performance_tree)], "stats.txt"))
        save_stats.grid(row = 1, column=0)
        
        
        #Performance frame
        performance_frame = ttk.Frame(notebook)
        performance_frame.grid(sticky="nsew")
        columns = ['Hour', '160', '80', '40', '20', '15', '10', 'Rate', 'Run %', 'Pct']
        self.performance_tree = ttk.Treeview(performance_frame,
                                             columns=columns, show='headings', height=16)
        self.performance_tree.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        for col in columns:
            self.performance_tree.heading(col,text=col)
            self.performance_tree.column(col, width=50)

        scrollbar = ttk.Scrollbar(performance_frame, orient=tk.VERTICAL, command=self.performance_tree.yview)
        scrollbar.grid(row=0, column=1, padx=3, pady=5, sticky="ns")
        self.performance_tree.configure(yscrollcommand=scrollbar.set)
        
        notebook.add(stat_frame, text="Stats")
        notebook.add(performance_frame, text="Peformance")
        
        self.populate_stats_tree()
        self.populate_performance_tree()

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
        columns = [ f'col{idx}' for idx in range(len(selected_items)+1)]
        self.stat_tree["columns"] = columns
        self.stat_tree.heading(columns[0], text='Statistics')
        stats = []
        for idx, col in enumerate(columns[1:]):
            item_id = selected_items[idx]
            item = self.log_tree.item(item_id)
            contest_name = item['values'][1]
            contest_id = item['values'][2]
            self.stat_tree.heading(col, text=contest_name)
            qs = self.log_source_.get_contest_qsos(contest_id=contest_id)
            stat, counts_10min, counts_30min, counts_60min = hl.generate_stats(qs)
            stat = list(stat.items())
            stat.insert(0,('Power category', self.log_source_.get_contest_info(contest_id)['PowerCategory'][0]))
            stat.insert(0,  ('Date', datetime.strptime(item['values'][0], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d-%H:%M")))
            stat = dict(stat)
            stats.append((stat, counts_10min, counts_30min, counts_60min))
        if len(stats) == 0:
            return
        for item in self.stat_tree.get_children():
            self.stat_tree.delete(item)

        for key in stats[0][0].keys():
            if key == 'Operating Time':
                formatted_values = []
                for st in stats:
                    td = st[0][key]
                    hours = td.components.days * 24 + td.components.hours
                    minutes = td.components.minutes
                    formatted_values.append(f"{hours:02d}:{minutes:02d}")
                values = [key] + formatted_values
            else:
                values = [key] + [st[0][key] for st in stats]
            self.stat_tree.insert('', tk.END, values=values)

    def populate_performance_tree(self):
        selected_items = self.log_tree.selection()  # Get selected item IDs
        contests = [ f'col{idx}' for idx in range(len(selected_items)+1)]
        stats = []
        for idx, col in enumerate(contests[1:]):
            item_id = selected_items[idx]
            item = self.log_tree.item(item_id)
            contest_id = item['values'][2]
            qs = self.log_source_.get_contest_qsos(contest_id=contest_id)
            stat = hl.generate_pefromance_data(qs, 1, "hours")
            stat = list(stat.items())
            stat = dict(stat)
            stats.append(stat)
        if len(stats) == 0:
            return
        for item in self.performance_tree.get_children():
            self.performance_tree.delete(item)

        for key in stats[-1].keys():
            values = [hl.get_hours(key)] + list(stats[-1][key])
            for i, v in enumerate(values):
                v = v[0]
                if i > 5:
                    break

            self.performance_tree.insert('', tk.END, values=values)


    def on_click(self, event):
        try:
            item = self.log_tree.focus()
            session_date = self.log_tree.item(item, 'values')[1]
            self.populate_stats_tree()
            self.populate_performance_tree()
        except IndexError:
            pass # ignore heading click

    def display_stats(self):
        selected_items = self.log_tree.selection()  # Get selected item IDs
        for item_id in selected_items:
            item = self.log_tree.item(item_id)


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
        self.ui_width = self.root_.winfo_width()  # Get current width
        self.ui_height = self.root_.winfo_height()
        self.save_settings()
        self.root_.quit()

    def load_settings(self):
        with shelve.open(os.path.join(self.config_path_,'settings')) as settings:
            self.data_source_file = tk.StringVar(value=settings.get('data_source_file', 'MASTER.SCP'))
            self.data_source_dir = settings.get('data_source_dir', self.data_path)
            self.ui_width = settings.get('ui_width',1200)
            self.ui_height =settings.get('ui_height', 500)
            self.sort_by = settings.get('sort_by', ['StartDate', 'ContestName'])
            self.sort_inverted = settings.get('sort_inverted', False)

    def save_settings(self):
        with shelve.open(os.path.join(self.config_path_,'settings')) as settings:
            settings['data_source_file'] = self.data_source_file.get()
            settings['data_source_dir'] = self.data_source_dir
            settings['ui_width'] = self.ui_width
            settings['ui_height'] = self.ui_height
            settings['sort_by'] = self.sort_by
            settings['sort_inverted'] = self.sort_inverted

from tabulate import tabulate

def traverse_tree_for_table(tree, item="", level=0, output=None):
    """Collect treeview data for table output."""
    if output is None:
        output = []
    children = tree.get_children(item)
    for child in children:
        text = tree.item(child, "text")  # Get the text of the current item
        values = tree.item(child, "values")  # Get the values of the current item
        row = list(values)  # Combine the text and values into a single row
        output.append(row)
    return output

# Function to save treeview contents to a formatted table
def save_tree_to_formatted_file(trees, filename):
    """Save treeview data as a formatted table to a text file."""
    with open(filename, "w") as f:
        for title, tree in trees:
            headers = []
            for col in tree["columns"]:
                headers.append(tree.heading(col)["text"])  # Fetch the text of each column header
            data = traverse_tree_for_table(tree)
            table = tabulate(data, headers=headers, tablefmt="grid")
            f.write(title)
            f.write("\n\n")
            f.write(table)
            f.write("\n\n\n")

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