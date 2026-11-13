"""Window layout of the Tk GUI: menu bar, the setup tab (file pickers, run buttons, log), the results / statistics / correlation tabs and the file browsers.

Mixin of cell_edge_analysis_gui.AnalysisGUI (methods moved verbatim from that file)."""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import gui_help
from gui_tooltips import attach


class LayoutMixin:
    def create_ui(self):
        """Create the main user interface."""
        # Menu bar (Help menu with the Analysis Guide)
        self.create_menubar()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tab 1: Setup & Run
        self.setup_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.setup_tab, text="Setup & Run")
        self.create_setup_tab()

        # Tab 2: Results Viewer
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="Results Viewer")
        self.create_results_tab()

        # Tab 3: Statistics
        self.stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text="Statistics")
        self.create_stats_tab()

        # Tab 4: Correlation Analysis
        self.correlation_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.correlation_tab, text="Correlation Analysis")
        self.create_correlation_tab()

    def create_menubar(self):
        """Create the top menu bar with a Help menu."""
        menubar = tk.Menu(self.root)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Analysis Guide (steps & math)...",
                              command=lambda: gui_help.show_help_window(self.root))
        help_menu.add_separator()
        help_menu.add_command(label="About...",
                              command=lambda: gui_help.show_about(self.root))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def create_setup_tab(self):
        """Create the setup and run tab."""
        # Main container with scrollbar
        canvas = tk.Canvas(self.setup_tab)
        scrollbar = ttk.Scrollbar(self.setup_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # File Selection Section
        file_frame = ttk.LabelFrame(scrollable_frame, text="Input Files", padding=10)
        file_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(file_frame, text="Image Stack:").grid(row=0, column=0, sticky='w', pady=2)
        attach(ttk.Entry(file_frame, textvariable=self.image_stack_path, width=60),
               'image_stack').grid(row=0, column=1, padx=5)
        attach(ttk.Button(file_frame, text="Browse", command=self.browse_image_stack),
               'image_stack').grid(row=0, column=2)

        ttk.Label(file_frame, text="Mask Stack:").grid(row=1, column=0, sticky='w', pady=2)
        attach(ttk.Entry(file_frame, textvariable=self.mask_stack_path, width=60),
               'mask_stack').grid(row=1, column=1, padx=5)
        attach(ttk.Button(file_frame, text="Browse", command=self.browse_mask_stack),
               'mask_stack').grid(row=1, column=2)

        ttk.Label(file_frame, text="Output Directory:").grid(row=2, column=0, sticky='w', pady=2)
        attach(ttk.Entry(file_frame, textvariable=self.output_base_dir, width=60),
               'output_dir').grid(row=2, column=1, padx=5)
        attach(ttk.Button(file_frame, text="Browse", command=self.browse_output_dir),
               'output_dir').grid(row=2, column=2)

        # Parameters Section
        self.create_parameters_section(scrollable_frame)

        # Control Buttons
        control_frame = ttk.Frame(scrollable_frame)
        control_frame.pack(fill='x', padx=10, pady=10)

        attach(ttk.Button(control_frame, text="Run All Steps", command=self.run_all_steps,
                  style='Accent.TButton'), 'run_all').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Run Selected Step", command=self.run_selected_step),
               'run_step').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Load Results", command=self.load_results),
               'load_results').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Clear Log", command=self.clear_log),
               'clear_log').pack(side='left', padx=5)

        # Progress Bar
        self.progress = ttk.Progressbar(scrollable_frame, mode='indeterminate')
        self.progress.pack(fill='x', padx=10, pady=5)

        # Log Output
        log_frame = ttk.LabelFrame(scrollable_frame, text="Analysis Log", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_parameters_section(self, parent):
        """Create parameter configuration section."""
        params_frame = ttk.LabelFrame(parent, text="Analysis Parameters", padding=10)
        params_frame.pack(fill='x', padx=10, pady=5)

        # Step selector
        step_frame = ttk.Frame(params_frame)
        step_frame.pack(fill='x', pady=5)
        ttk.Label(step_frame, text="Configure Step:").pack(side='left', padx=5)

        self.step_var = tk.StringVar(value="Step 1: Data Loading")
        steps = [
            "Step 1: Data Loading",
            "Step 2: Edge Detection",
            "Step 3: Displacement Calculation",
            "Step 4: Movement Classification",
            "Step 5: Edge Sampling",
            "Step 6: Sampling Rectangles",
            "Step 7: Intensity Extraction",
            "Step 8: Movement Assignment",
            "Step 9: Correlation Analysis"
        ]

        step_combo = ttk.Combobox(step_frame, textvariable=self.step_var, values=steps,
                                 state='readonly', width=40)
        step_combo.pack(side='left', padx=5)
        step_combo.bind('<<ComboboxSelected>>', self.on_step_selected)
        attach(step_combo, 'step_selector')

        # Parameter container
        self.param_container = ttk.Frame(params_frame)
        self.param_container.pack(fill='both', expand=True, pady=5)

        # Initialize with Step 1 parameters
        self.create_step1_params()

    def create_results_tab(self):
        """Create the results viewer tab."""
        # Control frame
        control_frame = ttk.Frame(self.results_tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="View:").pack(side='left', padx=5)

        self.view_var = tk.StringVar(value="Overview")
        views = ["Overview", "Edge Detection", "Displacement", "Classification",
                "Sampling", "Intensity"]
        attach(ttk.Combobox(control_frame, textvariable=self.view_var, values=views,
                    state='readonly', width=20), 'view_selector').pack(side='left', padx=5)
        attach(ttk.Button(control_frame, text="Update View", command=self.update_results_view),
               'update_view').pack(side='left', padx=5)

        # Frame navigation
        nav_frame = ttk.Frame(control_frame)
        nav_frame.pack(side='left', padx=20)

        ttk.Button(nav_frame, text="◄◄", command=self.first_frame, width=4).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="◄", command=self.prev_frame, width=4).pack(side='left', padx=2)

        self.frame_label = ttk.Label(nav_frame, text="Frame: 0 / 0")
        self.frame_label.pack(side='left', padx=10)
        attach(self.frame_label, 'frame_nav')

        ttk.Button(nav_frame, text="►", command=self.next_frame, width=4).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="►►", command=self.last_frame, width=4).pack(side='left', padx=2)

        # Matplotlib figure
        self.fig = Figure(figsize=(12, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.results_tab)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=5)

        # Toolbar
        toolbar_frame = ttk.Frame(self.results_tab)
        toolbar_frame.pack(fill='x', padx=10, pady=5)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

    def create_stats_tab(self):
        """Create the statistics summary tab."""
        # Stats text widget
        self.stats_text = scrolledtext.ScrolledText(self.stats_tab, wrap=tk.WORD, font=('Courier', 10))
        self.stats_text.pack(fill='both', expand=True, padx=10, pady=10)

        # Refresh button
        ttk.Button(self.stats_tab, text="Refresh Statistics",
                  command=self.update_statistics).pack(pady=5)

    def create_correlation_tab(self):
        """Create the correlation analysis tab with final summary plots."""
        # Control frame at top
        control_frame = ttk.Frame(self.correlation_tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="Correlation Analysis - Final Summary Plots",
                 font=('TkDefaultFont', 12, 'bold')).pack(side='left', padx=5)

        attach(ttk.Button(control_frame, text="Load Correlation Results",
                  command=self.load_correlation_plots), 'correlation_load').pack(side='right', padx=5)

        # Figure selection frame
        fig_frame = ttk.Frame(self.correlation_tab)
        fig_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(fig_frame, text="Select Plot:").pack(side='left', padx=5)
        self.correlation_fig_var = tk.StringVar(value="Scatter Plot")
        fig_options = ["Scatter Plot", "Binned Analysis", "Summary Statistics"]
        attach(ttk.Combobox(fig_frame, textvariable=self.correlation_fig_var, values=fig_options,
                    state='readonly', width=25), 'correlation_figure').pack(side='left', padx=5)
        ttk.Button(fig_frame, text="Update",
                  command=self.update_correlation_view).pack(side='left', padx=5)

        # Matplotlib figure for displaying correlation plots
        self.corr_fig = Figure(figsize=(12, 8))
        self.corr_canvas = FigureCanvasTkAgg(self.corr_fig, self.correlation_tab)
        self.corr_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=5)

        # Matplotlib toolbar
        toolbar_frame = ttk.Frame(self.correlation_tab)
        toolbar_frame.pack(fill='x', padx=10, pady=2)
        NavigationToolbar2Tk(self.corr_canvas, toolbar_frame)

        # Initialize correlation figure storage
        self.correlation_figures = {}

    # File browser methods
    def browse_image_stack(self):
        filename = filedialog.askopenfilename(
            title="Select Image Stack",
            filetypes=[("TIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        )
        if filename:
            self.image_stack_path.set(filename)

    def browse_mask_stack(self):
        filename = filedialog.askopenfilename(
            title="Select Mask Stack",
            filetypes=[("TIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        )
        if filename:
            self.mask_stack_path.set(filename)

    def browse_output_dir(self):
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_base_dir.set(dirname)

