import os, sys, random, subprocess, tempfile, threading, queue, shutil, math, struct, json, time, zipfile, re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tmc_audio_brain import classify as audio_brain_classify, editorial_layer as audio_brain_editorial, musical_sections as audio_brain_sections

APP_VERSION='19.6.7'
VIDEO_EXTS={'.mp4','.mkv','.mov','.webm','.avi','.m4v'}

class AutoVideoApp:
    @staticmethod
    def _no_console_kwargs():
        # Hide child console windows on Windows; harmless elsewhere.
        return {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)}
    def __init__(self,root):
        self.root=root; root.title(f'TMC-FPV AutoEditor v{APP_VERSION}')
        root.geometry('1100x850'); root.minsize(980,700)
        # Start maximised where supported; fall back to screen-sized geometry.
        try: root.state('zoomed')
        except tk.TclError:
            root.geometry(f'{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0')
        self.download_url=tk.StringVar(value='')
        self.config_path=Path.home()/'.tmcfpv_autoeditor_settings.json'
        self.saved_settings={}
        try: self.saved_settings=json.loads(self.config_path.read_text(encoding='utf-8'))
        except Exception: self.saved_settings={}
        default_folder=''
        self.q=queue.Queue(); self.running=False; self.job_type='generate'; self.scan_cancel=threading.Event(); self.render_cancel=threading.Event(); self.render_proc=None; self.scan_proc=None; self.download_proc=None; self.ffmpeg_ready=False; self.active_encoder='libx264'; self.encoder_status='CPU fallback'; self.last_stage_summary=[]; self.app_dir=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent; self.ytdlp_dir=self.app_dir/'yt-dlp'; self.ytdlp_exe=self.ytdlp_dir/'yt-dlp.exe'; self.ytdlp_url='https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe'; self.ffmpeg_dir=self.app_dir/'FFmpeg'/'bin'; self.ffmpeg_zip_url='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
        self.folder=tk.StringVar(value=self.saved_settings.get('footage_folder',default_folder)); self.song=tk.StringVar(value=self.saved_settings.get('song',''))
        self.output=tk.StringVar(value=self.saved_settings.get('output',''))
        self.download_quality=tk.StringVar(value=self.saved_settings.get('download_quality','720p'))
        self.min_len=tk.StringVar(value='2.5'); self.max_len=tk.StringVar(value='7')
        self.resolution=tk.StringVar(value=self.saved_settings.get('output_resolution','720p')); self.aspect_ratio=tk.StringVar(value=self.saved_settings.get('aspect_ratio','16:9 Landscape')); self.retro=tk.BooleanVar(value=True)
        self.output_quality=tk.StringVar(value=self.saved_settings.get('output_quality','High (CRF 20)'))
        self.fade_in=tk.BooleanVar(value=self.saved_settings.get('fade_in',False)); self.fade_out=tk.BooleanVar(value=self.saved_settings.get('fade_out',False))
        self.intro_path=tk.StringVar(value=self.saved_settings.get('intro_path',''))
        self.use_intro=tk.BooleanVar(value=self.saved_settings.get('use_intro',bool(self.saved_settings.get('intro_path',''))))
        if self.intro_path.get() and not Path(self.intro_path.get()).is_file():
            self.intro_path.set(''); self.use_intro.set(False)  # stale v9 bundled intro path: safely clear and skip
        self.intro_duration=tk.StringVar(value=self.saved_settings.get('intro_duration','2.0'))
        self.random_transitions=tk.BooleanVar(value=self.saved_settings.get('random_transitions',False))
        self.artistic_mode=tk.BooleanVar(value=self.saved_settings.get('artistic_mode',False))
        self.transition_strength=tk.StringVar(value=self.saved_settings.get('transition_strength','Balanced'))
        self.vertical_mode=tk.StringVar(value=self.saved_settings.get('vertical_mode','Original (fit)'))
        self.output_fps=tk.StringVar(value=self.saved_settings.get('output_fps','30 fps')); self.turn_it_up=tk.BooleanVar(value=self.saved_settings.get('turn_it_up',False))
        self.preset=tk.StringVar(value='Custom')
        self.seed=tk.StringVar(value=''); self.mode=tk.StringVar(value=self.saved_settings.get('mode','Story arc (recommended)')); self.single_source_order=tk.StringVar(value=self.saved_settings.get('single_source_order','Random'))
        self.highlight_schedule=self.saved_settings.get('highlight_schedule','')
        self.music_trim_schedule=self.saved_settings.get('music_trim_schedule','')
        self.dark_mode=tk.BooleanVar(value=bool(self.saved_settings.get('dark_mode',False)))
        self._build(); self._apply_theme(); self.root.after(150,self._poll)
    def toggle_dark_mode(self):
        self.dark_mode.set(not self.dark_mode.get())
        self.saved_settings['dark_mode']=self.dark_mode.get()
        self.save_settings()
        self._apply_theme()
    def _apply_theme(self):
        dark=bool(self.dark_mode.get())
        if dark:
            colors={'bg':'#25282B','panel':'#34383C','field':'#202326','border':'#555B60','fg':'#F0F2F4','muted':'#C6CBD0','accent':'#FF9800','select':'#67400F'}
        else:
            colors={'bg':'#F0F0F0','panel':'#F0F0F0','field':'#FFFFFF','border':'#C8C8C8','fg':'#202020','muted':'#555555','accent':'#D97800','select':'#FCE5C5'}
        self.theme_colors=colors
        try:
            style=ttk.Style(self.root)
            if 'clam' in style.theme_names(): style.theme_use('clam')
            style.configure('.',background=colors['bg'],foreground=colors['fg'])
            style.configure('TFrame',background=colors['bg'])
            style.configure('TLabelframe',background=colors['panel'],foreground=colors['fg'],bordercolor=colors['border'])
            style.configure('TLabelframe.Label',background=colors['panel'],foreground=colors['fg'])
            style.configure('TLabel',background=colors['bg'],foreground=colors['fg'])
            style.configure('TButton',background=colors['panel'],foreground=colors['fg'],bordercolor=colors['border'])
            style.map('TButton',background=[('active',colors['select']),('pressed',colors['select'])],foreground=[('active',colors['fg'])])
            style.configure('TButton',padding=5)
            style.configure('Accent.TButton',background=colors['accent'],foreground='#202020',padding=(12,8),font=('Segoe UI',10,'bold'))
            style.map('Accent.TButton',background=[('active',colors['select']),('pressed',colors['select'])],foreground=[('disabled',colors['muted'])])
            style.map('TButton',foreground=[('disabled',colors['muted'])],background=[('disabled',colors['panel'])])
            style.configure('TEntry',fieldbackground=colors['field'],foreground=colors['fg'],insertcolor=colors['fg'])
            style.configure('TCombobox',fieldbackground=colors['field'],background=colors['panel'],foreground=colors['fg'],arrowcolor=colors['fg'])
            style.map('TCombobox',fieldbackground=[('readonly',colors['field'])],foreground=[('readonly',colors['fg'])])
            style.configure('TCheckbutton',background=colors['bg'],foreground=colors['fg'])
            style.map('TCheckbutton',foreground=[('disabled',colors['muted'])])
            style.configure('TRadiobutton',background=colors['bg'],foreground=colors['fg'])
            style.map('TRadiobutton',foreground=[('disabled',colors['muted'])])
            style.configure('TLabel',background=colors['bg'],foreground=colors['fg'])
            style.configure('TRadiobutton',background=colors['bg'],foreground=colors['fg'])
            style.configure('Horizontal.TProgressbar',background=colors['accent'],troughcolor=colors['panel'])
            style.configure('TScrollbar',background=colors['panel'],troughcolor=colors['bg'],arrowcolor=colors['fg'])
            self.root.configure(background=colors['bg'])
            self.dark_mode_btn.configure(text=('LIGHT MODE' if dark else 'DARK MODE'))
            # Theme native Tk widgets (log, schedule editors) and canvas backgrounds.
            self._theme_widget_tree(self.root,colors)
        except Exception as exc:
            try:self._log(f'Theme update warning: {exc}')
            except Exception:pass
    def _theme_widget_tree(self,widget,colors):
        try:
            cls=widget.winfo_class()
            if cls in ('Text','Listbox','Entry'):
                widget.configure(background=colors['field'],foreground=colors['fg'],insertbackground=colors['fg'],selectbackground=colors['select'],selectforeground=colors['fg'],highlightbackground=colors['border'],highlightcolor=colors['accent'])
            elif cls=='Canvas':
                widget.configure(background=colors['panel'],highlightbackground=colors['border'])
            elif cls=='Frame':
                widget.configure(background=colors['bg'])
            elif cls=='Button':
                widget.configure(background=colors['panel'],foreground=colors['fg'],activebackground=colors['select'],activeforeground=colors['fg'],highlightbackground=colors['border'])
            elif cls=='Label':
                widget.configure(background=colors['panel'],foreground=colors['fg'])
            elif cls=='Toplevel':
                widget.configure(background=colors['bg'])
            for child in widget.winfo_children(): self._theme_widget_tree(child,colors)
        except Exception: pass
    def _build(self):
        # v18.6 UI rebuild: clean, simple workflow; advanced controls are opt-in.
        shell=ttk.Frame(self.root); shell.pack(fill='both',expand=True)
        body=ttk.Frame(shell); body.pack(side='top',fill='both',expand=True)
        canvas=tk.Canvas(body,highlightthickness=0,borderwidth=0)
        vscroll=ttk.Scrollbar(body,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side='right',fill='y'); canvas.pack(side='left',fill='both',expand=True)
        frm=ttk.Frame(canvas,padding=18)
        self.main_form=frm
        canvas_window=canvas.create_window((0,0),window=frm,anchor='nw')
        def update_scrollregion(_event=None): canvas.configure(scrollregion=canvas.bbox('all'))
        def fit_content_width(event): canvas.itemconfigure(canvas_window,width=event.width)
        frm.bind('<Configure>',update_scrollregion); canvas.bind('<Configure>',fit_content_width)
        def wheel_scroll(event): canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind_all('<MouseWheel>',wheel_scroll)

        # Header: three equal-width zones. Branding and utility controls balance the central Import card.
        header=ttk.Frame(frm); header.pack(fill='x',pady=(0,10))
        for col in range(3): header.columnconfigure(col,weight=1,uniform='headerzone')
        titlebox=ttk.Frame(header); titlebox.grid(row=0,column=0,sticky='nsew',padx=(0,5))
        ttk.Label(titlebox,text='TMC-FPV AutoEditor',font=('Segoe UI',19,'bold')).pack(anchor='w')
        ttk.Label(titlebox,text=f'AUTOMATED VIDEO PRODUCTION  ·  v{APP_VERSION}',font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(2,0))
        ttk.Label(titlebox,text='The Lazy Persons DVR Editor',font=('Segoe UI',9,'italic')).pack(anchor='w',pady=(2,0))

        # Central import zone — its footprint is equal to the title and utility zones.
        import_zone=ttk.Frame(header); import_zone.grid(row=0,column=1,sticky='nsew',padx=5)
        self.import_card_btn=ttk.Button(import_zone,text='IMPORT FOOTAGE\nAdd videos or a folder',command=lambda:self._toggle_import_panel(self.import_panel, self.import_card_btn, stages))
        self.import_card_btn.pack(fill='both',expand=True)

        header_actions=ttk.Frame(header); header_actions.grid(row=0,column=2,sticky='nsew',padx=(5,0))
        utility_row=ttk.Frame(header_actions); utility_row.pack(expand=True,anchor='center')
        self.pc_info_btn=ttk.Button(utility_row,text='ABOUT',command=self.show_pc_info); self.pc_info_btn.pack(side='left',padx=(0,6))
        self.dark_mode_btn=ttk.Button(utility_row,text='DARK MODE',command=self.toggle_dark_mode); self.dark_mode_btn.pack(side='left')
        self._apply_theme()

        # Optional import/download row: a three-cell bank with controls only in the centre cell.
        self.source_kind=tk.StringVar(value='YouTube')
        self.download_dest=tk.StringVar(value=self.saved_settings.get('download_folder',''))
        self.import_panel=ttk.Frame(frm)
        for import_col in range(3): self.import_panel.columnconfigure(import_col,weight=1,uniform='importbank')
        import_content=ttk.LabelFrame(self.import_panel,text='Import footage (optional)',padding=8)
        import_content.grid(row=0,column=1,sticky='nsew',padx=5)
        ttk.Label(import_content,text='Source').grid(row=0,column=0,sticky='w')
        ttk.Combobox(import_content,textvariable=self.source_kind,values=['YouTube','Google Photos shared album'],state='readonly',width=18).grid(row=0,column=1,sticky='w',padx=4)
        ttk.Label(import_content,text='Download quality').grid(row=0,column=2,sticky='w',padx=(8,0))
        ttk.Combobox(import_content,textvariable=self.download_quality,values=['480p','720p','1080p','Best available'],state='readonly',width=12).grid(row=0,column=3,sticky='w',padx=4)
        ttk.Label(import_content,text='Video / playlist / channel / shared album URL').grid(row=1,column=0,sticky='w',pady=(6,0))
        self.download_url=tk.StringVar(value='')
        ttk.Entry(import_content,textvariable=self.download_url,width=30).grid(row=1,column=1,columnspan=2,sticky='ew',padx=4,pady=(6,0))
        ttk.Button(import_content,text='Choose destination…',command=self.pick_download_folder).grid(row=1,column=3,padx=4,pady=(6,0))
        self.download_dest_label=ttk.Label(import_content,text='Destination: '+(self.download_dest.get() or '(select a folder)'),foreground='#245b85')
        self.download_dest_label.grid(row=2,column=0,columnspan=4,sticky='w',pady=(5,0))
        self.download_btn=ttk.Button(import_content,text='DOWNLOAD',command=self.start_download,state='disabled'); self.download_btn.grid(row=3,column=0,pady=(6,0),sticky='w')
        self.photos_open_btn=ttk.Button(import_content,text='OPEN GOOGLE PHOTOS LINK',command=self.open_google_photos,state='disabled'); self.photos_open_btn.grid(row=3,column=1,pady=(6,0),sticky='w')
        ttk.Label(import_content,text='YouTube downloads use yt-dlp. For Google Photos, open the album in your browser and extract Download all into the destination.',foreground='#555',wraplength=420).grid(row=4,column=0,columnspan=4,sticky='w',pady=(6,0))
        import_content.columnconfigure(1,weight=1); import_content.columnconfigure(2,weight=1)
        self.download_dest.trace_add('write',self.update_download_buttons)
        self.download_quality.trace_add('write',lambda *_: self.save_settings())
        self.download_url.trace_add('write',self.update_download_buttons)
        self.source_kind.trace_add('write',self.update_download_buttons)

        # v18.8.0: three equal stage bank, with balance inside each stage.
        stages=ttk.Frame(frm); stages.pack(fill='x',pady=(0,8))
        for col in range(3): stages.columnconfigure(col,weight=1,uniform='mainstage')

        # Stage 1 — project files: three aligned, compact rows.
        project=ttk.LabelFrame(stages,text='1  ·  Project files',padding=8); project.grid(row=0,column=0,sticky='nsew',padx=(0,4))
        project.columnconfigure(1,weight=1)
        ttk.Label(project,text='Footage folder').grid(row=0,column=0,sticky='w',pady=4)
        ttk.Entry(project,textvariable=self.folder,width=24).grid(row=0,column=1,sticky='ew',padx=5,pady=4)
        ttk.Button(project,text='Browse…',command=self.pick_folder).grid(row=0,column=2,pady=4)
        ttk.Label(project,text='Music file').grid(row=1,column=0,sticky='w',pady=4)
        ttk.Entry(project,textvariable=self.song,width=24).grid(row=1,column=1,sticky='ew',padx=5,pady=4)
        ttk.Button(project,text='Browse…',command=self.pick_song).grid(row=1,column=2,pady=4)
        ttk.Label(project,text='Output file').grid(row=2,column=0,sticky='w',pady=4)
        ttk.Entry(project,textvariable=self.output,width=24).grid(row=2,column=1,sticky='ew',padx=5,pady=4)
        ttk.Button(project,text='Browse…',command=self.pick_output).grid(row=2,column=2,pady=4)
        for var in (self.folder,self.song): var.trace_add('write',lambda *_: self.root.after(150,self.refresh_estimate))

        # Stage 2 — edit choices, internally balanced around its own centreline.
        edit=ttk.LabelFrame(stages,text='2  ·  Choose your edit',padding=8); edit.grid(row=0,column=1,sticky='nsew',padx=4)
        edit.columnconfigure(0,weight=1,uniform='editbalance'); edit.columnconfigure(1,weight=1,uniform='editbalance')
        left_edit=ttk.Frame(edit); left_edit.grid(row=0,column=0,sticky='nsew',padx=(0,4))
        right_edit=ttk.Frame(edit); right_edit.grid(row=0,column=1,sticky='nsew',padx=(4,0))
        ttk.Label(left_edit,text='Editing style',font=('Segoe UI',10,'bold')).pack(anchor='w')
        ttk.Combobox(left_edit,textvariable=self.mode,values=['Story arc (recommended)','FPV action / fast cuts','Retro documentary / long shots','Rhythm-focused','Random montage'],state='readonly',width=19).pack(fill='x',pady=(4,6))
        ttk.Label(right_edit,text='Quick preset').pack(anchor='w')
        preset_row=ttk.Frame(right_edit); preset_row.pack(fill='x',pady=(4,6))
        ttk.Combobox(preset_row,textvariable=self.preset,values=['Custom','FPV Action','Long Range','Retro Camcorder','Music Video'],state='readonly',width=12).pack(side='left',fill='x',expand=True)
        ttk.Button(preset_row,text='Apply',command=self.apply_preset).pack(side='left',padx=(4,0))
        ttk.Checkbutton(edit,text='Artistic Mode — automatic creative variation',variable=self.artistic_mode).grid(row=1,column=0,columnspan=2,pady=(4,0))
        ttk.Checkbutton(edit,text='TURN IT UP TO ELEVEN — amplify the Director',variable=self.turn_it_up).grid(row=2,column=0,columnspan=2,pady=(4,0))

        # Stage 3 — output options use the same equal-half structure.
        outputbox=ttk.LabelFrame(stages,text='3  ·  Video output',padding=8); outputbox.grid(row=0,column=2,sticky='nsew',padx=(4,0))
        outputbox.columnconfigure(0,weight=1,uniform='outputbalance'); outputbox.columnconfigure(1,weight=1,uniform='outputbalance')
        out_left=ttk.Frame(outputbox); out_left.grid(row=0,column=0,sticky='nsew',padx=(0,4))
        out_right=ttk.Frame(outputbox); out_right.grid(row=0,column=1,sticky='nsew',padx=(4,0))
        ttk.Label(out_left,text='Resolution').pack(anchor='w')
        ttk.Combobox(out_left,textvariable=self.resolution,values=['720p','1080p','1440p'],state='readonly',width=8).pack(anchor='w',pady=(3,6))
        ttk.Label(out_left,text='Aspect ratio').pack(anchor='w')
        ttk.Combobox(out_left,textvariable=self.aspect_ratio,values=['16:9 Landscape','1:1 Square','9:16 Vertical (crop)'],state='readonly',width=15).pack(anchor='w',pady=(3,0))
        ttk.Label(out_right,text='Quality').pack(anchor='w')
        ttk.Combobox(out_right,textvariable=self.output_quality,values=['Standard (CRF 23)','High (CRF 20)','Very high (CRF 18)'],state='readonly',width=15).pack(anchor='w',pady=(3,6))
        ttk.Label(out_right,text='Frame rate').pack(anchor='w')
        ttk.Combobox(out_right,textvariable=self.output_fps,values=['30 fps','50 fps','60 fps'],state='readonly',width=8).pack(anchor='w',pady=(3,0))

        # Advanced controls are hidden behind a single explicit reveal.
        self.advanced_panel=ttk.LabelFrame(frm,text='Advanced options',padding=10)
        adv_toggle=ttk.Button(frm,text='＋  Advanced options (clip lengths, effects, schedules, intro/logo)',command=lambda:self._toggle_panel(self.advanced_panel,adv_toggle))
        adv_toggle.pack(fill='x',pady=(0,8))
        adv=self.advanced_panel
        for col in range(3): adv.columnconfigure(col,weight=1,uniform='advanced')
        stylebox=ttk.LabelFrame(adv,text='Clip selection',padding=8); stylebox.grid(row=0,column=0,sticky='nsew',padx=4,pady=3)
        ttk.Label(stylebox,text='Minimum clip (s)').grid(row=0,column=0,sticky='w'); ttk.Entry(stylebox,textvariable=self.min_len,width=7).grid(row=0,column=1,sticky='w',padx=5)
        ttk.Label(stylebox,text='Maximum clip (s)').grid(row=1,column=0,sticky='w',pady=5); ttk.Entry(stylebox,textvariable=self.max_len,width=7).grid(row=1,column=1,sticky='w',padx=5)
        ttk.Label(stylebox,text='Source order').grid(row=2,column=0,sticky='w',pady=5); ttk.Combobox(stylebox,textvariable=self.single_source_order,values=['Random','Chronological'],state='readonly',width=13).grid(row=2,column=1,sticky='w',padx=5)
        self.highlight_schedule_button=ttk.Button(stylebox,text='Edit highlight schedule…',command=self.edit_highlights); self.highlight_schedule_button.grid(row=3,column=0,columnspan=2,sticky='w',pady=(8,2))
        self.highlight_status=tk.StringVar(value='✓ Schedule loaded' if self.highlight_schedule.strip() else 'No highlights scheduled')
        self.highlight_status_label=ttk.Label(stylebox,textvariable=self.highlight_status,foreground=('#17833b' if self.highlight_schedule.strip() else '#666')); self.highlight_status_label.grid(row=4,column=0,columnspan=2,sticky='w')
        self.music_trim_button=ttk.Button(stylebox,text='Edit music trim schedule…',command=self.edit_music_trim); self.music_trim_button.grid(row=5,column=0,columnspan=2,sticky='w',pady=(8,2))
        self.music_trim_status=tk.StringVar(value='✓ Trim loaded' if self.music_trim_schedule.strip() else 'Full track (untouched)')
        self.music_trim_status_label=ttk.Label(stylebox,textvariable=self.music_trim_status,foreground=('#17833b' if self.music_trim_schedule.strip() else '#666')); self.music_trim_status_label.grid(row=6,column=0,columnspan=2,sticky='w')
        effectsbox=ttk.LabelFrame(adv,text='Effects',padding=8); effectsbox.grid(row=0,column=1,sticky='nsew',padx=4,pady=3)
        ttk.Checkbutton(effectsbox,text='Retro handheld / camcorder look',variable=self.retro).grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Checkbutton(effectsbox,text='Fade video in',variable=self.fade_in).grid(row=1,column=0,sticky='w',pady=5)
        ttk.Checkbutton(effectsbox,text='Fade video out',variable=self.fade_out).grid(row=1,column=1,sticky='w',pady=5)
        ttk.Checkbutton(effectsbox,text='Random transitions',variable=self.random_transitions).grid(row=2,column=0,sticky='w')
        ttk.Label(effectsbox,text='Transition strength').grid(row=3,column=0,sticky='w',pady=5); ttk.Combobox(effectsbox,textvariable=self.transition_strength,values=['Subtle','Balanced','Strong','Heavy'],state='readonly',width=12).grid(row=3,column=1,sticky='w',padx=4)
        ttk.Label(effectsbox,text='Vertical footage').grid(row=4,column=0,sticky='w',pady=5); ttk.Combobox(effectsbox,textvariable=self.vertical_mode,values=['Original (fit)','50% zoom'],state='readonly',width=14).grid(row=4,column=1,sticky='w',padx=4)
        introbox=ttk.LabelFrame(adv,text='Intro / logo',padding=8); introbox.grid(row=0,column=2,sticky='nsew',padx=4,pady=3)
        ttk.Checkbutton(introbox,text='Include intro/logo',variable=self.use_intro,command=self.save_settings).grid(row=0,column=0,columnspan=3,sticky='w')
        ttk.Entry(introbox,textvariable=self.intro_path).grid(row=1,column=0,columnspan=2,sticky='ew',padx=(0,4),pady=5); ttk.Button(introbox,text='Browse…',command=self.pick_intro).grid(row=1,column=2,sticky='w',pady=5)
        ttk.Label(introbox,text='Still-image duration (s)').grid(row=2,column=0,sticky='w'); ttk.Entry(introbox,textvariable=self.intro_duration,width=7).grid(row=2,column=1,sticky='w',padx=4)
        ttk.Label(introbox,text='Random seed').grid(row=3,column=0,sticky='w',pady=5); ttk.Entry(introbox,textvariable=self.seed,width=12).grid(row=3,column=1,sticky='w',padx=4); ttk.Button(introbox,text='Copy seed',command=self.copy_seed).grid(row=3,column=2,sticky='w')
        introbox.columnconfigure(0,weight=1); introbox.columnconfigure(1,weight=1)

        # v19.5.0: Storyboard is an in-app collapsible drawer, matching Advanced options.
        self.storyboard_drawer=tk.Frame(frm)
        self.storyboard_toggle=ttk.Button(frm,text='＋  Storyboard preview (review and replace clips)',command=self._toggle_storyboard_drawer)
        self.storyboard_toggle.pack(fill='x',pady=(0,8))
        self.storyboard_drawer.pack_forget()

        # Settings persistence and render-estimate refresh hooks
        for var in (self.output_quality,self.fade_in,self.fade_out,self.use_intro,self.intro_path,self.intro_duration,self.resolution,self.aspect_ratio,self.mode,self.random_transitions,self.artistic_mode,self.transition_strength,self.vertical_mode,self.output_fps,self.single_source_order,self.turn_it_up):
            var.trace_add('write',lambda *_: self.save_settings())
        for var in (self.resolution,self.output_quality,self.output_fps,self.random_transitions): var.trace_add('write',lambda *_: self.root.after(150,self.refresh_estimate))
        self.hardware_summary=tk.StringVar(value='Checking PC hardware…')
        self.estimate_summary=tk.StringVar(value='Estimated render time: calculating…')
        estimate=ttk.Label(frm,textvariable=self.estimate_summary,foreground='#245b85',wraplength=930); estimate.pack(anchor='w',pady=(0,10)); self.estimate_summary_label=estimate

        # Fixed, centered action ribbon. Symmetrical margins keep the controls visually balanced.
        dock=ttk.Frame(shell,padding=(10,7)); dock.pack(side='bottom',fill='x')
        ribbon_outer=ttk.LabelFrame(dock,text='Controls',padding=(8,5)); ribbon_outer.pack(fill='x',pady=(0,5))
        ribbon=ttk.Frame(ribbon_outer); ribbon.pack(anchor='center')
        self.scan_btn=ttk.Button(ribbon,text='SCAN FOOTAGE',command=self.scan_library); self.scan_btn.pack(side='left',padx=3)
        self.cancel_scan_btn=ttk.Button(ribbon,text='CANCEL SCAN',command=self.cancel_scan,state='disabled'); self.cancel_scan_btn.pack(side='left',padx=3)
        self.generate_btn=ttk.Button(ribbon,text='▶  GENERATE VIDEO',command=self.start,state='disabled',style='Accent.TButton'); self.generate_btn.pack(side='left',padx=3)
        self.generate_again_btn=ttk.Button(ribbon,text='GENERATE AGAIN',command=self.start_new_random,state='disabled'); self.generate_again_btn.pack(side='left',padx=3)
        self.cancel_render_btn=ttk.Button(ribbon,text='CANCEL RENDER',command=self.cancel_render,state='disabled'); self.cancel_render_btn.pack(side='left',padx=3)
        ttk.Button(ribbon,text='CHECK PROJECT',command=self.preflight).pack(side='left',padx=3)
        ttk.Button(ribbon,text='OPEN OUTPUT FOLDER',command=self.open_output_folder).pack(side='left',padx=3)
        ttk.Button(ribbon,text='PLAY FINISHED VIDEO',command=self.play_output).pack(side='left',padx=3)
        ttk.Button(ribbon,text='COPY LOG / ERROR DETAILS',command=self.copy_log).pack(side='left',padx=3)
        status=ttk.Frame(dock); status.pack(fill='x',pady=(2,4))
        self.progress_text=tk.StringVar(value='Ready — choose project files to begin')
        ttk.Label(status,textvariable=self.progress_text).pack(side='left',anchor='w')
        self.progress=ttk.Progressbar(status,mode='determinate',maximum=100,value=0); self.progress.pack(side='right',fill='x',expand=True,padx=(12,0))
        log_panel=ttk.LabelFrame(dock,text='Activity / log',padding=(6,3)); log_panel.pack(fill='x')
        log_text_frame=ttk.Frame(log_panel); log_text_frame.pack(fill='both',expand=True)
        self.log=tk.Text(log_text_frame,height=3,wrap='word',state='disabled',font=('Consolas',9))
        log_scroll=ttk.Scrollbar(log_text_frame,orient='vertical',command=self.log.yview); self.log.configure(yscrollcommand=log_scroll.set)
        self.log.pack(side='left',fill='both',expand=True); log_scroll.pack(side='right',fill='y')

        self._log(f'TMC-FPV AutoEditor v{APP_VERSION} loaded — Live Storyboard, 50 FPS, Turn It Up To Eleven and FPV interpretation v3.')
        self.update_download_buttons(); self._add_tooltips(); self.root.after(300,self.ensure_ffmpeg_async); self.root.after(350,self.ensure_ytdlp_async); self.root.after(450,self.hardware_scan_async); self.root.after(800,self.refresh_estimate)
    def _toggle_import_panel(self,panel,button,stages):
        if panel.winfo_manager():
            panel.pack_forget(); button.configure(text='IMPORT FOOTAGE\nAdd videos or a folder')
        else:
            panel.pack(fill='x',pady=(0,8),before=stages)
            button.configure(text='IMPORT FOOTAGE\nHide import options')
    def _toggle_panel(self,panel,button):
        if panel.winfo_manager():
            panel.pack_forget(); button.configure(text=button.cget('text').replace('－','＋').replace('−','＋'))
        else:
            panel.pack(fill='x',pady=(0,8),before=button); button.configure(text=button.cget('text').replace('＋','－'))
    def _add_tooltips(self):
        tips={
            'ABOUT':'Opens build details, intelligence-system explanations, development notes, hardware and render-time estimate. Hover over brain components for explanations.',
            'Source':'Choose the Stage 1 import method: YouTube download with yt-dlp, or the Google Photos shared-album browser workflow.',
            'Download quality':'Select the target quality for YouTube downloads. Best available may produce larger files. The chosen quality is limited by what the source offers.',
            'Video / playlist / channel / shared album URL':'Paste the URL for a YouTube video, playlist or channel, or a Google Photos shared album. Use the Source selector to choose the matching workflow.',
            'Select download destination…':'Choose the folder where Stage 1 downloads or imported files will be placed. You must select a destination before the download/import buttons are enabled.',
            'DOWNLOAD':'Downloads the selected YouTube source to the destination folder. Requires yt-dlp. Archive tracking can skip items already downloaded. Google Photos is handled in the browser instead.',
            'OPEN GOOGLE PHOTOS LINK':'Opens the shared album in your browser. Use Google Photos Download all, save the ZIP to your selected destination, then extract it into that folder. Return to Stage 2 and scan the footage',
            'Footage folder':'Folder containing the videos to edit. The scan includes subfolders. A single source video can still be edited by selecting sections from it',
            'Music file':'The soundtrack for the finished edit. Clip selection and timing are planned around the soundtrack length and its analysed energy where available',
            'Output MP4':'Full path and filename for the rendered video. Choose a destination and filename ending in .mp4',
            'Editing style':'Select the overall editing approach. This influences clip selection, pacing and how sections are arranged; it does not guarantee a specific sequence',
            'Minimum clip (s)':'Shortest target duration for a selected footage section, in seconds. Use a positive number and keep it below or equal to the maximum clip length',
            'Maximum clip (s)':'Longest target duration for a selected footage section, in seconds. Use a positive number and keep it above or equal to the minimum clip length',
            'Clip length (seconds)':'Minimum and maximum values define the target range for individual video sections, in seconds. Minimum must not exceed maximum',
            'Source order (all videos)':'Random mixes selected sections from the available videos. Chronological selects across the source timeline in forward order; split files are ordered by filename',
            'Quick preset':'Choose a preset recipe to populate several editing settings at once. The preset is a starting point and can be customized afterward',
            'Apply preset':'Applies the selected Quick preset to the editing controls. It overwrites those settings with the preset values; you can then adjust them',
            'Output size':'Sets the final video frame size. Larger resolutions generally take longer to encode and may increase file size. This is output resolution, not source quality',
            'Quality':'Sets the H.264 encoding quality/bitrate trade-off using CRF. Lower CRF values generally mean higher quality and larger files, and may take longer to encode',
            'Output quality':'Sets the H.264 encoding quality/bitrate trade-off using CRF. Lower CRF values generally mean higher quality and larger files, and may take longer to encode',
            'Frame rate':'Sets output frame rate. 50 fps is especially useful for 100 fps DVR: FFmpeg selects alternate frames for clean 2:1 sampling without interpolation. 30 and 60 fps remain available.',
            'Output frame rate':'Sets output frame rate. 50 fps is especially useful for 100 fps DVR: FFmpeg selects alternate frames for clean 2:1 sampling without interpolation. 30 and 60 fps remain available.',
            'Vertical footage':'For 16:9 sources, the existing frame treatment is unchanged. For non-16:9 footage in 16:9 output: Original (fit) keeps the entire image visible and adds black padding as needed. 50% zoom: portrait (9:16) footage is enlarged to 150% of its fit size and centre-cropped; other non-16:9 landscape/near-square sources fill and crop. If you choose a square or vertical output aspect ratio, this control is not used for the same 16:9 fit/zoom handling',
            'Aspect ratio':'Choose the final frame shape. 16:9 Landscape fits/crops source footage using the landscape rules; 1:1 Square outputs a square frame; 9:16 Vertical (crop) outputs portrait video and crops to fill',
            'Retro handheld / camcorder look':'Adds a restrained vintage-style image treatment: reduced saturation, adjusted contrast/brightness, grain and vignette. It affects the rendered footage',
            'Apply retro handheld / camcorder look':'Adds a restrained vintage-style image treatment: reduced saturation, adjusted contrast/brightness, grain and vignette. It affects the rendered footage',
            'Fade video in':'Fades the video picture up from black at the beginning of the edit',
            'Fade video out':'Fades the video picture down to black at the end of the edit',
            'Random transitions':'Allows occasional randomly selected transitions between montage clips. If disabled, clips use hard cuts. Transitions may be unavailable if FFmpeg lacks the required filters',
            'Transition strength':'Controls the frequency/duration range of random transitions. Only has an effect when Random transitions is enabled; stronger settings use more noticeable/longer transitions',
            'Artistic Mode':'Adds restrained creative variation automatically: occasional monochrome, colour/contrast treatments, grain or vignette accents, plus a more experimental transition pool when random transitions are enabled. Most clips remain untouched; effects avoid consecutive repetition. This is an early version and will become more context-aware as scene and music analysis improve',
            'Artistic Mode (creative editing)':'Adds restrained creative variation automatically: occasional monochrome, colour/contrast treatments, grain or vignette accents, plus a more experimental transition pool when random transitions are enabled. Most clips remain untouched; effects avoid consecutive repetition. This is an early version and will become more context-aware as scene and music analysis improve',
            'Use intro/logo':'Adds the selected intro video or still image before the main montage. Turn this on and choose a valid file below',
            'Use optional intro/logo':'Adds the selected intro video or still image before the main montage. Turn this on and choose a valid file below',
            'Browse…':'Browse for the intro/logo file. Supported still images use the Intro duration setting; video intros use their own duration',
            'Intro duration (still image)':'Duration in seconds for a still-image intro/logo. Enter a positive number. Video intros use the source video duration',
            'Intro duration':'Duration in seconds for a still-image intro/logo. Enter a positive number. Video intros use the source video duration',
            'Random seed':'Optional seed used by randomized choices. Leave blank for a fresh random edit; reusing the same seed with the same project/settings can help reproduce an edit, though changes in inputs or software can alter results',
            'Random seed (optional; same number = repeatable edit)':'Optional seed used by randomized choices. Leave blank for a fresh random edit; reusing the same seed with the same project/settings can help reproduce an edit, though changes in inputs or software can alter results',
            'Copy seed':'Copies the current seed value to the clipboard so you can save or reuse it later',
            'SCAN / UPDATE FOOTAGE LIBRARY':'Analyses videos in the selected footage folder and refreshes the cached clip information used to plan edits. Run this after adding, removing or changing footage',
            'CANCEL SCAN':'Requests that the active scan stops after the current file/process finishes',
            'EDIT HIGHLIGHT SCHEDULE…':'Open the optional highlight schedule editor. Enter one source filename and timestamp per line, separated by a comma. Example: Flight3, 00:02:14. Timestamps may be MM:SS or HH:MM:SS. Filename extensions are optional; match by filename stem (case-insensitive), with no folder path. Blank lines are ignored. For source videos longer than 12 seconds, the first and last 2 seconds are excluded from selections; highlight timestamps in those margins are moved into the usable range. Highlights are placed into the edit timeline where possible. The status tick means a schedule is saved, not that every entry has been checked against the footage yet',
            'EDIT MUSIC TRIM SCHEDULE…':'Optional music-section editor. Enter start and end timestamps, separated by a comma; one section per line. Example: 01:05, 01:35. Multiple sections are joined with 0.5-second crossfades. Trimmed music gets up to 2 seconds of buffer and 2-second fades at edit start/end; blank schedule uses the full track unchanged.',
            'GENERATE VIDEO':'Starts project analysis, clip selection, rendering, montage assembly and final encoding using the current settings',
            'GENERATE AGAIN':'Starts another edit using a new random seed so the randomized selection can differ. It does not change your saved settings',
            'GENERATE AGAIN (new random edit)':'Starts another edit using a new random seed so the randomized selection can differ. It does not change your saved settings',
            'CANCEL RENDER':'Requests cancellation of the current render. The active FFmpeg step may need to stop before the cancellation takes effect',
            'CHECK PROJECT':'Runs preflight checks on the selected footage, soundtrack, output path and FFmpeg setup before rendering. It does not render the video',
            'OPEN OUTPUT FOLDER':'Opens the folder containing the selected output path',
            'PLAY FINISHED VIDEO':'Opens the rendered output file if it exists',
            'COPY LOG / ERROR DETAILS':'Copies the timestamped status log and error details to the clipboard. Paste it into a message when reporting a problem'
        }
        for widget in self.root.winfo_children():
            self._tooltip_tree(widget,tips)
        # Give the highlight schedule button its dedicated format/use tooltip.
        self._attach_tooltip(self.highlight_schedule_button,tips['EDIT HIGHLIGHT SCHEDULE…'])
        self._attach_tooltip(self.music_trim_button,tips['EDIT MUSIC TRIM SCHEDULE…'])
    def _tooltip_tree(self,widget,tips):
        try:
            text=widget.cget('text')
            if text in tips:self._attach_tooltip(widget,tips[text])
            elif widget.winfo_class() in ('TCombobox','Entry','TEntry'):
                label=''
                try:
                    row=int(widget.grid_info().get('row',-1)); parent=widget.master
                    candidates=[]
                    for sibling in parent.winfo_children():
                        if sibling is widget:continue
                        if sibling.winfo_class() in ('TLabel','Label') and int(sibling.grid_info().get('row',-2))==row:
                            candidates.append((int(sibling.grid_info().get('column',0)),sibling.cget('text')))
                    if candidates:label=max(candidates,key=lambda item:item[0])[1]
                except Exception:pass
                desc=tips.get(label)
                if not desc:
                    desc={'TCombobox':'Select an option. Hover over its nearby label for more details.','Entry':'Enter or edit this value. Hover over its nearby label for more details.'}.get(widget.winfo_class())
                self._attach_tooltip(widget,desc)
        except Exception: pass
        try:
            for child in widget.winfo_children():self._tooltip_tree(child,tips)
        except Exception: pass
    def _attach_tooltip(self,widget,text):
        tip=tk.Toplevel(widget); tip.withdraw(); tip.overrideredirect(True)
        label=tk.Label(tip,text=text,justify='left',wraplength=360,background='#fffbd6',foreground='#222',relief='solid',borderwidth=1,padx=7,pady=5,font=('Segoe UI',9))
        label.pack()
        def show(event=None):
            try:tip.geometry(f'+{widget.winfo_rootx()+18}+{widget.winfo_rooty()+widget.winfo_height()+4}');tip.deiconify()
            except Exception:pass
        def hide(event=None):tip.withdraw()
        widget.bind('<Enter>',show,add='+');widget.bind('<Leave>',hide,add='+');widget.bind('<Button-1>',hide,add='+')
    def show_pc_info(self):
        # Show technical PC details in a separate window so they don't crowd the main editor.
        win=tk.Toplevel(self.root)
        win.title(f'TMC-FPV AutoEditor v{APP_VERSION} — About')
        win.transient(self.root)
        win.geometry('620x650')
        win.minsize(540,500)
        outer=ttk.Frame(win); outer.pack(fill='both',expand=True)
        about_canvas=tk.Canvas(outer,highlightthickness=0)
        about_scroll=ttk.Scrollbar(outer,orient='vertical',command=about_canvas.yview)
        about_canvas.configure(yscrollcommand=about_scroll.set)
        about_scroll.pack(side='right',fill='y'); about_canvas.pack(side='left',fill='both',expand=True)
        panel=ttk.Frame(about_canvas,padding=14); panel_window=about_canvas.create_window((0,0),window=panel,anchor='nw')
        panel.bind('<Configure>',lambda e:about_canvas.configure(scrollregion=about_canvas.bbox('all')))
        about_canvas.bind('<Configure>',lambda e:about_canvas.itemconfigure(panel_window,width=e.width))
        ttk.Label(panel,text='ABOUT TMC-FPV AutoEditor',font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(0,8))
        ttk.Label(panel,text=f'Editor build: TMC-FPV AutoEditor v{APP_VERSION}',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,8))
        brains=ttk.LabelFrame(panel,text='Intelligence systems',padding=8); brains.pack(fill='x',pady=(0,8))
        brain_items=[('Audio Brain · v0.2.7','Interprets pulse, phrases, accents, energy builds, drops, releases and editorial progressions. Cues add cut opportunities; beats are not mandatory cut points.\n\nDevelopment: offline music interpretation, iteratively refined and integrated into edit planning.'),('Vision Brain · v3 FPV heuristic','Adds local FPV event vocabulary: Flow, Building Motion, Motion Spike, Reveal/View Change, Reversal/Instability and Close-Pass Candidate. Labels use grayscale pixel/spatial-change proxies and confidence values; they are not semantic trick or gap recognition.\n\nDevelopment: offline temporal interpretation and Director-aware candidate scoring.'),(f'Director Engine · v{APP_VERSION}','Combines soundtrack context and footage evidence to select source moments, timing, narrative role, pacing, contrast and payoffs.\n\nDevelopment: music-led arcs, candidate scoring, source diversity, WOW reservations/payoffs and decision-report refinement.')]
        for title,tiptext in brain_items:
            ttk.Label(brains,text=title,font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(3,1))
            ttk.Label(brains,text=tiptext,wraplength=530,justify='left').pack(anchor='w',pady=(0,5))
        ttk.Label(panel,textvariable=self.hardware_summary,wraplength=510,justify='left').pack(anchor='w',fill='x')
        ttk.Label(panel,text='Render estimate',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(12,2))
        ttk.Label(panel,textvariable=self.estimate_summary,wraplength=510,justify='left').pack(anchor='w',fill='x')
        ttk.Label(panel,text='Work Edition uses CPU encoding (libx264) to avoid GPU encoder dependencies.',wraplength=510,justify='left').pack(anchor='w',pady=(12,0))
        ttk.Label(panel,text='Built through iterative development, repeated testing, real-footage evaluation and ongoing refinement.',wraplength=510,justify='left').pack(anchor='w',pady=(6,0))
        ttk.Button(panel,text='Close',command=win.destroy).pack(anchor='e',pady=(14,0))
        panel.update_idletasks(); about_canvas.configure(scrollregion=about_canvas.bbox('all'))
        self._theme_widget_tree(win,self.theme_colors)
        win.focus_set()
    def hardware_scan_async(self):
        threading.Thread(target=self._hardware_worker,daemon=True).start()
    def _hardware_worker(self):
        # Work Edition deliberately avoids GPU encoder probing and PowerShell/CIM calls.
        cpu=os.environ.get('PROCESSOR_IDENTIFIER','CPU information unavailable')
        ram='RAM information unavailable'; gpu='Hardware encoding disabled in Work Edition'
        self.active_encoder='libx264'; self.encoder_status='CPU-only Work Edition (libx264)'
        self.q.put(('hardware',f'CPU: {cpu}  |  {gpu}'))
        self.q.put(('encoder_info','Active video encoder: CPU-only Work Edition (libx264)'))
    def refresh_estimate(self,*_):
        try:
            folder=Path(self.folder.get().strip()); files=[]
            if folder.is_dir():files=[p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
            songdur=0.0
            songpath=self.song.get().strip()
            if songpath and Path(songpath).is_file() and self.ffmpeg_ready:
                try:songdur=self.probe_duration(songpath)
                except Exception:pass
            try:
                trim=self._parse_music_trim_schedule(self.music_trim_schedule)
                if trim and songpath and Path(trim[0][0] if False else songpath).is_file(): songdur=max(0.0,sum(e-a for a,e,_,_ in trim)-0.5*(len(trim)-1)+min(2.0,trim[0][0])+min(2.0,max(0.0,songdur-trim[-1][1])))
            except Exception: pass
            clips_guess=max(1,int(songdur/max(1.0,(float(self.min_len.get())+float(self.max_len.get()))/2))) if songdur else max(1,len(files)*4)
            # Broad, intentionally conservative heuristic; actual speed depends on source decode, filters, disk and codec.
            multiplier={'720p':1.0,'1080p':1.6,'1440p':2.7}.get(self.resolution.get(),1.6)
            fpsmult=1.0 if self.output_fps.get().startswith('30') else (1.45 if self.output_fps.get().startswith('50') else 1.65)
            qualitymult={'Standard (CRF 23)':0.8,'High (CRF 20)':1.0,'Very high (CRF 18)':1.35}.get(self.output_quality.get(),1.0)
            transitionsmult=1.18 if self.random_transitions.get() else 1.0
            cpu_factor=max(0.65,8/max(4,(os.cpu_count() or 8)))
            base=(clips_guess*2.8*cpu_factor*multiplier*fpsmult*qualitymult*transitionsmult)+(songdur*0.35*cpu_factor)
            low=max(1,base*0.65);high=max(low+1,base*1.9)
            disk_note='';
            try:
                outputpath=Path(self.output.get().strip()); probe_path=outputpath.parent if outputpath.parent.exists() else Path.home(); free=shutil.disk_usage(str(probe_path)).free/(1024**3); disk_note=f'  |  Free output disk: {free:.1f} GB'
            except Exception:pass
            self.estimate_summary.set(f'Estimated render time: about {self._fmt_time(low)}–{self._fmt_time(high)} (rough estimate)  |  {len(files)} source file(s) detected'+disk_note)
            self._estimate_base_sec=base;self._estimate_source_count=len(files)
        except Exception:
            self.estimate_summary.set('Estimated render time: select footage and music for an estimate')
    def _fmt_time(self,seconds):
        seconds=int(max(0,seconds));mins=seconds//60;hrs=mins//60;mins%=60
        return f'{hrs}h {mins}m' if hrs else (f'{mins}m' if mins else f'{seconds}s')
    def _stage_time_fmt(self,seconds):
        seconds=int(max(0,seconds)); h=seconds//3600; m=(seconds%3600)//60; sec=seconds%60
        return f'{h:02d}:{m:02d}:{sec:02d}'
    def _update_live_eta(self,completed,total):
        if not total or completed<=0:return
        elapsed=time.time()-getattr(self,'render_started',time.time())
        # Estimate from measured clip phase throughput; add a conservative allowance for assembly and final mux.
        per_clip=elapsed/max(1,completed)
        remain=max(0,total-completed)*per_clip
        remain+=max(20,remain*0.22)
        self.estimate_summary.set(f'Live render ETA: about {self._fmt_time(remain)} remaining  |  {completed}/{total} clips rendered (estimate improves as it runs)')
    def update_download_buttons(self,*_):
        dest=self.download_dest.get().strip(); url=self.download_url.get().strip(); valid=bool(dest and Path(dest).is_dir() and url)
        self.download_dest_label.configure(text='Destination: '+(dest or '(select a destination folder first)'))
        if self.source_kind.get()=='YouTube':
            self.download_btn.configure(state='normal' if valid and not self.running else 'disabled'); self.photos_open_btn.configure(state='disabled')
        else:
            self.download_btn.configure(state='disabled'); self.photos_open_btn.configure(state='normal' if valid and url and not self.running else 'disabled')
    def pick_download_folder(self):
        p=filedialog.askdirectory(title='Select destination for downloaded/imported footage')
        if p:
            self.download_dest.set(p)
            self.save_settings()
    def open_google_photos(self):
        url=self.download_url.get().strip(); dest=self.download_dest.get().strip()
        if not url or not Path(dest).is_dir():
            messagebox.showerror('Missing information','Paste a Google Photos shared link and select a valid destination folder first.'); return
        try:
            import webbrowser; webbrowser.open(url)
            messagebox.showinfo('Google Photos import',f'Google Photos link opened in your browser.\n\nUse the album menu / Download all. Save the ZIP to:\n{dest}\n\nThen extract its contents into that destination folder. Return here and use Stage 2 to scan the footage. Bulk downloading from shared albums is not reliably supported by yt-dlp, so this browser handoff is used rather than pretending the link can be downloaded directly.')
        except Exception as e: messagebox.showerror('Browser error',str(e))
    def edit_highlights(self):
        # Plain Notepad-style schedule editor. Changes are committed only with Accept.
        win=tk.Toplevel(self.root); win.title('TMC-FPV Auto Editor — Highlight Schedule')
        win.transient(self.root); win.geometry('620x420'); win.minsize(500,320); win.resizable(True,True)
        panel=ttk.Frame(win,padding=10); panel.pack(fill='both',expand=True); panel.columnconfigure(0,weight=1); panel.rowconfigure(2,weight=1)
        ttk.Label(panel,text='Enter one highlight per line:',font=('Segoe UI',10,'bold')).grid(row=0,column=0,sticky='w',pady=(0,5))
        ttk.Label(panel,text='Filename (extension optional), timestamp (MM:SS or HH:MM:SS) — example: Flight3, 00:02:14',foreground='#555').grid(row=1,column=0,sticky='w',pady=(0,5))
        text=tk.Text(panel,wrap='none',background='white',foreground='black',font=('Consolas',10),undo=True)
        text.grid(row=2,column=0,sticky='nsew'); text.insert('1.0',self.highlight_schedule)
        buttons=ttk.Frame(panel); buttons.grid(row=3,column=0,sticky='ew',pady=(8,0)); buttons.columnconfigure(0,weight=1); buttons.columnconfigure(1,weight=1)
        def accept():
            content=text.get('1.0','end-1c').strip()
            try: self._parse_highlight_schedule(content)
            except ValueError as e:
                messagebox.showerror('Highlight schedule format',str(e),parent=win); return
            self.highlight_schedule=content
            active=bool(content)
            self.highlight_status.set('✓ Schedule loaded' if active else 'No highlights scheduled')
            self.highlight_status_label.configure(foreground=('#17833b' if active else '#666'))
            self.save_settings(); win.destroy()
        action_group=ttk.Frame(buttons); action_group.grid(row=0,column=0,columnspan=2)
        ttk.Button(action_group,text='Cancel',command=win.destroy).pack(side='left',padx=4)
        ttk.Button(action_group,text='Accept',command=accept,style='Accent.TButton').pack(side='left',padx=4)
        self._theme_widget_tree(win,self.theme_colors)
        win.focus_set(); text.focus_set()
    @staticmethod
    def _timestamp_seconds(value):
        value=value.strip()
        parts=value.split(':')
        if len(parts) not in (2,3): raise ValueError('Timestamp must be MM:SS or HH:MM:SS.')
        try:
            nums=[float(x) for x in parts]
        except ValueError: raise ValueError('Timestamp contains non-numeric values.')
        if any(x<0 for x in nums) or nums[-1]>=60 or (len(nums)==3 and nums[1]>=60):
            raise ValueError('Timestamp is invalid. Use MM:SS or HH:MM:SS.')
        if len(nums)==2: return nums[0]*60+nums[1]
        return nums[0]*3600+nums[1]*60+nums[2]
    def edit_music_trim(self):
        # Bottom action row is fixed; only the text editor expands when resized.
        win=tk.Toplevel(self.root); win.title('TMC-FPV Auto Editor — Music Trim Schedule')
        win.transient(self.root); win.geometry('650x380'); win.minsize(520,300); win.resizable(True,True)
        panel=ttk.Frame(win,padding=10); panel.pack(fill='both',expand=True)
        panel.columnconfigure(0,weight=1); panel.rowconfigure(3,weight=1)
        ttk.Label(panel,text='Optional: choose section(s) of the selected music track',font=('Segoe UI',10,'bold')).grid(row=0,column=0,sticky='w',pady=(0,6))
        ttk.Label(panel,text='Enter start and end timestamps, separated by a comma. Use one line per section. Example: 01:05, 01:35',foreground='#555',wraplength=660).grid(row=1,column=0,sticky='w',pady=(0,6))
        ttk.Label(panel,text='Each line selects a section of the chosen track. Multiple lines are joined with short crossfades. Trimmed music gets automatic 2-second fades at the edit start and end; full-track audio remains untouched.',foreground='#555',wraplength=660).grid(row=2,column=0,sticky='w',pady=(0,8))
        text=tk.Text(panel,wrap='none',background='white',foreground='black',font=('Consolas',10),undo=True)
        text.grid(row=3,column=0,sticky='nsew'); text.insert('1.0',self.music_trim_schedule)
        buttons=ttk.Frame(panel); buttons.grid(row=4,column=0,sticky='ew',pady=(8,0)); buttons.columnconfigure(0,weight=1); buttons.columnconfigure(1,weight=1)
        def accept():
            content=text.get('1.0','end-1c').strip()
            try: self._parse_music_trim_schedule(content)
            except ValueError as e:
                messagebox.showerror('Music trim schedule format',str(e),parent=win); return
            self.music_trim_schedule=content
            active=bool(content)
            self.music_trim_status.set('Trim schedule saved' if active else 'Full track (untouched)')
            self.music_trim_status_label.configure(foreground=('#17833b' if active else '#666'))
            self.save_settings(); win.destroy()
        action_group=ttk.Frame(buttons); action_group.grid(row=0,column=0,columnspan=2)
        ttk.Button(action_group,text='Cancel',command=win.destroy).pack(side='left',padx=4)
        ttk.Button(action_group,text='Accept',command=accept,style='Accent.TButton').pack(side='left',padx=4)
        self._theme_widget_tree(win,self.theme_colors)
        win.focus_set(); text.focus_set()
    def _parse_music_trim_schedule(self,content):
        if not content.strip(): return None
        entries=[]
        for line_no,line in enumerate(content.splitlines(),1):
            line=line.strip()
            if not line: continue
            parts=[part.strip() for part in line.split(',')]
            if len(parts)!=2: raise ValueError(f'Line {line_no}: use Start, End (for example 01:05, 01:35).')
            start_text,end_text=parts
            try: start=self._timestamp_seconds(start_text); end=self._timestamp_seconds(end_text)
            except ValueError as e: raise ValueError(f'Line {line_no}: {e}')
            if end<=start: raise ValueError(f'Line {line_no}: end timestamp must be later than start.')
            if end-start<0.25: raise ValueError(f'Line {line_no}: section must be at least 0.25 seconds long.')
            entries.append((start,end,start_text,end_text))
        if not entries: return None
        return entries
    @staticmethod
    def _timestamp_seconds(value):
        value=value.strip()
        parts=value.split(':')
        if len(parts) not in (2,3): raise ValueError('Timestamp must be MM:SS or HH:MM:SS.')
        try:
            nums=[float(x) for x in parts]
        except ValueError: raise ValueError('Timestamp contains non-numeric values.')
        if any(x<0 for x in nums) or nums[-1]>=60 or (len(nums)==3 and nums[1]>=60):
            raise ValueError('Timestamp is invalid. Use MM:SS or HH:MM:SS.')
        if len(nums)==2: return nums[0]*60+nums[1]
        return nums[0]*3600+nums[1]*60+nums[2]
    def _parse_highlight_schedule(self,content):
        entries=[]
        for line_no,line in enumerate(content.splitlines(),1):
            line=line.strip()
            if not line: continue
            if ',' not in line: raise ValueError(f'Line {line_no}: use Filename, timestamp (for example Flight3, 00:02:14).')
            filename,timestamp=line.rsplit(',',1); filename=filename.strip()
            if not filename: raise ValueError(f'Line {line_no}: filename is missing.')
            try: seconds=self._timestamp_seconds(timestamp)
            except ValueError as e: raise ValueError(f'Line {line_no}: {e}')
            entries.append((filename,seconds,timestamp.strip()))
        return entries
    def save_settings(self):
        try:
            self.config_path.write_text(json.dumps({'footage_folder':self.folder.get().strip(),'song':self.song.get().strip(),'output':self.output.get().strip(),'highlight_schedule':self.highlight_schedule if hasattr(self,'highlight_schedule') else self.saved_settings.get('highlight_schedule',''),'music_trim_schedule':self.music_trim_schedule if hasattr(self,'music_trim_schedule') else self.saved_settings.get('music_trim_schedule',''),'mode':self.mode.get(),'single_source_order':self.single_source_order.get() if hasattr(self,'single_source_order') else self.saved_settings.get('single_source_order','Random'),'download_folder':self.download_dest.get().strip() if hasattr(self,'download_dest') else self.saved_settings.get('download_folder',''),'download_quality':self.download_quality.get() if hasattr(self,'download_quality') else self.saved_settings.get('download_quality','720p'),'output_resolution':self.resolution.get() if hasattr(self,'resolution') else self.saved_settings.get('output_resolution','720p'),'aspect_ratio':self.aspect_ratio.get() if hasattr(self,'aspect_ratio') else self.saved_settings.get('aspect_ratio','16:9 Landscape'),'output_quality':self.output_quality.get() if hasattr(self,'output_quality') else self.saved_settings.get('output_quality','High (CRF 20)'),'fade_in':self.fade_in.get() if hasattr(self,'fade_in') else False,'fade_out':self.fade_out.get() if hasattr(self,'fade_out') else False,'use_intro':self.use_intro.get() if hasattr(self,'use_intro') else False,'intro_path':self.intro_path.get() if hasattr(self,'intro_path') else self.saved_settings.get('intro_path',''),'intro_duration':self.intro_duration.get() if hasattr(self,'intro_duration') else self.saved_settings.get('intro_duration','2.0'),'random_transitions':self.random_transitions.get(),'artistic_mode':self.artistic_mode.get() if hasattr(self,'artistic_mode') else self.saved_settings.get('artistic_mode',False),'transition_strength':self.transition_strength.get(),'vertical_mode':self.vertical_mode.get() if hasattr(self,'vertical_mode') else self.saved_settings.get('vertical_mode','Original (fit)'), 'output_fps':self.output_fps.get() if hasattr(self,'output_fps') else self.saved_settings.get('output_fps','30 fps'),'turn_it_up':self.turn_it_up.get() if hasattr(self,'turn_it_up') else self.saved_settings.get('turn_it_up',False),'dark_mode':self.dark_mode.get() if hasattr(self,'dark_mode') else self.saved_settings.get('dark_mode',False)},indent=2),encoding='utf-8')
        except Exception as e: self.q.put(('log',f'Could not save settings: {e}'))
    def ensure_footage_folder(self):
        selected=self.folder.get().strip()
        if not selected:
            messagebox.showinfo('Select footage folder','Please select your footage folder using Browse before generating a video.')
            self.pick_folder()
            selected=self.folder.get().strip()
            if not selected: return None
        folder=Path(selected)
        if not folder.is_dir():
            messagebox.showerror('Invalid footage folder',f'The selected footage folder does not exist:\n{folder}\n\nPlease choose an existing folder containing your video footage.')
            return None
        self.save_settings(); return folder
    def start_download(self):
        url=self.download_url.get().strip(); folder=self.download_dest.get().strip()
        if self.source_kind.get()!='YouTube':
            self.open_google_photos(); return
        if not url: messagebox.showerror('Missing URL','Paste a YouTube video, playlist or channel URL first.'); return
        if not folder: messagebox.showerror('Missing destination','Select a download destination folder before downloading.'); return
        dest=Path(folder)
        if not dest.is_dir(): messagebox.showerror('Invalid destination',f'Destination folder does not exist:\n{dest}'); return
        exe=str(self.ytdlp_exe) if self.ytdlp_exe.is_file() else (shutil.which('yt-dlp') or shutil.which('yt-dlp.exe'))
        if not exe:
            messagebox.showerror('yt-dlp unavailable','yt-dlp has not been downloaded successfully yet. Please wait for startup setup to finish and try again.'); return
        self.save_settings(); self.running=True; self.job_type='download'; self.generate_btn.configure(state='disabled'); self.scan_btn.configure(state='disabled'); self.download_btn.configure(state='disabled'); self.progress.configure(mode='indeterminate'); self.progress.start(12); self.progress_text.set('Downloading from YouTube…')
        threading.Thread(target=self.download_worker,args=(exe,url,str(dest)),daemon=True).start()
    def download_worker(self,exe,url,folder):
        try:
            archive=os.path.join(folder,'yt-dlp_download_archive.txt')
            quality=self.download_quality.get() if hasattr(self,'download_quality') else '720p'
            cap={'480p':480,'720p':720,'1080p':1080}.get(quality)
            fmt=(f'bv[height<={cap}]/b[height<={cap}]' if cap else 'bv/b')
            cmd=[exe,'--ignore-errors','--download-archive',archive,'-f',fmt,'--merge-output-format','mkv','--newline','-o',os.path.join(folder,'%(title)s.%(ext)s'),url]
            self.q.put(('log',f'YouTube maximum quality: {quality}'))
            self.q.put(('log',f'DOWNLOAD DESTINATION (confirmed): {folder}'))
            self.q.put(('log','Starting yt-dlp. Playlist/channel URLs may queue multiple videos; archived items are skipped.'))
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',**self._no_console_kwargs()); self.download_proc=proc
            for line in proc.stdout:
                line=line.strip()
                if line:
                    self.q.put(('log',line))
                    import re
                    match=re.search(r'([0-9]+(?:\.[0-9]+)?)% of',line)
                    if match:self.q.put(('progress',float(match.group(1)),100,'Downloading '+Path(folder).name))
            code=proc.wait(); self.download_proc=None
            self.q.put(('log',f'yt-dlp finished with exit code {code}.'))
            self.q.put(('done',code==0))
        except Exception as e:self.download_proc=None; self.q.put(('log',f'Download error: {e}')); self.q.put(('done',False))
    def scan_library(self):
        folder=Path(self.folder.get().strip())
        if not folder.is_dir(): messagebox.showerror('Missing footage folder','Please select a valid footage folder first.'); return
        if self.running:return
        self.render_cancel.clear(); self.running=True; self.job_type='scan'; self.scan_cancel.clear(); self.generate_btn.configure(state='disabled'); self.scan_btn.configure(state='disabled'); self.download_btn.configure(state='disabled'); self.cancel_scan_btn.configure(state='normal'); self.progress.configure(mode='determinate',maximum=100,value=0); self.progress_text.set('Preparing scan…')
        threading.Thread(target=self.scan_worker,args=(str(folder),),daemon=True).start()
    def _path_row(self,parent,row,label,var,callback):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',padx=4,pady=5)
        ttk.Entry(parent,textvariable=var,width=44).grid(row=row,column=1,sticky='w',padx=4,pady=4)
        ttk.Button(parent,text='Browse…',command=callback).grid(row=row,column=2,padx=4,pady=5); parent.columnconfigure(1,weight=0)
    def apply_preset(self):
        preset=self.preset.get()
        presets={
            'FPV Action': {'mode':'FPV action / fast cuts','retro':False,'transitions':True,'min':'1.5','max':'4.0'},
            'Long Range': {'mode':'Story arc (recommended)','retro':False,'transitions':False,'min':'4.0','max':'8.0'},
            'Retro Camcorder': {'mode':'Retro documentary / long shots','retro':True,'transitions':False,'min':'5.0','max':'12.0'},
            'Music Video': {'mode':'Rhythm-focused','retro':False,'transitions':True,'min':'2.0','max':'6.0'}
        }
        if preset not in presets:return
        cfg=presets[preset]
        self.mode.set(cfg['mode']); self.retro.set(cfg['retro']); self.random_transitions.set(cfg['transitions'])
        self.min_len.set(cfg['min']); self.max_len.set(cfg['max']); self.save_settings()
        self._log(f'Preset applied: {preset}')
    def pick_intro(self):
        p=filedialog.askopenfilename(title='Select optional intro video or logo image',filetypes=[('Intro / logo media','*.mp4 *.mov *.mkv *.avi *.webm *.png *.jpg *.jpeg'),('All files','*.*')])
        if p:
            self.intro_path.set(p)
            if Path(p).suffix.lower() not in {'.png','.jpg','.jpeg'}:
                try:
                    duration=self.probe_duration(p); self.intro_duration.set(f'{duration:.3f}')
                except Exception: pass
            else:
                self.intro_duration.set(self.saved_settings.get('intro_duration','3.0'))
            self.use_intro.set(True); self.save_settings()
            self.save_settings()
    def pick_folder(self):
        p=filedialog.askdirectory(title='Select folder containing downloaded video footage'); self.folder.set(p) if p else None; self.save_settings()
    def pick_song(self):
        p=filedialog.askopenfilename(title='Select music track',filetypes=[('Audio','*.mp3 *.wav *.m4a *.aac *.flac *.ogg'),('All files','*.*')]); self.song.set(p) if p else None; self.save_settings()
    def pick_output(self):
        p=filedialog.asksaveasfilename(title='Save generated music video',defaultextension='.mp4',filetypes=[('MP4 video','*.mp4')]); self.output.set(p) if p else None; self.save_settings()
    def _log(self,msg):
        stamp=time.strftime('%H:%M:%S',time.localtime())
        self.log.configure(state='normal'); self.log.insert('end',f'[{stamp}] {msg}\n'); self.log.see('end'); self.log.configure(state='disabled')
    def copy_log(self):
        try:
            self.root.clipboard_clear(); self.root.clipboard_append(self.log.get('1.0','end-1c')); self.root.update()
            self.progress_text.set('Timestamped log copied to clipboard')
        except Exception as e: messagebox.showerror('Copy log failed',str(e))
    def _poll(self):
        try:
            while True:
                msg=self.q.get_nowait()
                if msg[0]=='log': self._log(msg[1])
                elif msg[0]=='hardware': self.hardware_summary.set(msg[1]); self._log('Hardware scan: '+msg[1])
                elif msg[0]=='encoder_info': self.hardware_summary.set(self.hardware_summary.get()+'  |  '+msg[1])
                elif msg[0]=='ffmpeg_ready':
                    if msg[1]: self.generate_btn.configure(state='normal'); self.generate_again_btn.configure(state='normal'); self.scan_btn.configure(state='normal'); self.progress_text.set('Ready — portable FFmpeg verified'); self.root.after(100,self.refresh_estimate)
                    else: self.progress_text.set('FFmpeg setup failed — see log')
                elif msg[0]=='progress':
                    _,value,total,status=msg; self.progress.configure(mode='determinate',maximum=max(1,total),value=value); self.progress_text.set(f'{status} — {100*value/max(1,total):.0f}%'); self._update_live_eta(value,total)
                elif msg[0]=='overall':
                    _,percent,status=msg; self.progress.stop(); self.progress.configure(mode='determinate',maximum=100,value=max(0,min(100,percent))); self.progress_text.set(f'{status} — {percent:.0f}%')
                    if getattr(self,'_storyboard_progress_active',False): self._update_storyboard_progress(percent,status)
                elif msg[0]=='assembly_status': self.progress_text.set(msg[1])
                elif msg[0]=='storyboard':
                    _,segments,usable,evt=msg
                    try: self._storyboard_open_failed=False; self.open_storyboard(segments,usable,evt)
                    except Exception as drawer_exc: self._storyboard_open_failed=True; self._log(f'FATAL: Storyboard drawer failed; render gate remains closed: {drawer_exc}'); evt.set()
                elif msg[0]=='storyboard_thumb':
                    _,idx,path=msg
                    try:
                        photo=tk.PhotoImage(file=str(path)) if path and Path(path).exists() else None
                        widgets=getattr(self,'_storyboard_render_cards',[])
                        if idx<len(widgets) and photo:
                            label=widgets[idx]
                            label.configure(image=photo,text=''); label.image=photo
                            getattr(self,'_storyboard_render_images',{})[idx]=photo
                    except Exception as thumb_exc: self._log(f'Storyboard thumbnail update failed for clip {idx+1}: {thumb_exc}')
                elif msg[0]=='stage_summary':
                    parts=msg[1]; self.last_stage_summary=parts; self._log('STAGE TIMINGS — '+ ' | '.join(f'{name}: {self._stage_time_fmt(seconds)}' for name,seconds in parts))
                elif msg[0]=='done':
                    job=self.job_type
                    self.running=False; self._storyboard_progress_active=False; self.storyboard_drawer.pack_forget(); self.storyboard_toggle.configure(text='＋  Storyboard preview (review and replace clips)',state='normal'); self.progress.stop(); self.progress.configure(mode='determinate',maximum=100,value=100 if msg[1] else 0); self.cancel_scan_btn.configure(state='disabled'); self.cancel_render_btn.configure(state='disabled'); self.generate_btn.configure(state='normal' if self.ffmpeg_ready else 'disabled'); self.generate_again_btn.configure(state='normal' if self.ffmpeg_ready else 'disabled'); self.scan_btn.configure(state='normal' if self.ffmpeg_ready else 'disabled'); self.update_download_buttons(); self.progress_text.set('Completed' if msg[1] else ('Render cancelled' if self.render_cancel.is_set() else 'Stopped / failed'))
                    if msg[1] and job=='generate':
                        try:
                            outp=Path(self.output.get()); size_mb=outp.stat().st_size/(1024*1024); elapsed=time.time()-getattr(self,'render_started',time.time()); duration=self.probe_duration(str(outp)) if self.ffmpeg_ready else 0
                            stage_text='\n'.join(f'  {name}: {self._stage_time_fmt(seconds)}' for name,seconds in getattr(self,'last_stage_summary',[]))
                            summary=f'Video created successfully\n\nDuration: {duration:.1f}s\nFile size: {size_mb:.1f} MB\nRender time: {elapsed/60:.1f} minutes\n\nStage timings:\n{stage_text}\n\nOutput: {outp}'
                        except Exception: summary=f'Video created successfully:\n{self.output.get()}'
                        messagebox.showinfo('Finished',summary)
                    elif msg[1] and job=='scan': messagebox.showinfo('Library scan complete','Footage index created or updated. You can now generate videos.')
                    elif msg[1] and job=='download': messagebox.showinfo('Download complete','Download process completed. New footage is ready to scan into your library.')
                    elif job=='scan' and self.scan_cancel.is_set(): messagebox.showinfo('Scan cancelled','Scan stopped safely. Cached and completed entries were retained.')
                    elif job=='generate' and self.render_cancel.is_set(): messagebox.showinfo('Render cancelled','Rendering was stopped. Temporary files have been cleaned up.')
                    else: messagebox.showerror('Operation failed','See the log for the error details.')
        except queue.Empty: pass
        self.root.after(150,self._poll)
    def _start_storyboard_progress(self):
        """Show a live, lightweight musical-arc progress view while the Director builds the edit."""
        self._storyboard_progress_active=True
        panel=self.storyboard_drawer
        colors=getattr(self,'theme_colors',{'bg':'#25282B','panel':'#34383C','fg':'#F0F2F4','muted':'#C6CBD0','accent':'#FF9800','border':'#555B60'})
        for child in panel.winfo_children(): child.destroy()
        panel.configure(bg=colors['bg'])
        tk.Label(panel,text='DIRECTOR  ·  BUILDING YOUR EDIT',bg=colors['bg'],fg=colors['fg'],font=('Segoe UI',12,'bold')).pack(anchor='w',padx=10,pady=(8,2))
        self._storyboard_progress_status=tk.StringVar(value='Reading music and planning the edit…')
        tk.Label(panel,textvariable=self._storyboard_progress_status,bg=colors['bg'],fg=colors['muted'],font=('Segoe UI',9)).pack(anchor='w',padx=10,pady=(0,6))
        cv=tk.Canvas(panel,height=86,bg=colors['bg'],highlightthickness=0)
        cv.pack(fill='x',padx=10,pady=(0,8))
        sections=['BREATHING SPACE','FLOW','BUILD','PEAKS / WOW','FINALE']
        cv.update_idletasks(); width=max(500,cv.winfo_width()); margin=8; usable=width-2*margin; gap=5; bw=(usable-gap*(len(sections)-1))/len(sections
        )
        self._storyboard_progress_canvas=cv; self._storyboard_progress_sections=[]; self._storyboard_progress_marker=None; self._storyboard_progress_dot=None
        for i,name in enumerate(sections):
            x=margin+i*(bw+gap)
            cv.create_rectangle(x,22,x+bw,70,fill=colors['panel'],outline=colors['border'],width=1)
            cv.create_text(x+bw/2,46,text=name,fill=colors['muted'],font=('Segoe UI',8,'bold'),width=bw-4)
            self._storyboard_progress_sections.append((x,bw))
        x0=margin; x1=margin+usable
        self._storyboard_progress_marker=cv.create_line(x0,14,x0,76,fill=colors['accent'],width=3)
        self._storyboard_progress_dot=cv.create_oval(x0-4,9,x0+4,17,fill=colors['accent'],outline=colors['accent'])
        self._storyboard_progress_range=(x0,x1)
        self.storyboard_toggle.configure(text='DIRECTOR IS WORKING  ·  STORYBOARD PROGRESS',state='disabled')
        if not panel.winfo_manager(): panel.pack(fill='x',pady=(0,8),before=self.estimate_summary_label)
        self.root.update_idletasks()
        self._update_storyboard_progress(3,'Starting up')
    def _update_storyboard_progress(self,percent,status):
        if not getattr(self,'_storyboard_progress_active',False): return
        # The Director planning phase spans roughly 3–35% of the existing pipeline.
        normalized=max(0,min(100,(float(percent)-3.0)/(35.0-3.0)*100.0))
        cv=getattr(self,'_storyboard_progress_canvas',None); marker=getattr(self,'_storyboard_progress_marker',None)
        if cv is not None and marker is not None:
            x0,x1=self._storyboard_progress_range; x=x0+(x1-x0)*normalized/100.0
            cv.coords(marker,x,14,x,76)
            dot=getattr(self,'_storyboard_progress_dot',None)
            if dot is not None: cv.coords(dot,x-4,9,x+4,17)
        statusvar=getattr(self,'_storyboard_progress_status',None)
        if statusvar is not None: statusvar.set(f'{status}  ·  Director progress {normalized:.0f}%')

    def _storyboard_frame(self,src,start,duration,size='420x236'):
        """Extract a representative frame for the Storyboard using the bundled FFmpeg."""
        cache=getattr(self,'_storyboard_cache_dir',None)
        if cache is None:
            cache=Path(tempfile.mkdtemp(prefix='tmcfpv_storyboard_')); self._storyboard_cache_dir=cache
        key=re.sub(r'[^A-Za-z0-9]+','_',Path(src).stem)[:32]+f'_{int(start*10)}_{int(duration*10)}_{size.replace("x","_")}.png'
        out=cache/key
        if not out.exists():
            seek=max(0.0,float(start)+max(0.0,float(duration))*0.5)
            try:
                subprocess.run([self._ffmpeg_exe(),'-hide_banner','-loglevel','error','-ss',f'{seek:.3f}','-i',src,'-frames:v','1','-vf',f'scale={size.replace("x",":")}:force_original_aspect_ratio=decrease','-y',str(out)],capture_output=True,timeout=20,**self._no_console_kwargs())
            except Exception: pass
        return out if out.exists() else None
    def _storyboard_open_source(self,src,start,duration=None):
        """Create and open a short preview beginning 1.5s before the selected edit segment."""
        try:
            start=max(0.0,float(start)); clip_dur=max(0.1,float(duration or 3.0))
            preview_start=max(0.0,start-1.5)
            preview_length=clip_dur+(start-preview_start)
            cache=getattr(self,'_storyboard_preview_dir',None)
            if cache is None:
                cache=Path(tempfile.mkdtemp(prefix='tmcfpv_clip_preview_')); self._storyboard_preview_dir=cache
            out=cache/(f'preview_{int(time.time()*1000)}.mp4')
            cmd=[self._ffmpeg_exe(),'-hide_banner','-loglevel','error','-ss',f'{preview_start:.3f}','-i',src,'-t',f'{preview_length:.3f}','-vf',"scale=w='if(gt(iw,ih),960,-2)':h='if(gt(ih,iw),960,-2)',scale=trunc(iw/2)*2:trunc(ih/2)*2",'-c:v','libx264','-preset','ultrafast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','-y',str(out)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=90,**self._no_console_kwargs())
            if result.returncode!=0 or not out.exists() or out.stat().st_size==0:
                raise RuntimeError((result.stderr or 'FFmpeg failed to create preview clip')[-1200:])
            os.startfile(str(out))
            self._log(f'Storyboard preview created: {Path(src).name}; starts {preview_start:.2f}s (1.5s pre-roll where available), then selected {start:.2f}-{start+clip_dur:.2f}s segment.')
        except Exception as e:
            messagebox.showerror('Preview failed',str(e))
    def _toggle_storyboard_drawer(self):
        panel=getattr(self,'storyboard_drawer',None)
        button=getattr(self,'storyboard_toggle',None)
        if panel is None or button is None: return
        if panel.winfo_manager():
            # Hiding the drawer is purely a view operation. It NEVER approves the edit
            # or releases the render gate; the user can reopen it at any time.
            panel.pack_forget()
            button.configure(text='＋  Storyboard preview (reopen review)')
        else:
            panel.pack(fill='x',pady=(0,8),before=self.estimate_summary_label)
            button.configure(text='－  Storyboard preview (hide review panel)')

    def open_storyboard(self,segments,usable,review_event=None):
        """Embedded Storyboard drawer: review and replace clips in the main AutoEditor window."""
        if not segments: return
        self._storyboard_progress_active=False
        self._storyboard_review_event=review_event
        colors=getattr(self,'theme_colors',{'bg':'#25282B','panel':'#34383C','fg':'#F0F2F4','muted':'#C6CBD0','accent':'#FF9800','border':'#555B60'})
        panel=self.storyboard_drawer
        # Clear previous drawer contents while preserving the panel itself.
        for child in panel.winfo_children(): child.destroy()
        panel.configure(bg=colors['bg'])
        top=tk.Frame(panel,bg=colors['bg']); top.pack(fill='x',padx=8,pady=(6,4))
        total=sum(float(x[2]) for x in segments); unique=len(set(x[0] for x in segments))
        tk.Label(top,text=f'STORYBOARD   {len(segments)} clips  ·  {total:.1f}s  ·  {unique} sources',bg=colors['bg'],fg=colors['fg'],font=('Segoe UI',12,'bold')).pack(side='left')
        # Ribbon of thumbnail cards, horizontally scrollable.
        ribbonframe=tk.Frame(panel,bg=colors['bg']); ribbonframe.pack(fill='x',padx=8,pady=6)
        canvas=tk.Canvas(ribbonframe,height=158,bg=colors['panel'],highlightthickness=1,highlightbackground=colors['border'])
        hbar=tk.Scrollbar(ribbonframe,orient='horizontal',command=canvas.xview); canvas.configure(xscrollcommand=hbar.set)
        canvas.pack(fill='x'); hbar.pack(fill='x')
        cards=tk.Frame(canvas,bg=colors['panel']); cards_window=canvas.create_window((0,0),window=cards,anchor='nw')
        selected={'i':0}; image_refs={}; card_widgets=[]; render_thumb_labels=[]
        for i,(src,start,dur) in enumerate(segments):
            card=tk.Frame(cards,bg=colors['panel'],highlightthickness=2,highlightbackground=colors['border'],width=226,height=148); card.pack(side='left',padx=4,pady=4); card.pack_propagate(False)
            lbl=tk.Label(card,text='Loading source frame…',bg=colors['panel'],fg=colors['muted']); lbl.pack(fill='x',padx=4,pady=(3,0))
            render_thumb_labels.append(lbl)
            tk.Label(card,text=f'{i+1:02d}  ·  {dur:.1f}s',bg=colors['panel'],fg=colors['fg'],font=('Segoe UI',9,'bold')).pack()
            for w in (card,)+tuple(card.winfo_children()): w.bind('<Button-1>',lambda e,idx=i:select_clip(idx))
            card_widgets.append(card)
        self._storyboard_render_cards=render_thumb_labels; self._storyboard_render_images={}
        # Pre-render-review thumbnails are extracted from ORIGINAL source footage, not rendered clips.
        # They are ready before the user can approve and before the render worker starts.
        for ti,(tsrc,tstart,tdur) in enumerate(segments):
            try:
                source_thumb=self._storyboard_frame(tsrc,tstart,tdur,'200x112')
                source_photo=tk.PhotoImage(file=str(source_thumb)) if source_thumb and Path(source_thumb).exists() else None
                if source_photo:
                    render_thumb_labels[ti].configure(image=source_photo,text=''); render_thumb_labels[ti].image=source_photo
                    self._storyboard_render_images[ti]=source_photo
                else: render_thumb_labels[ti].configure(text='Source thumbnail unavailable')
            except Exception as thumb_exc:
                render_thumb_labels[ti].configure(text='Source thumbnail unavailable')
                self._log(f'Source storyboard thumbnail failed for clip {ti+1}: {thumb_exc}')
        cards.update_idletasks(); canvas.itemconfigure(cards_window,width=max(cards.winfo_reqwidth(),1),height=max(cards.winfo_reqheight(),1)); canvas.configure(scrollregion=canvas.bbox('all'))
        cards.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        main=tk.Frame(panel,bg=colors['bg']); main.pack(fill='both',expand=True,padx=8,pady=6)
        previewbox=tk.Frame(main,bg=colors['panel'],highlightthickness=1,highlightbackground=colors['border']); previewbox.pack(side='left',fill='both',expand=True,padx=(0,4))
        preview=tk.Label(previewbox,bg=colors['panel'],fg=colors['muted'],text='Select a clip',font=('Segoe UI',11)); preview.pack(fill='both',expand=True,padx=8,pady=8)
        info=tk.Frame(main,bg=colors['panel']); info.pack(side='right',fill='both',expand=True,padx=(4,0))
        title=tk.Label(info,text='',bg=colors['panel'],fg=colors['fg'],font=('Segoe UI',12,'bold'),wraplength=240); title.pack(anchor='w',padx=12,pady=(12,4))
        details=tk.Label(info,text='',bg=colors['panel'],fg=colors['muted'],font=('Segoe UI',10),justify='left',wraplength=240); details.pack(anchor='w',padx=12,pady=5)
        previewbtn=tk.Button(info,text='▶  Play selected clip',bg=colors['panel'],fg=colors['fg'],command=lambda:self._storyboard_open_source(segments[selected['i']][0],segments[selected['i']][1],segments[selected['i']][2])); previewbtn.pack(fill='x',padx=12,pady=(12,5))
        replacebtn=tk.Button(info,text='REPLACE CLIP',bg=colors['accent'],fg='#202020',font=('Segoe UI',10,'bold'),command=lambda:replace_clip()); replacebtn.pack(fill='x',padx=12,pady=5)
        tk.Label(panel,text='Review clips, make replacements, and use the arrow keys to navigate. Hiding this panel does not approve or start rendering.',bg=colors['bg'],fg=colors['muted'],font=('Segoe UI',9,'italic')).pack(anchor='w',padx=8,pady=(0,6))
        approvalrow=tk.Frame(panel,bg=colors['bg']); approvalrow.pack(fill='x',padx=8,pady=(4,8))
        approvebtn=tk.Button(approvalrow,text='APPROVE STORYBOARD  ·  CONTINUE TO RENDER',bg=colors['accent'],fg='#202020',font=('Segoe UI',10,'bold'),command=lambda:approve_review())
        approvebtn.pack(fill='x')
        def approve_review():
            evt=getattr(self,'_storyboard_review_event',None)
            if evt is not None:
                approvebtn.configure(state='disabled',text='STORYBOARD APPROVED  ·  CONTINUING…')
                evt.set()
        def select_clip(i):
            selected['i']=i; src,start,dur=segments[i]
            for j,c in enumerate(card_widgets): c.configure(highlightbackground=colors['accent'] if j==i else colors['border'])
            frame=self._storyboard_frame(src,start,dur,'700x394')
            # Refresh the ribbon card too, so replacements are reflected in the plan itself.
            try:
                ribbon_frame=self._storyboard_frame(src,start,dur,'200x112')
                ribbon_photo=tk.PhotoImage(file=str(ribbon_frame)) if ribbon_frame and Path(ribbon_frame).exists() else None
                if ribbon_photo:
                    render_thumb_labels[i].configure(image=ribbon_photo,text=''); render_thumb_labels[i].image=ribbon_photo
                    self._storyboard_render_images[i]=ribbon_photo
            except Exception as ribbon_exc: self._log(f'Replacement ribbon thumbnail failed for clip {i+1}: {ribbon_exc}')
            try:
                ph=tk.PhotoImage(file=str(frame)) if frame else None
                if ph: preview.configure(image=ph,text=''); preview.image=ph
                else: preview.configure(image='',text='Preview frame unavailable')
            except Exception: preview.configure(image='',text='Preview frame unavailable')
            title.configure(text=f'CLIP {i+1:02d}'); details.configure(text=f'Source: {Path(src).name}\nSource position: {start:.2f}s\nDuration: {dur:.2f}s\nTimeline position: {sum(float(x[2]) for x in segments[:i]):.2f}s')
            previewbtn.configure(command=lambda:self._storyboard_open_source(src,start,dur))
            canvas.update_idletasks()
        def replace_clip():
            i=selected['i']; oldsrc,oldstart,dur=segments[i]
            others=[(f,d,score) for f,d,score in usable if f!=oldsrc and d>dur+0.05]
            if not others:
                messagebox.showinfo('Replace clip','No alternative sources are long enough for this clip.'); return
            rng=random.Random(); rng.shuffle(others); candidates=[]
            for src,d,score in others:
                low,high=(2.0,max(2.0,d-2.0)) if d>12 else (0.0,d)
                if high-low<dur: continue
                st=rng.uniform(low,max(low,high-dur)); candidates.append((src,st,dur))
                if len(candidates)>=3: break
            if not candidates:
                messagebox.showinfo('Replace clip','Could not find replacement windows with enough usable footage.'); return
            dlg=tk.Toplevel(self.root); dlg.title('Choose replacement'); dlg.geometry('800x390'); dlg.transient(self.root); dlg.configure(bg=colors['bg'])
            tk.Label(dlg,text='Choose a replacement — preview the actual footage before accepting',bg=colors['bg'],fg=colors['fg'],font=('Segoe UI',11,'bold')).pack(pady=10)
            row=tk.Frame(dlg,bg=colors['bg']); row.pack(fill='both',expand=True,padx=8); thumbs=[]
            for k,(src,st,ln) in enumerate(candidates):
                cell=tk.Frame(row,bg=colors['panel']); cell.pack(side='left',fill='both',expand=True,padx=5)
                thumb=self._storyboard_frame(src,st,ln,'210x118')
                try: ph=tk.PhotoImage(file=str(thumb)) if thumb else None
                except Exception: ph=None
                thumbs.append(ph)
                if ph: lab=tk.Label(cell,image=ph,bg=colors['panel']); lab.image=ph; lab.pack(padx=5,pady=5)
                tk.Label(cell,text=f'{Path(src).name}\nSource @ {st:.1f}s\n{ln:.1f}s',bg=colors['panel'],fg=colors['fg'],wraplength=220).pack(pady=5)
                tk.Button(cell,text='▶ Preview',bg=colors['panel'],fg=colors['fg'],command=lambda f=src,t=st:self._storyboard_open_source(f,t)).pack(fill='x',padx=5,pady=3)
                tk.Button(cell,text='Use this clip',bg=colors['accent'],fg='#202020',command=lambda candidate=candidates[k]:accept(candidate,dlg)).pack(fill='x',padx=5,pady=(3,8))
            def accept(candidate,d):
                segments[i]=candidate; d.destroy(); select_clip(i)
                self._log(f'STORYBOARD: clip {i+1} replaced with {Path(candidate[0]).name} at {candidate[1]:.2f}s.')
            tk.Button(dlg,text='Cancel',bg=colors['panel'],fg=colors['fg'],command=dlg.destroy).pack(pady=8)
        def storyboard_key(event,delta):
            if not panel.winfo_manager(): return None
            try:
                focus=self.root.focus_get()
                if isinstance(focus,(tk.Entry,tk.Text,ttk.Entry,ttk.Combobox)): return None
            except Exception: pass
            nxt=max(0,min(len(segments)-1,selected['i']+delta))
            if nxt!=selected['i']:
                select_clip(nxt)
                # Scroll selected card into view in the horizontal ribbon.
                cards.update_idletasks(); canvas.configure(scrollregion=canvas.bbox('all'))
                denom=max(1,len(segments)-1); canvas.xview_moveto(nxt/denom)
            return 'break'
        self.root.bind_all('<Left>',lambda e:storyboard_key(e,-1))
        self.root.bind_all('<Right>',lambda e:storyboard_key(e,1))
        select_clip(0)
        # Drawer starts expanded. Hiding is not approval; the explicit approve button
        # is the ONLY action that releases the render review gate.
        if not panel.winfo_manager(): panel.pack(fill='x',pady=(0,8),before=self.estimate_summary_label)
        self.storyboard_toggle.configure(text='－  Storyboard preview (hide review panel)',state='normal')
        self.root.update_idletasks()

    def open_output_folder(self):
        try:
            out=Path(self.output.get().strip()); folder=out.parent
            if not folder.exists(): messagebox.showinfo('Output folder',f'Folder does not exist yet:\n{folder}'); return
            os.startfile(str(folder))
        except Exception as e: messagebox.showerror('Open folder error',str(e))
    def play_output(self):
        try:
            out=Path(self.output.get().strip())
            if not out.is_file(): messagebox.showinfo('Video not found',f'No output video found yet:\n{out}'); return
            os.startfile(str(out))
        except Exception as e: messagebox.showerror('Play video error',str(e))
    def preflight(self,show=True):
        issues=[]; folder=Path(self.folder.get().strip()); song=Path(self.song.get().strip()); out=Path(self.output.get().strip())
        if not folder.is_dir(): issues.append('Footage folder is missing or invalid.')
        else:
            count=sum(1 for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in VIDEO_EXTS)
            if count==0: issues.append('No supported video files were found in the footage folder.')
        if not song.is_file(): issues.append('Music file is missing or invalid.')
        if not out.name.lower().endswith('.mp4'): issues.append('Output filename should end in .mp4.')
        
        if self.use_intro.get() and self.intro_path.get().strip() and not Path(self.intro_path.get().strip()).is_file(): issues.append('Selected intro/logo file cannot be found.')
        try: mn=float(self.min_len.get()); mx=float(self.max_len.get())
        except: issues.append('Clip lengths must be numeric.'); mn=0; mx=0
        if mn<=0 or mx<mn: issues.append('Clip length minimum/maximum values are invalid.')
        if self.seed.get().strip():
            try: int(self.seed.get().strip())
            except: issues.append('Seed must be a whole number or left blank for automatic randomness.')
        if not self.ffmpeg_ready: issues.append('Portable FFmpeg is not yet verified.')
        msg=('Project check found issues:\n\n• '+'\n• '.join(issues)) if issues else 'Project check passed. Footage, music, output settings and portable FFmpeg look ready.'
        if show: messagebox.showwarning('Project check',msg) if issues else messagebox.showinfo('Project check',msg)
        self._log(('Pre-flight check: issues found — ' if issues else 'Pre-flight check passed — ')+('; '.join(issues) if issues else 'paths and settings look valid'))
        return not issues
    def _ffmpeg_exe(self): return str(self.ffmpeg_dir/'ffmpeg.exe')
    def _localize_cmd(self,cmd):
        if cmd and cmd[0]=='ffmpeg':
            cmd=list(cmd); cmd[0]=self._ffmpeg_exe()
        return cmd
    def ensure_ytdlp_async(self):
        threading.Thread(target=self._ytdlp_setup_worker,daemon=True).start()
    def _ytdlp_setup_worker(self):
        try:
            self.ytdlp_dir.mkdir(parents=True,exist_ok=True)
            if self.ytdlp_exe.exists() and self.ytdlp_exe.stat().st_size>1024:
                self.q.put(('log','yt-dlp verified in application yt-dlp folder.'))
                return
            import urllib.request
            temp_path=self.ytdlp_dir/'yt-dlp.download.tmp'
            self.q.put(('log','yt-dlp missing. Downloading official yt-dlp executable automatically…'))
            urllib.request.urlretrieve(self.ytdlp_url,str(temp_path))
            if not temp_path.exists() or temp_path.stat().st_size<1024:
                raise RuntimeError('Downloaded yt-dlp file is missing or unexpectedly small.')
            temp_path.replace(self.ytdlp_exe)
            self.q.put(('log','yt-dlp download and verification complete. YouTube downloads are ready.'))
        except Exception as e:
            try:
                temp_path=self.ytdlp_dir/'yt-dlp.download.tmp'
                if temp_path.exists(): temp_path.unlink()
            except Exception: pass
            self.q.put(('log','Automatic yt-dlp setup failed: '+str(e)))
            self.q.put(('log','YouTube download feature will remain unavailable until startup setup succeeds.'))
    def ensure_ffmpeg_async(self):
        threading.Thread(target=self._ffmpeg_setup_worker,daemon=True).start()
    def _ffmpeg_setup_worker(self):
        try:
            self.ffmpeg_dir.mkdir(parents=True,exist_ok=True)
            ff=self.ffmpeg_dir/'ffmpeg.exe'
            if not ff.exists():
                import urllib.request
                zip_path=self.ffmpeg_dir.parent/'ffmpeg_download.zip'
                self.q.put(('log','FFmpeg missing from application folder. Downloading portable FFmpeg essentials…'))
                def reporthook(blocknum, blocksize, totalsize):
                    if totalsize>0:
                        pct=min(100,blocknum*blocksize*100/totalsize)
                        self.q.put(('overall',pct,'Downloading portable FFmpeg'))
                urllib.request.urlretrieve(self.ffmpeg_zip_url,str(zip_path),reporthook=reporthook)
                self.q.put(('log','FFmpeg download complete. Extracting local binaries…'))
                with zipfile.ZipFile(zip_path) as z:
                    names=z.namelist()
                    ff_member=next((n for n in names if n.lower().endswith('/bin/ffmpeg.exe')),None)
                    if not ff_member: raise RuntimeError('Downloaded FFmpeg archive did not contain ffmpeg.exe.')
                    bin_prefix=ff_member.rsplit('ffmpeg.exe',1)[0]
                    members=[m for m in names if m.startswith(bin_prefix) and not m.endswith('/') and not m.lower().endswith('ffprobe.exe')]
                    for idx,member in enumerate(members,1):
                        target=self.ffmpeg_dir/Path(member).name
                        with z.open(member) as src, open(target,'wb') as dst: shutil.copyfileobj(src,dst)
                        self.q.put(('overall',min(99,idx*100/max(1,len(members))),'Extracting FFmpeg files'))
                try: zip_path.unlink()
                except: pass
            filters=subprocess.run([str(ff),' -hide_banner'.strip(),'-filters'],capture_output=True,text=True,timeout=30,**self._no_console_kwargs())
            if filters.returncode!=0: raise RuntimeError('Bundled FFmpeg failed its startup check.')
            if not any('xfade' in line.split() for line in filters.stdout.splitlines()): raise RuntimeError('Bundled FFmpeg is installed but does not expose xfade.')
            enc=subprocess.run([str(ff),'-hide_banner','-encoders'],capture_output=True,text=True,timeout=15,**self._no_console_kwargs()).stdout.lower()
            # Test encoders with a tiny real encode, not merely presence in the encoder list.
            candidates=[('h264_amf','AMD AMF'),('h264_nvenc','NVIDIA NVENC'),('h264_qsv','Intel Quick Sync')]
            selected='libx264'; status='CPU fallback (libx264)'
            for codec,label in candidates:
                if codec not in enc: continue
                testcmd=[str(ff),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc=size=160x120:rate=30:duration=0.4','-frames:v','8','-an','-c:v',codec]
                if codec=='h264_amf': testcmd += ['-quality','balanced']
                elif codec=='h264_nvenc': testcmd += ['-preset','p4']
                elif codec=='h264_qsv': testcmd += ['-preset','medium']
                testcmd += ['-f','null','-']
                try:
                    testres=subprocess.run(testcmd,capture_output=True,text=True,timeout=15,**self._no_console_kwargs())
                    if testres.returncode==0:
                        selected=codec; status=f'{label} selected (startup encode test passed)'; break
                    else:
                        self.q.put(('log',f'{label} startup test failed; trying next encoder.'))
                except Exception as probe_error:
                    self.q.put(('log',f'{label} startup test could not complete: {probe_error}; trying next encoder.'))
            self.active_encoder=selected; self.encoder_status=status
            encnote='Active video encoder: '+status
            self.ffmpeg_ready=True; self.q.put(('overall',100,'FFmpeg setup complete')); self.q.put(('log','Portable FFmpeg verified: xfade filter available. App will use its local FFmpeg binaries.')); self.q.put(('log',encnote)); self.q.put(('encoder_info',encnote)); self.q.put(('ffmpeg_ready',True))
        except Exception as e:
            self.ffmpeg_ready=False; self.q.put(('log','FFmpeg setup failed: '+str(e))); self.q.put(('ffmpeg_ready',False))
    def video_encoder_args(self,crf):
        # Work Edition uses CPU encoding for maximum compatibility on managed PCs.
        return ['-c:v','libx264','-preset','medium','-crf',str(crf)]

    def run_render_process(self,cmd,**kwargs):
        if self.render_cancel.is_set(): raise RuntimeError('RENDER_CANCELLED')
        cmd=self._localize_cmd(cmd)
        capture=kwargs.get('capture_output',False); out_target=subprocess.PIPE if capture else kwargs.get('stdout',subprocess.DEVNULL); err_target=subprocess.PIPE if capture else kwargs.get('stderr',subprocess.PIPE); textmode=kwargs.get('text',False); proc=subprocess.Popen(cmd,stdout=out_target,stderr=err_target,text=textmode,encoding=kwargs.get('encoding','utf-8') if textmode else None,errors=kwargs.get('errors','replace') if textmode else None,**self._no_console_kwargs())
        self.render_proc=proc
        try:
            while proc.poll() is None:
                if self.render_cancel.is_set():
                    try: proc.terminate()
                    except: pass
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                    raise RuntimeError('RENDER_CANCELLED')
                time.sleep(0.15)
            out,err=proc.communicate()
            if proc.returncode: raise subprocess.CalledProcessError(proc.returncode,cmd,output=out,stderr=err)
            return subprocess.CompletedProcess(cmd,proc.returncode,out,err)
        finally: self.render_proc=None
    def run_ffmpeg_final_progress(self,cmd,total_duration):
        if self.render_cancel.is_set(): raise RuntimeError('RENDER_CANCELLED')
        cmd=self._localize_cmd(cmd)
        cmd=cmd[:-1]+['-progress','pipe:1','-nostats',cmd[-1]] if cmd and cmd[-1] else cmd
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',bufsize=1,**self._no_console_kwargs())
        self.render_proc=proc
        try:
            for line in proc.stdout:
                line=line.strip()
                if line.startswith('out_time='):
                    stamp=line.split('=',1)[1]
                    try:
                        h,m,sec=stamp.split(':'); current=int(h)*3600+int(m)*60+float(sec)
                        pct=min(99,max(90,90+current/max(0.1,float(total_duration))*9))
                        self.q.put(('overall',pct,'Final encode / mux'))
                    except Exception: pass
                elif line.startswith('progress=') and line.endswith('end'):
                    self.q.put(('overall',100,'Final encode complete'))
                if self.render_cancel.is_set():
                    proc.terminate()
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait()
                    raise RuntimeError('RENDER_CANCELLED')
            err=proc.stderr.read();code=proc.wait()
            if code: raise subprocess.CalledProcessError(code,cmd,stderr=err)
            return subprocess.CompletedProcess(cmd,code,None,err)
        finally: self.render_proc=None
    def run_ffmpeg_assembly_progress(self,cmd,estimated_duration):
        """Parse FFmpeg progress while assembling transitions; report real activity, speed and elapsed heartbeat."""
        if self.render_cancel.is_set(): raise RuntimeError('RENDER_CANCELLED')
        cmd=self._localize_cmd(cmd)
        if cmd and cmd[-1]: cmd=cmd[:-1]+['-progress','pipe:1','-nostats',cmd[-1]]
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',bufsize=1,**self._no_console_kwargs())
        self.render_proc=proc; start=time.time(); last_heartbeat=start; last_stats={}; last_reported_stats={}; stderr_lines=[]
        def drain_stderr():
            try:
                for line in proc.stderr:
                    if line.strip(): stderr_lines.append(line.rstrip())
            except Exception: pass
        err_thread=threading.Thread(target=drain_stderr,daemon=True); err_thread.start()
        try:
            for line in proc.stdout:
                line=line.strip()
                if '=' in line:
                    key,value=line.split('=',1); last_stats[key]=value
                now=time.time(); elapsed=now-start
                if last_stats.get('progress') in ('continue','end'):
                    try:
                        out=last_stats.get('out_time','00:00:00.000000').split(':'); outsec=float(out[-1])+int(out[-2])*60+int(out[-3])*3600
                    except Exception: outsec=0.0
                    try: frame=int(last_stats.get('frame','0'))
                    except Exception: frame=0
                    speed=last_stats.get('speed','?')
                    last_reported_stats=dict(last_stats)
                    if estimated_duration and estimated_duration>0:
                        ratio=max(0,min(1,outsec/estimated_duration)); pct=77+ratio*4.8
                        self.q.put(('overall',pct,'Assembly — '+(f'{outsec:.1f}s / {estimated_duration:.1f}s' if outsec else 'processing transitions')))
                    self.q.put(('assembly_status',f'Assembly active · {elapsed:.0f}s elapsed · frame {frame} · {speed}'))
                    last_stats={}
                if now-last_heartbeat>=20:
                    self.q.put(('log',f'Assembly heartbeat: FFmpeg still running ({elapsed:.0f}s elapsed; latest frame {last_reported_stats.get("frame","n/a")} and output time {last_reported_stats.get("out_time","n/a")} reported).'))
                    last_heartbeat=now
                if self.render_cancel.is_set():
                    proc.terminate()
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                    raise RuntimeError('RENDER_CANCELLED')
            err_thread.join(timeout=2); code=proc.wait()
            if code: raise subprocess.CalledProcessError(code,cmd,stderr='\n'.join(stderr_lines[-100:]))
            return subprocess.CompletedProcess(cmd,code,None,'\n'.join(stderr_lines))
        finally: self.render_proc=None
    def cancel_render(self):
        if self.job_type=='generate' and self.running:
            self.render_cancel.set(); self.progress_text.set('Cancelling render…'); self._log('Render cancellation requested. Stopping current FFmpeg process…')
            p=self.render_proc
            if p and p.poll() is None:
                try: p.terminate()
                except: pass

    def copy_seed(self):
        value=self.seed.get().strip()
        if value:
            self.root.clipboard_clear(); self.root.clipboard_append(value); self._log(f'Seed copied: {value}')
        else: messagebox.showinfo('Seed','No seed is currently set. Generate an edit first.')
    def start_new_random(self):
        self.seed.set('')
        self.start()
    def start(self):
        if self.running:return
        if not self.ffmpeg_ready: messagebox.showinfo('FFmpeg setup','The portable FFmpeg engine is still being installed or could not be verified. Check the log and try again.'); return
        folder=self.ensure_footage_folder()
        if folder is None:return
        song=Path(self.song.get().strip()); out=Path(self.output.get().strip())
        self.save_settings()
        if not folder.is_dir():messagebox.showerror('Missing footage folder',f'Footage folder is not available:\n{folder}');return
        if not song.is_file():messagebox.showerror('Missing song','Please select a valid audio file.');return
        if not self.output.get().strip():
            messagebox.showinfo('Choose output filename','Please choose a filename and location for your finished MP4 using Browse.')
            self.pick_output()
            if not self.output.get().strip(): return
            out=Path(self.output.get().strip())
        if not out.parent.exists():
            try:out.parent.mkdir(parents=True,exist_ok=True)
            except Exception as e:messagebox.showerror('Output folder error',str(e));return
        try:mn=float(self.min_len.get());mx=float(self.max_len.get())
        except ValueError:messagebox.showerror('Clip length error','Enter numeric clip lengths.');return
        if mn<=0 or mx<mn:messagebox.showerror('Clip length error','Maximum must be at least minimum, and both positive.');return
        if not (self.ffmpeg_dir/'ffmpeg.exe').is_file():messagebox.showerror('FFmpeg missing','The application-local FFmpeg binary is missing. Restart the editor to install it.');return
        if not self.seed.get().strip():
            self.seed.set(str(random.SystemRandom().randint(100000,999999999)))
            self._log(f'Auto-generated random seed: {self.seed.get()}')
        if not self.preflight(show=True): return
        if out.exists() and not messagebox.askyesno('Overwrite existing video',f'The output file already exists:\n\n{out}\n\nOverwrite it?'): return
        try: highlight_entries=self._parse_highlight_schedule(self.highlight_schedule)
        except ValueError as e: messagebox.showerror('Highlight schedule error',str(e)); return
        try: music_trim=self._parse_music_trim_schedule(self.music_trim_schedule)
        except ValueError as e: messagebox.showerror('Music trim schedule error',str(e)); return
        self._start_storyboard_progress()
        self.render_started=time.time()
        self.render_cancel.clear(); self.running=True;self.job_type='generate';self.generate_btn.configure(state='disabled');self.generate_again_btn.configure(state='disabled');self.cancel_render_btn.configure(state='normal');self.scan_btn.configure(state='disabled');self.download_btn.configure(state='disabled');self.progress.configure(mode='indeterminate');self.progress.start(12);self.progress_text.set('Preparing edit…')
        args=(str(folder),str(song),str(out),mn,mx,self.resolution.get(),self.aspect_ratio.get(),self.retro.get(),self.seed.get().strip(),self.mode.get(),self.output_quality.get(),self.fade_in.get(),self.fade_out.get(),self.use_intro.get(),self.intro_path.get().strip(),self.intro_duration.get().strip(),self.random_transitions.get(),self.transition_strength.get(),self.vertical_mode.get(),self.output_fps.get(),self.single_source_order.get(),highlight_entries,self.artistic_mode.get(),music_trim,self.turn_it_up.get())
        threading.Thread(target=self.worker,args=args,daemon=True).start()
    def probe_duration(self,path):
        # FFmpeg-only media probe: FFprobe is intentionally not launched because
        # Windows Application Control blocks the bundled executable on some PCs.
        cmd=[self._ffmpeg_exe(),'-hide_banner','-i',str(path),'-t','0','-f','null','-']
        started=time.time()
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20,check=False,**self._no_console_kwargs())
        except subprocess.TimeoutExpired as e:
            msg=f'FFMPEG PROBE TIMEOUT (20s): {Path(path).name}'
            self.q.put(('log',msg)); raise RuntimeError(msg) from e
        except Exception as e:
            msg=f'FFMPEG PROBE LAUNCH FAILED: {Path(path).name} | {type(e).__name__}: {e}'
            self.q.put(('log',msg)); raise RuntimeError(msg) from e
        output=(p.stderr or '')+'\n'+(p.stdout or '')
        match=re.search(r'Duration:\s*(\d{2,}:\d{2}:\d{2}(?:\.\d+)?)',output)
        if not match:
            detail=(p.stderr or p.stdout or '').strip().replace('\n',' ')[:300]
            msg=f'FFMPEG PROBE FAILED: {Path(path).name} | exit {p.returncode} | {detail or "duration not found"}'
            self.q.put(('log',msg)); raise RuntimeError(msg)
        try:
            h,m,sec=match.group(1).split(':'); duration=int(h)*3600+int(m)*60+float(sec)
            if not math.isfinite(duration) or duration<=0: raise ValueError('Duration is not positive')
        except Exception as e:
            msg=f'FFMPEG PROBE INVALID DURATION: {Path(path).name} | {match.group(1)}'
            self.q.put(('log',msg)); raise RuntimeError(msg) from e
        self.q.put(('log',f'FFMPEG PROBE OK: {Path(path).name} | {duration:.2f}s | {time.time()-started:.1f}s'))
        return duration
    def probe_video_dimensions(self,path):
        cmd=[self._ffmpeg_exe(),'-hide_banner','-i',str(path),'-t','0','-f','null','-']
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20,check=False,**self._no_console_kwargs())
        except Exception as e:
            self.q.put(('log',f'VIDEO DIMENSION PROBE FAILED: {Path(path).name} | {e}'))
            raise
        output=(p.stderr or '')+'\n'+(p.stdout or '')
        match=re.search(r'\b(\d{2,5})x(\d{2,5})\b',output)
        if not match:
            detail=(p.stderr or p.stdout or '').strip().replace('\n',' ')[:250]
            raise RuntimeError(f'Video dimensions not found for {Path(path).name}: {detail}')
        return int(match.group(1)),int(match.group(2))
    def _detect_transients_trim_aware(self,audio,duration,audio_start=0.0):
        """Build a musical edit map using beat, bar, phrase, energy and spectral-change cues.
        Lightweight analysis uses only Python stdlib and the app's local FFmpeg.
        Downbeat is estimated, not guaranteed; bars/phrases assume 4/4.
        When a trim schedule is active, analyse only the selected audio segment.
        """
        self.q.put(('log','Analysing music structure: pulse, bars, phrases, energy builds and timbral changes…'))
        sample_rate=8000; hop=320; frame_size=1024; expected_bytes=max(1,int(duration*sample_rate*2))
        cmd=['ffmpeg','-hide_banner','-loglevel','error']
        if audio_start>0: cmd += ['-ss',f'{audio_start:.3f}']
        cmd += ['-t',f'{duration:.3f}','-i',audio,'-ac','1','-ar',str(sample_rate),'-f','s16le','-']
        cmd=self._localize_cmd(cmd)
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**self._no_console_kwargs()); self.render_proc=proc
        pcm=bytearray(); bytes_read=0; last_update=0.0
        try:
            while True:
                if self.render_cancel.is_set():
                    try: proc.terminate()
                    except: pass
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                    raise RuntimeError('RENDER_CANCELLED')
                chunk=proc.stdout.read(65536) if proc.stdout else b''
                if not chunk: break
                pcm.extend(chunk); bytes_read+=len(chunk); secs=bytes_read/(sample_rate*2)
                if secs-last_update>=2.0 or bytes_read>=expected_bytes:
                    pct=min(100,bytes_read*100/expected_bytes)
                    self.q.put(('overall',22+6*pct/100,f'Analysing music: {min(duration,secs):.1f}/{duration:.1f}s')); last_update=secs
            rc=proc.wait()
            if rc: raise RuntimeError(f'FFmpeg music decode failed (exit {rc}).')
        finally:
            self.render_proc=None
            if proc.poll() is None:
                try: proc.terminate()
                except: pass
                try: proc.wait(timeout=2)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            if proc.stdout:
                try: proc.stdout.close()
                except: pass
        sample_count=len(pcm)//2
        if sample_count<frame_size*4: return []
        # RMS and spectral band features at 50 ms hops. FFT is a small radix-2 implementation.
        def fft(real):
            n=len(real); imag=[0.0]*n; j=0
            for i in range(1,n):
                bit=n>>1
                while j&bit: j^=bit; bit>>=1
                j^=bit
                if i<j: real[i],real[j]=real[j],real[i]; imag[i],imag[j]=imag[j],imag[i]
            length=2
            while length<=n:
                angle=-2.0*math.pi/length; wr0=math.cos(angle); wi0=math.sin(angle); half=length//2
                for base in range(0,n,length):
                    wr=1.0; wi=0.0
                    for k in range(half):
                        u_r=real[base+k]; u_i=imag[base+k]; v_r=real[base+k+half]*wr-imag[base+k+half]*wi; v_i=real[base+k+half]*wi+imag[base+k+half]*wr
                        real[base+k]=u_r+v_r; imag[base+k]=u_i+v_i; real[base+k+half]=u_r-v_r; imag[base+k+half]=u_i-v_i
                        wr,wi=wr*wr0-wi*wi0,wr*wi0+wi*wr0
                length*=2
            return real,imag
        bands=[]; rms_values=[]; spectral_flux=[]; band_change=[]; prev_mag=None; prev_bands=None
        # Frequency ranges approximate sub/bass, bass, low-mid, mid, presence and treble.
        ranges=[(0,60),(60,120),(120,256),(256,512),(512,768),(768,1024)]
        for frame_no,start in enumerate(range(0,max(0,sample_count-frame_size+1),hop)):
            if frame_no%400==0 and frame_no>0 and self.render_cancel.is_set(): raise RuntimeError('RENDER_CANCELLED')
            vals=struct.unpack_from('<'+'h'*frame_size,pcm,start*2)
            rms=math.sqrt(sum(v*v for v in vals)/frame_size); rms_values.append(rms)
            real=[(vals[i]/32768.0)*(0.5-0.5*math.cos(2*math.pi*i/(frame_size-1))) for i in range(frame_size)]; real,imag=fft(real)
            mags=[math.sqrt(real[k]*real[k]+imag[k]*imag[k]) for k in range(frame_size//2)]
            band=[]
            for lo,hi in ranges: band.append(sum(mags[lo:hi])/(hi-lo+1))
            bands.append(band)
            if prev_mag is None: spectral_flux.append(0.0)
            else:
                flux=sum(max(0.0,mags[k]-prev_mag[k]) for k in range(1,len(mags)))/(sum(prev_mag[1:])+1e-8)
                spectral_flux.append(flux)
            if prev_bands is None: band_change.append(0.0)
            else:
                a=prev_bands; b=band; dot=sum(x*y for x,y in zip(a,b)); na=math.sqrt(sum(x*x for x in a))+1e-9; nb=math.sqrt(sum(y*y for y in b))+1e-9
                band_change.append(max(0.0,1.0-dot/(na*nb)))
            prev_mag=mags; prev_bands=band
        if len(rms_values)<12: return []
        # Smooth short-term features but preserve sharp transients.
        def smooth(values,radius=1):
            return [sum(values[max(0,i-radius):min(len(values),i+radius+1)])/(min(len(values),i+radius+1)-max(0,i-radius)) for i in range(len(values))]
        rms_s=smooth(rms_values,1); flux_s=smooth(spectral_flux,1); change_s=smooth(band_change,1)
        mean_rms=sum(rms_s)/len(rms_s); median_rms=sorted(rms_s)[len(rms_s)//2]
        flux_mean=sum(flux_s)/len(flux_s); flux_med=sorted(flux_s)[len(flux_s)//2]
        onset_threshold=max(flux_med*1.8,flux_mean*1.55,0.006)
        onsets=[]
        for i in range(2,len(flux_s)-2):
            if flux_s[i]>=flux_s[i-1] and flux_s[i]>flux_s[i+1] and flux_s[i]>=onset_threshold and rms_s[i]>=max(median_rms*0.45,mean_rms*0.18): onsets.append((i*hop/sample_rate,flux_s[i]))
        # Pulse autocorrelation on 40-ms novelty envelope; supports 60–180 BPM.
        novelty=[max(0.0,flux_s[i]-flux_s[i-2]) if i>=2 else 0.0 for i in range(len(flux_s))]
        centered=[v-(sum(novelty)/len(novelty)) for v in novelty]; best_lag=None; best_corr=-1.0
        for lag in range(8,26):
            left=centered[lag:]; right=centered[:-lag]; cross=sum(a*b for a,b in zip(left,right)); nl=sum(a*a for a in left) or 1.0; nr=sum(b*b for b in right) or 1.0; corr=cross/math.sqrt(nl*nr); bpm=60.0/(lag*hop/sample_rate)
            if 60<=bpm<=180 and corr>best_corr: best_corr=corr; best_lag=lag
        if not best_lag or best_corr<0.035:
            self.q.put(('log','Pulse confidence low; falling back to detected musical events and section-change cues.'))
            # Fallback is still musically ranked: prominent spectral changes outrank
            # ordinary onset accents when pulse/downbeat confidence is insufficient.
            fallback=[]
            for t,strength in onsets: fallback.append((t,0.8+min(0.8,strength/max(onset_threshold,1e-6)*0.15),'accent'))
            section_events=[(i*hop/sample_rate,v) for i,v in enumerate(change_s) if v>=max(0.22,sorted(change_s)[int(len(change_s)*0.985)])]
            fallback.extend((t,1.8,'section') for t,_ in section_events)
            # Dynamic cues supplement the fallback when pulse estimation fails.
            energy_window=max(1,int(2.5*sample_rate/hop))
            for i in range(energy_window,len(rms_s)-energy_window,max(1,energy_window//3)):
                before=sum(rms_s[i-energy_window:i])/energy_window; after=sum(rms_s[i:i+energy_window])/energy_window
                t=i*hop/sample_rate
                if before>1e-6 and after/before>=1.5 and after>median_rms*1.15: fallback.append((t,1.9,'build'))
                elif after>1e-6 and before/after>=1.5 and before>median_rms*1.15: fallback.append((t,2.0,'drop'))
            filtered=[]
            for item in sorted(fallback,key=lambda x:x[0]):
                if not filtered or item[0]-filtered[-1][0]>=0.35: filtered.append(item)
                elif item[1]>filtered[-1][1]: filtered[-1]=item
            return filtered
        beat_period=best_lag*hop/sample_rate; bpm=60.0/beat_period
        self.q.put(('log',f'Pulse estimate: ~{bpm:.1f} BPM (confidence {best_corr:.2f}); deriving beat/bar/phrase grid.'))
        # Choose beat phase by maximizing onset novelty over the first 12 seconds.
        phase_scores=[]; phase_span=min(len(novelty),int(12*sample_rate/hop)); phase_steps=max(1,int(best_lag))
        for phase in range(phase_steps):
            score=sum(novelty[i] for i in range(phase,phase_span,phase_steps))
            phase_scores.append(score)
        anchor_index=max(range(len(phase_scores)),key=lambda i:phase_scores[i]); anchor=anchor_index*hop/sample_rate
        beat_times=[]; t=anchor
        while t<duration:
            if t>=0: beat_times.append(t)
            t+=beat_period
        # Refine grid points only with nearby onset novelty peaks; avoid pulling beats arbitrarily.
        refined=[]
        for beat in beat_times:
            near=[o for o in onsets if abs(o[0]-beat)<=0.10]
            refined.append(max(near,key=lambda x:x[1])[0] if near else beat)
        bar_cues=[]; phrase_cues=[]; four_bar_cues=[]
        for beat_i,beat in enumerate(refined):
            if beat_i%4==0 and beat<duration: bar_cues.append(beat)
            if beat_i%16==0 and beat_i>0 and beat<duration: phrase_cues.append(beat)
        # Strong spectral novelty/instrumentation changes and sharp onset peaks act as override edit events.
        change_cutoff=max(0.20,sorted(change_s)[int(len(change_s)*0.985)])
        novelty_cutoff=max(onset_threshold*1.7,sorted(novelty)[int(len(novelty)*0.99)])
        raw_events=[]
        for i in range(2,len(change_s)-2):
            if change_s[i]>=change_cutoff and change_s[i]>=change_s[i-1] and change_s[i]>change_s[i+1]: raw_events.append((i*hop/sample_rate,change_s[i]))
        event_cues=[t for t,strength in onsets if strength>=novelty_cutoff]
        section_cues=[t for t,strength in raw_events if strength>=change_cutoff]
        # v17.11 music intelligence: identify sustained energy lifts, drops and
        # high/low-energy section boundaries from rolling RMS, not beat novelty alone.
        build_cues=[]; drop_cues=[]; energy_peak_cues=[]; low_energy_cues=[]
        window=int(2.5*sample_rate/hop)
        stride=max(1,window//3)
        for i in range(window,len(rms_s)-window,stride):
            before=sum(rms_s[i-window:i])/window; after=sum(rms_s[i:i+window])/window
            t=i*hop/sample_rate
            if before>1e-6 and after/before>=1.50 and after>median_rms*1.15:
                build_cues.append(t)
            elif after>1e-6 and before/after>=1.50 and before>median_rms*1.15:
                drop_cues.append(t)
        # Energy-state markers: use a smoothed ~1.5 s envelope and relative
        # thresholds so quieter/louder tracks can both produce useful labels.
        energy_window=max(1,int(1.5*sample_rate/hop))
        energy_env=[sum(rms_s[max(0,i-energy_window//2):min(len(rms_s),i+energy_window//2+1)]) / max(1,len(rms_s[max(0,i-energy_window//2):min(len(rms_s),i+energy_window//2+1)])) for i in range(len(rms_s))]
        energy_hi=max(median_rms*1.45,mean_rms*1.25)
        energy_lo=max(1e-6,median_rms*0.62)
        for i in range(2,len(energy_env)-2):
            if energy_env[i]>=energy_hi and energy_env[i]>=energy_env[i-1] and energy_env[i]>energy_env[i+1]:
                energy_peak_cues.append(i*hop/sample_rate)
            if energy_env[i]<=energy_lo and energy_env[i]<=energy_env[i-1] and energy_env[i]<energy_env[i+1]:
                low_energy_cues.append(i*hop/sample_rate)
        # v17.11: weighted anchors include musical structure plus dynamics.
        weighted=[]
        weighted.extend((t,0.75,'beat') for t in refined)
        weighted.extend((t,2.25,'bar') for t in bar_cues)
        weighted.extend((t,3.25,'phrase') for t in phrase_cues)
        weighted.extend((t,1.45,'accent') for t in event_cues)
        weighted.extend((t,2.0,'section') for t in section_cues)
        weighted.extend((t,1.85,'build') for t in build_cues)
        weighted.extend((t,2.10,'drop') for t in drop_cues)
        weighted.extend((t,1.70,'energy_peak') for t in energy_peak_cues)
        weighted.extend((t,0.95,'low_energy') for t in low_energy_cues)
        weighted.sort(key=lambda item:item[0])
        filtered=[]
        for cue in weighted:
            if not filtered or cue[0]-filtered[-1][0]>=0.20:
                filtered.append(cue)
            elif cue[1]>filtered[-1][1]:
                filtered[-1]=cue
        # Legacy v17.11 map log removed; consolidated versioned summary is emitted below.
        # Refined Audio Brain event/progression targets supplement the existing beat-grid map.
        brain_cues=self._audio_brain_event_cues(rms_s,flux_s,bands,sample_rate,hop,duration)
        filtered.extend(brain_cues)
        filtered.sort(key=lambda item:(item[0],-item[1]))
        # Deduplicate very close targets, retaining the higher-priority anchor.
        merged=[]
        for cue in filtered:
            if not merged or cue[0]-merged[-1][0]>=0.16:merged.append(cue)
            elif cue[1]>merged[-1][1]:merged[-1]=cue
        self.q.put(('log',f'v{APP_VERSION} refined music map: {len(refined)} beats, {len(bar_cues)} bars, {len(phrase_cues)} phrases, {len(event_cues)} strong accents, {len(section_cues)} timbral changes, {len(build_cues)} lifts, {len(drop_cues)} drops, {len(energy_peak_cues)} energy peaks, {len(low_energy_cues)} low-energy markers.'))
        self.q.put(('log',f'Audio Brain edit targets merged: {len(merged)} anchors (musical grid + interpreted progressions).'))
        return merged
    def _audio_brain_event_cues(self, rms_s, flux_s, bands, sample_rate, hop, duration):
        """Apply the Audio Brain v0.2.7 interpretation layers to this scan's existing DSP arrays.
        Builds 10-second bins in the interpreter's expected report format; no second audio decode.
        """
        bin_seconds=10.0
        n_frames=min(len(rms_s),len(flux_s),len(bands))
        if n_frames<1:return []
        segments=[]
        for a in range(0,n_frames,max(1,int(bin_seconds*sample_rate/hop))):
            b=min(n_frames,a+max(1,int(bin_seconds*sample_rate/hop)))
            def avg(vals):return sum(vals[a:b])/max(1,b-a)
            band_avg=[avg([float(row[k]) for row in bands]) for k in range(6)]
            # Collapse six coarse spectral buckets into the Audio Brain's four texture groups.
            texture={'bass_20_150':band_avg[0]+band_avg[1],
                   'low_mid_150_500':band_avg[2],
                   'high_mid_500_2000':band_avg[3]+band_avg[4],
                   'high_2k_5k':band_avg[5]}
            segments.append({'start_s':a*hop/sample_rate,'end_s':min(duration,b*hop/sample_rate),
                'rms_mean':avg(rms_s[a:b]),'spectral_flux_mean':avg(flux_s[a:b]),
                'spectral_centroid_hz':0.0,'texture_band_energy':texture})
        report={'segments_10s':segments}
        interpreted=audio_brain_classify(report)
        events=interpreted.get('events',[])
        progression,texture=audio_brain_editorial(events)
        sections=audio_brain_sections(report,interpreted.get('metrics',{}))
        cue_map={'PEAK':'brain_peak','BUILD':'brain_build','REBUILD':'rebuild',
            'HIGH ENERGY':'high_energy','DROP / RELEASE':'release','BREATHER':'breather',
            'TEXTURE SHIFT':'texture_shift','RECOVERY':'recovery','LOW ENERGY':'low_energy'}
        cues=[]
        for event in progression:
            label=cue_map.get(event.get('label'))
            if label:
                # Start markers provide an editorial arrival target; sustained events
                # also contribute an exit cue so the Director can cut away naturally.
                cues.append((float(event.get('start',0)),2.6,label))
                if event.get('kind') in ('sustain','sequence') and float(event.get('end',0))-float(event.get('start',0))>=8:
                    cues.append((float(event.get('end',0)),1.7,label+'_end'))
        self.q.put(('log',f'Audio Brain v0.2.7 integrated: {len(events)} interpreted events, {len(progression)} editorial progressions, {len(sections)} track sections; {len(cues)} additional edit targets.'))
        return cues
    def _director_music_profile(self,audio,duration):
        """Compact energy/dynamics map for the v18 Director Engine. Stdlib-only."""
        rate=4000
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-i',audio,'-ac','1','-ar',str(rate),'-f','s16le','-']
        proc=subprocess.Popen(self._localize_cmd(cmd),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**self._no_console_kwargs())
        samples=[]; chunk_size=rate*2
        try:
            while True:
                if self.render_cancel.is_set():
                    proc.terminate()
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait()
                    raise RuntimeError('RENDER_CANCELLED')
                chunk=proc.stdout.read(chunk_size) if proc.stdout else b''
                if not chunk: break
                usable_bytes=len(chunk)//2*2
                if usable_bytes:
                    vals=struct.unpack('<'+'h'*(usable_bytes//2),chunk[:usable_bytes])
                    rms=math.sqrt(sum(v*v for v in vals)/max(1,len(vals)))
                    samples.append(rms)
            rc=proc.wait()
            if rc: raise RuntimeError(f'Music profile decode failed ({rc}).')
        finally:
            if proc.poll() is None:
                try: proc.terminate()
                except: pass
                try: proc.wait(timeout=2)
                except subprocess.TimeoutExpired: proc.kill();proc.wait()
            if proc.stdout:
                try: proc.stdout.close()
                except: pass
        if not samples:
            return [{'start':0.0,'end':duration,'energy':0.5,'trend':0.0,'state':'flow'}]
        sortedv=sorted(samples); med=sortedv[len(sortedv)//2] or 1.0; mx=max(samples) or 1.0
        sections=[]
        for i,e in enumerate(samples):
            before=sum(samples[max(0,i-4):i+1])/max(1,len(samples[max(0,i-4):i+1]))
            after=sum(samples[i:min(len(samples),i+5)])/max(1,len(samples[i:min(len(samples),i+5)]))
            normalized=max(0.0,min(1.0,e/mx))
            trend=(after-before)/(mx+1e-8)
            if normalized>=0.78: state='peak'
            elif normalized<=0.26: state='breather'
            elif trend>=0.075: state='build'
            else: state='flow'
            sections.append({'start':float(i),'end':min(duration,float(i+1)),'energy':normalized,'trend':trend,'state':state})
        # Smooth isolated one-second labels and group contiguous states into readable musical arcs.
        states=[s['state'] for s in sections]
        for i in range(1,len(states)-1):
            if states[i-1]==states[i+1] and states[i]!=states[i-1]: states[i]=states[i-1]
        for i,s in enumerate(sections): s['state']=states[i]
        grouped=[]
        for sec in sections:
            if grouped and grouped[-1]['state']==sec['state'] and sec['start']-grouped[-1]['end']<0.01:
                g=grouped[-1]; g['end']=sec['end']; g['energy_sum']+=sec['energy']; g['trend_sum']+=sec['trend'];g['count']+=1
            else: grouped.append({'start':sec['start'],'end':sec['end'],'state':sec['state'],'energy_sum':sec['energy'],'trend_sum':sec['trend'],'count':1})
        for g in grouped:
            g['energy']=g.pop('energy_sum')/g['count'];g['trend']=g.pop('trend_sum')/g['count'];g.pop('count')
        # Avoid over-fragmented one-second classifications by merging short arcs (<3 s) into adjacent arc.
        changed=True
        while changed and len(grouped)>1:
            changed=False
            for i,g in enumerate(grouped):
                if g['end']-g['start']>=3.0: continue
                j=0 if i==0 else (len(grouped)-1 if i==len(grouped)-1 else (i-1 if grouped[i-1]['end']-grouped[i-1]['start']>=grouped[i+1]['end']-grouped[i+1]['start'] else i+1))
                if j==i: continue
                lo=min(i,j); hi=max(i,j); a,b=grouped[lo],grouped[hi]
                # Merge into the longer arc's state, retaining a weighted mean.
                dur_a=a['end']-a['start'];dur_b=b['end']-b['start'];total=dur_a+dur_b
                if total>0:
                    a['energy']=(a['energy']*dur_a+b['energy']*dur_b)/total
                    a['trend']=(a['trend']*dur_a+b['trend']*dur_b)/total
                a['state']=a['state'] if dur_a>=dur_b else b['state'];a['end']=b['end']
                grouped.pop(hi);changed=True;break
        self.q.put(('log',f'Director music map: {len(grouped)} narrative sections; states: '+', '.join(f"{g['state']} {g['start']:.0f}-{g['end']:.0f}s" for g in grouped[:12])))
        return grouped
    def _director_video_candidates(self,source,duration,metric,minlen,maxlen):
        """Build candidate subclips from cached per-second analysis, not whole-file scores."""
        timeline=metric.get('timeline') or []
        lo,hi=(2.0,max(2.0,duration-2.0)) if duration>12.0 else (0.0,duration)
        usable=max(0.0,hi-lo)
        if usable<0.8: return []
        # Target durations are decided later by the music arc; scan several window sizes now.
        lengths=sorted(set([max(1.5,min(maxlen,2.0)),max(2.0,min(maxlen,3.0)),max(2.5,min(maxlen,4.0)),max(3.5,min(maxlen,5.0)),max(4.5,min(maxlen,6.0)),max(5.5,min(maxlen,7.0)),max(6.5,min(maxlen,8.0)),max(7.5,min(maxlen,9.0)),max(8.5,min(maxlen,10.0)),float(maxlen),min(12.0,float(maxlen)*1.35)]))
        step=1.5; candidates=[]
        for length in lengths:
            length=min(length,usable)
            if length<0.75: continue
            start=lo
            while start+length<=hi+0.001:
                first=int(max(0,start));last=int(min(len(timeline),math.ceil(start+length)))
                rows=timeline[first:last]
                if rows:
                    motion=sum(float(r.get('motion',0)) for r in rows)/len(rows)
                    detail=sum(float(r.get('detail',0)) for r in rows)/len(rows)
                    brightness=sum(float(r.get('brightness',120)) for r in rows)/len(rows)
                    variability=sum(float(r.get('motion_var',0)) for r in rows)/len(rows)
                    event=sum(float(r.get('event',0)) for r in rows)/len(rows)
                    # Temporal Intelligence v2: compare the motion profile's early and late thirds.
                    third=max(1,len(rows)//3); early_rows=rows[:third]; late_rows=rows[-third:]
                    early_motion=sum(float(r.get('motion',0)) for r in early_rows)/len(early_rows)
                    late_motion=sum(float(r.get('motion',0)) for r in late_rows)/len(late_rows)
                    motion_progress=(late_motion-early_motion)/48.0
                    peak_event=max((float(r.get('event',0)) for r in rows),default=0.0)
                    quality=max(0.0,1.0-abs(brightness-120)/140.0)
                    motionn=motion/(motion+32.0) if motion>0 else 0.0; detailn=detail/(detail+45.0) if detail>0 else 0.0; variabilityn=variability/(variability+18.0) if variability>0 else 0.0
                    progression_label=('building' if motion_progress>0.12 else 'settling' if motion_progress<-0.12 else 'steady')
                    event_label=('eventful' if peak_event>0.68 else 'moderate' if peak_event>0.38 else 'calm')
                    fpv_counts={}
                    for row in rows:
                        for tag,confidence in row.get('fpv_events',[]): fpv_counts[tag]=fpv_counts.get(tag,0.0)+float(confidence)
                    fpv_primary=max(fpv_counts.items(),key=lambda x:x[1])[0] if fpv_counts else 'LOW_ACTIVITY'
                    fpv_strength=max(fpv_counts.values(),default=0.0)/max(1,len(rows))
                    visual_score=0.23*quality+0.18*detailn+0.22*motionn+0.15*variabilityn+0.14*min(1.0,event)+0.08*min(1.0,abs(motion_progress))
                    candidates.append({'start':start,'length':length,'score':visual_score,'motion':motionn,'motion_raw':motion,'event':min(1.0,event),'peak_event':peak_event,'detail':detailn,'brightness':brightness,'variability':variability,'variabilityn':variabilityn,'motion_progress':motion_progress,'progression':progression_label,'event_type':event_label,'fpv_primary':fpv_primary,'fpv_strength':round(fpv_strength,3),'fpv_events':fpv_counts})
                start+=step
        # Keep a compact pool of high-value and spatially distributed moments.
        candidates.sort(key=lambda c:c['score'],reverse=True)
        picked=[]
        for c in candidates:
            if all(abs(c['start']-p['start'])>2.0 or abs(c['length']-p['length'])>1.0 for p in picked): picked.append(c)
            if len(picked)>=48: break
        return picked
    def _director_plan(self,usable,index,sections,cues,song_duration,minlen,maxlen,mode,rng,source_bounds,chronological=False):
        """Plan the edit in musical arcs, selecting high-scoring footage moments with diversity."""
        self.last_director_decisions=[]
        if chronological:
            sources=sorted(usable,key=lambda item:[int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)',Path(item[0]).name)])
            total=sum(max(0.0,source_bounds(d)[1]-source_bounds(d)[0]) for _,d,_ in sources)
            segs=[]; elapsed=0.0; cursor=0.0; chronological_decisions=[]
            while elapsed<song_duration-0.05:
                target=min(maxlen,max(minlen,5.0),song_duration-elapsed)
                prog=min(total-0.01,max(0.0,elapsed/max(song_duration,0.01)*total));off=0.0;chosen=None
                for src,d,sc in sources:
                    a,b=source_bounds(d);avail=max(0,b-a)
                    if prog<off+avail:chosen=(src,d,sc,a+prog-off);break
                    off+=avail
                if chosen is None:
                    src,d,sc=sources[-1];a,b=source_bounds(d);chosen=(src,d,sc,max(a,b-0.8))
                src,d,sc,start=chosen;a,b=source_bounds(d);target=min(target,b-start)
                if target<=0.05: break
                segs.append((src,start,target));chronological_decisions.append({'time':elapsed,'duration':target,'source':Path(src).name,'arc':'chronological','target':'continuity','motion':0.0,'event':'n/a','progression':'n/a','score':0.0});elapsed+=target
            self.last_director_decisions=chronological_decisions
            return segs
        pools={}
        for src,d,score in usable:
            m=index.get(str(Path(src).resolve()),{})
            pools[src]=self._director_video_candidates(src,d,m,minlen,maxlen)
        candidates_total=sum(len(v) for v in pools.values())
        # v18.5.1 WOW Director: identify exceptional moments across the entire footage pool,
        # then reserve them for musical peaks/payoffs instead of spending them early.
        all_candidates=[(src,c) for src,items in pools.items() for c in items]
        if all_candidates:
            ranked_moments=sorted(all_candidates,key=lambda pair:(0.34*pair[1]['score']+0.24*pair[1].get('peak_event',0.0)+0.18*pair[1]['motion']+0.14*pair[1]['variability']/18.0+0.10*pair[1]['detail']+0.08*pair[1].get('fpv_strength',0.0)),reverse=True)
            wow_pool=[]
            for src,c in ranked_moments:
                if all(src!=oldsrc or abs(c['start']-oldc['start'])>max(3.0,oldc['length']*0.65) for oldsrc,oldc in wow_pool):
                    wow_pool.append((src,c))
                if len(wow_pool)>=max(3,min(7,round(song_duration/35))):break
            for rank,(src,c) in enumerate(wow_pool,1):
                c['wow_rank']=rank;c['wow_score']=max(0.0,1.0-(rank-1)/max(1,len(wow_pool)))
            self.wow_moments=[{'rank':i+1,'source':Path(src).name,'start':c['start'],'length':c['length'],'score':c.get('wow_score',0.0),'event':c.get('event_type','unknown'),'motion':c['motion']} for i,(src,c) in enumerate(wow_pool)]
        else:self.wow_moments=[]
        self.q.put(('log',f'WOW DIRECTOR: {len(self.wow_moments)} exceptional moments identified and reserved for deliberate payoff; {candidates_total} total candidates across {len(pools)} sources.'))
        segments=[];elapsed=0.0;recent_sources=[];recent_motions=[];recent_events=[];used_windows=[];last_state=None;last_src=None;director_decisions=[];deployed_wow_ranks=set()
        # Arc-aware desired clip durations and visual character.
        state_cfg={'breather':(max(5.0,minlen),max(8.5,maxlen),'smooth'),'opening':(max(4.5,minlen),max(8.0,maxlen),'smooth'),'build':(max(3.0,minlen),max(5.5,maxlen),'dynamic'),'flow':(max(3.0,minlen),max(6.5,maxlen),'flow'),'peak':(max(1.7,minlen),max(3.8,maxlen),'impact'),'finale':(max(2.2,minlen),max(4.8,maxlen),'impact')}
        if not sections: sections=[{'start':0.0,'end':song_duration,'state':'flow','energy':0.5,'trend':0.0}]
        peak_starts=[s['start'] for s in sections if s['state']=='peak']
        for slot in range(2000):
            if elapsed>=song_duration-0.05:break
            sec=next((s for s in sections if s['start']<=elapsed<s['end']),sections[-1])
            state=sec['state']
            if mode=='Random montage': state='flow'
            elif elapsed<min(6.0,song_duration*0.12) and slot<2:state='opening'
            if mode!='Random montage' and elapsed>=song_duration-max(9.0,song_duration*0.15):state='finale'
            cfg=state_cfg.get(state,state_cfg['flow']);lo,hi,character=cfg
            remaining=song_duration-elapsed
            # Preset identity remains meaningful: fast cuts intensify, documentary breathes,
            # rhythm-focused tightens its musical timing, while Story Arc reserves impact.
            if mode=='FPV action / fast cuts': lo*=0.70;hi*=0.72
            elif mode=='Retro documentary / long shots': lo*=1.28;hi*=1.38;character='smooth'
            elif mode=='Rhythm-focused': lo*=0.85;hi*=0.88
            elif mode=='Random montage': lo=3.0;hi=6.0;character='flow'
            target_lo=max(minlen,lo);target_hi=min(maxlen,hi)
            if target_hi<target_lo:target_hi=target_lo
            desired=min(remaining,rng.uniform(target_lo,target_hi))
            cut_cue='Director duration target'
            cut_cue_time=None
            # Music events may pull the cut toward a strong phrase/accent, but the director avoids beat-grid obedience.
            cue_window=0.70 if mode=='Rhythm-focused' else 1.1
            cue_min_gap=0.9 if mode=='Rhythm-focused' else 1.2
            near=[c for c in cues if isinstance(c,tuple) and len(c)>=3 and elapsed+desired-cue_window<=c[0]<=elapsed+desired+cue_window and c[0]>elapsed+cue_min_gap and c[2] in ('phrase','bar','section','build','drop','energy_peak','brain_peak','brain_build','rebuild','release','breather','high_energy','recovery','low_energy','texture_shift')]
            if near:
                cut=min(near,key=lambda c:abs(c[0]-(elapsed+desired))-(0.45 if c[2] in ('brain_peak','brain_build','rebuild','release') else 0.30 if c[2]=='phrase' else 0.15 if c[2]=='bar' else 0.0))
                desired=max(1.0,min(remaining,cut[0]-elapsed))
                cut_cue=cut[2].replace('_',' ').title()
                cut_cue_time=float(cut[0])
            desired=max(0.7,min(remaining,desired))
            ranked=[]
            for src,src_candidates in pools.items():
                if not src_candidates:continue
                src_score=next((s for f,d,s in usable if f==src),0.5)
                for c in src_candidates:
                    # Candidate can be trimmed to desired length if its available window is long enough.
                    if c['length']+0.05<desired:continue
                    # v18.5.1 DUPLICATION FIX: evaluate actual interval overlap, not
                    # merely the distance between clip start points. Sliding-window
                    # candidates from the same source often overlap substantially.
                    candidate_end=c['start']+desired
                    overlap=False
                    for u,st,ln in used_windows:
                        if src!=u: continue
                        overlap_len=max(0.0,min(candidate_end,st+ln)-max(c['start'],st))
                        if overlap_len>0.35*min(desired,ln):
                            overlap=True;break
                    if overlap:continue
                    # Strong source cooldown: don't revisit a source while fresh
                    # alternatives remain. The hard exclusion is relaxed only when
                    # necessary to keep the edit moving.
                    recent_penalty=0.30 if src in recent_sources[-5:] else 0.0
                    if src in recent_sources[-3:] and len(pools)>3:
                        continue
                    duplicate_motion_penalty=0.18 if recent_motions and abs(c['motion']-recent_motions[-1])<0.12 else 0.0
                    repeated_event_penalty=0.12 if recent_events and c.get('event_type')==recent_events[-1] else 0.0
                    # v19.2: gently discourage short-run visual-pattern repetition,
                    # without forbidding a useful recurring event/motion character.
                    recent_event_window=recent_events[-3:]
                    same_event_count=sum(1 for ev in recent_event_window if ev==c.get('event_type'))
                    pattern_repeat_penalty=0.07 if same_event_count>=2 else 0.0
                    recent_motion_window=recent_motions[-3:]
                    similar_motion_count=sum(1 for mv in recent_motion_window if abs(float(mv)-float(c['motion']))<0.13)
                    if similar_motion_count>=2: pattern_repeat_penalty+=0.04
                    if character=='smooth':
                        # Breather/opening: favour gentle, sustained motion and low event pressure.
                        motion_fit=max(0.0,1.0-abs(c['motion']-0.28)*1.65)
                        event_fit=0.22*c['event']
                        role_fit=0.65*motion_fit+0.35*(1.0-c['event'])
                    elif character=='impact':
                        motion_fit=0.55*c['motion']+0.45*c['event'];event_fit=c['event']
                        role_fit=0.55*motion_fit+0.45*c.get('variabilityn',0.0)
                    elif character=='dynamic':
                        # Build: reward rising motion and change, not just raw intensity.
                        motion_fit=0.45*c['motion']+0.30*c.get('variabilityn',0.0)+0.25*max(0.0,min(1.0,c.get('motion_progress',0.0)*2.0))
                        event_fit=0.35*c['event'];role_fit=0.65*motion_fit+0.35*event_fit
                    else:
                        # Flow: coherent mid-range movement, avoiding repeated extremes.
                        motion_fit=max(0.0,1.0-abs(c['motion']-0.55)*1.25)
                        event_fit=0.30*c['event'];role_fit=0.70*motion_fit+0.30*(1.0-c.get('variabilityn',0.0))
                    # Encourage fresh sources, visual variety, strong moments, and match to the musical role.
                    fpv_bonus=0.0
                    fpv_strength=float(c.get('fpv_strength',0.0))
                    fpv_label=c.get('fpv_primary','LOW_ACTIVITY')
                    if character=='smooth' and fpv_label=='FLOW': fpv_bonus=0.035*fpv_strength
                    elif character in ('impact','dynamic') and fpv_label in ('MOTION_SPIKE','CLOSE_PASS_CANDIDATE','REVEAL_OR_VIEW_CHANGE'): fpv_bonus=0.055*fpv_strength
                    elif state=='build' and fpv_label=='BUILDING_MOTION': fpv_bonus=0.045*fpv_strength
                    score=0.29*c['score']+0.23*max(0.0,min(1.0,role_fit))+0.09*max(0.0,min(1.0,motion_fit))+0.09*event_fit+0.11*src_score+0.10*(1.0-min(1.0,recent_penalty*3))+0.05*(1.0-min(1.0,duplicate_motion_penalty*4))+0.05*(1.0-min(1.0,repeated_event_penalty*5))-pattern_repeat_penalty+0.04*max(0.0,min(1.0,c.get('motion_progress',0.0) if state=='build' else -c.get('motion_progress',0.0) if state=='breather' else abs(c.get('motion_progress',0.0))))+fpv_bonus
                    if src==last_src:score-=0.14
                    if state=='peak' and c['event']>0.45:score+=0.08
                    if mode=='FPV action / fast cuts':score+=0.05*c['motion']+0.04*c['event']
                    elif mode=='Retro documentary / long shots':score+=0.10*(1.0-c['motion'])
                    elif mode=='Story arc (recommended)' and state=='finale':score+=0.12*c['score']
                    elif mode=='Rhythm-focused' and near:score+=0.04
                    # Exceptional footage is deliberately withheld from the opening/middle.
                    # Strong musical peaks and the finale unlock the reserved moments.
                    wow_rank=c.get('wow_rank',0);wow_score=c.get('wow_score',0.0)
                    progress=elapsed/max(song_duration,0.01)
                    payoff_slot=(state in ('peak','finale') or progress>=0.78)
                    if wow_rank:
                        if payoff_slot: score+=0.34*wow_score
                        elif progress<0.62: score-=0.24*wow_score
                        else: score-=0.10*wow_score
                    # Contrast-aware punctuation: when recent cuts are similar, reward
                    # candidates whose motion/event character visibly changes.
                    if recent_motions and abs(c['motion']-recent_motions[-1])>0.28:score+=0.055
                    if recent_events and c.get('event_type')!=recent_events[-1]:score+=0.035
                    ranked.append((score,src,c))
            if not ranked:
                # Graceful fallback when the new index lacks detailed timeline samples.
                src,d,sc=rng.choice([u for u in usable if u[0]!=last_src] or usable);a,b=source_bounds(d);length=min(desired,b-a,song_duration-elapsed);start=rng.uniform(a,max(a,b-length));segments.append((src,start,length));used_windows.append((src,start,length));recent_sources.append(src);recent_motions.append(0.5);last_src=src;elapsed+=length;continue
            # v19: at musical payoff slots, explicitly deploy an unused reserved WOW
            # moment when its source interval is still available and fits the planned cut.
            progress_now=elapsed/max(song_duration,0.01)
            payoff_slot_now=(state in ('peak','finale') or progress_now>=0.78)
            forced_wow=None
            if payoff_slot_now:
                eligible_wow=[]
                for wsrc,wc in all_candidates:
                    wr=wc.get('wow_rank',0)
                    if not wr or wr in deployed_wow_ranks or wc['length']+0.05<desired: continue
                    cend=wc['start']+desired
                    if any(wsrc==u and max(0.0,min(cend,st+ln)-max(wc['start'],st))>0.35*min(desired,ln) for u,st,ln in used_windows): continue
                    eligible_wow.append((wr,wc.get('score',0.0),wsrc,wc))
                if eligible_wow:
                    eligible_wow.sort(key=lambda x:(x[0],-x[1]))
                    _,_,wsrc,wc=eligible_wow[0]
                    forced_wow=(float('inf'),wsrc,wc)
            # Randomness remains, but high-ranked choices dominate to keep edits reproducible and coherent.
            # v19: collapse to one best candidate per source while preserving the explicit WOW candidate.
            # source for this slot, so one source cannot occupy most of the shortlist.
            best_by_source={}
            for item in ranked:
                if item[1] not in best_by_source or item[0]>best_by_source[item[1]][0]:
                    best_by_source[item[1]]=item
            ranked=list(best_by_source.values())
            ranked.sort(key=lambda x:x[0],reverse=True);shortlist=ranked[:min(8,len(ranked))]
            if forced_wow is not None:
                _,src,c=forced_wow
                selected_score=next((item[0] for item in ranked if item[1]==src and item[2] is c),float(c.get('score',0.0)))
                deployed_wow_ranks.add(c.get('wow_rank',0))
                self.q.put(('log',f'WOW PAYOFF DEPLOYED: #{c.get("wow_rank",0)} {Path(src).name} at source {c["start"]:.2f}s into {state} arc.'))
            else:
                weights=[max(0.01,x[0]-shortlist[-1][0]+0.10) for x in shortlist]
                selected_score,src,c=rng.choices(shortlist,weights=weights,k=1)[0]
            # Recompute the selected candidate's role-fit for reporting (the loop's
            # final temporary role_fit belongs to whichever candidate was evaluated last).
            if character=='smooth':
                selected_motion_fit=max(0.0,1.0-abs(c['motion']-0.28)*1.65)
                selected_role_fit=0.65*selected_motion_fit+0.35*(1.0-c['event'])
            elif character=='impact':
                selected_motion_fit=0.55*c['motion']+0.45*c['event']
                selected_role_fit=0.55*selected_motion_fit+0.45*c.get('variabilityn',0.0)
            elif character=='dynamic':
                selected_motion_fit=0.45*c['motion']+0.30*c.get('variabilityn',0.0)+0.25*max(0.0,min(1.0,c.get('motion_progress',0.0)*2.0))
                selected_role_fit=0.65*selected_motion_fit+0.35*0.35*c['event']
            else:
                selected_motion_fit=max(0.0,1.0-abs(c['motion']-0.55)*1.25)
                selected_role_fit=0.70*selected_motion_fit+0.30*(1.0-c.get('variabilityn',0.0))
            start=c['start'];length=min(desired,c['length'],remaining)
            # Track decision context for the report and sequence-memory penalties.
            segments.append((src,start,length));used_windows.append((src,start,length));recent_sources.append(src);recent_motions.append(c['motion']);recent_events.append(c.get('event_type','unknown'));last_src=src;elapsed+=length
            director_decisions.append({'time':elapsed-length,'duration':length,'start':start,'source':Path(src).name,'arc':state,'target':character,'motion':c['motion'],'motion_raw':c.get('motion_raw',0.0),'fpv_primary':c.get('fpv_primary','proxy'),'fpv_strength':c.get('fpv_strength',0.0),'event':c.get('event_type','unknown'),'event_strength':c.get('peak_event',0.0),'progression':c.get('progression','steady'),'score':float(selected_score),'role_fit':float(selected_role_fit),'cut_cue':cut_cue,'cut_cue_time':cut_cue_time,'wow_rank':c.get('wow_rank',0),'wow_score':c.get('wow_score',0.0),'payoff':bool(c.get('wow_rank') and (payoff_slot_now or payoff_slot))})
            if slot%8==0:self.q.put(('log',f'Director plan progress: {elapsed/song_duration*100:.0f}% of music mapped; current arc={state}, target shot={character}.'))
        self.last_director_decisions=director_decisions
        self.q.put(('log',f'DIRECTOR PLAN COMPLETE: {len(segments)} clips, {song_duration:.1f}s covered, {len(set(s[0] for s in segments))} unique sources used.'))
        self.q.put(('log',f'DIRECTOR INTELLIGENCE: temporal progression, event-profile labels, shot-to-shot motion/event memory active; {len(director_decisions)} explainable decisions recorded.'))
        return segments
    def library_path(self,folder):
        return Path(folder)/'.cockies_footage_index_v6_director.json'
    def _vision_fpv_interpret(self,row):
        # FPV event vocabulary v3: local heuristics based on grayscale temporal/spatial proxies.
        motion=float(row.get('motion',0)); event=float(row.get('event',0)); var=float(row.get('motion_var',0)); sc=float(row.get('scene_change',0)); sp=float(row.get('spatial_change',0)); trend=float(row.get('motion_trend',0))
        labels=[]; scores={}
        labels.append(('FLOW',max(0.0,1.0-min(1.0,var/35.0))*max(0.0,1.0-event)))
        labels.append(('BUILDING_MOTION',max(0.0,min(1.0,(trend+12)/32.0))*min(1.0,motion/25.0)))
        labels.append(('MOTION_SPIKE',max(event, min(1.0,motion/70.0)*min(1.0,var/30.0))))
        labels.append(('REVEAL_OR_VIEW_CHANGE',min(1.0,0.65*sc+0.35*sp)))
        labels.append(('REVERSAL_OR_INSTABILITY',min(1.0,var/45.0+max(0.0,-trend)/35.0)))
        labels.append(('CLOSE_PASS_CANDIDATE',min(1.0,motion/65.0*0.55+sp*0.35+event*0.10)))
        labels=[(name,round(float(conf),3)) for name,conf in labels if conf>=0.20]
        return {'fpv_events':labels,'fpv_primary':max(labels,key=lambda x:x[1])[0] if labels else 'LOW_ACTIVITY','fpv_confidence':max((v for _,v in labels),default=0.0)}
    def _director_vision_profile(self,timeline):
        """Heuristic temporal + spatial visual profile. Not semantic object/action recognition."""
        if not timeline:
            return {'vision_version':3,'roles':{},'moments':[],'confidence_note':'No usable samples.'}
        motions=[float(x.get('motion',0.0)) for x in timeline]
        events=[float(x.get('event',0.0)) for x in timeline]
        details=[float(x.get('detail',0.0)) for x in timeline]
        brightness=[float(x.get('brightness',0.0)) for x in timeline]
        scene_changes=[float(x.get('scene_change',0.0)) for x in timeline]
        mm,em,dm= sum(motions)/len(motions),sum(events)/len(events),sum(details)/len(details)
        moments=[]
        for i,row in enumerate(timeline):
            prev=timeline[max(0,i-1)]; nxt=timeline[min(len(timeline)-1,i+1)]
            motion=float(row.get('motion',0.0)); event=float(row.get('event',0.0))
            detail=float(row.get('detail',0.0)); bright=float(row.get('brightness',0.0))
            bchange=abs(bright-float(prev.get('brightness',bright)))
            dchange=abs(detail-float(prev.get('detail',detail)))
            mtrend=float(nxt.get('motion',motion))-motion
            sc=float(row.get('scene_change',0.0)); composition=row.get('composition','unknown')
            role='flow'; confidence=0.30; reason='Moderate movement profile'
            if sc>=0.48:
                role='possible_scene_change'; confidence=0.50; reason='Large sampled visual/spatial change; may be a cut, rapid movement, or major view change'
            elif motion<=max(7.0,mm*0.55) and event<0.12:
                role='breather_or_establishing'; confidence=0.42; reason='Low measured movement; could be atmosphere or an establishing view'
            elif event>=max(0.22,em*1.8) or (bchange>=18 and dchange>=10):
                role='possible_impact_or_change'; confidence=0.46; reason='Movement spike or visual-change proxy'
            elif motion>=max(28.0,mm*1.45) and event<0.18:
                role='dynamic_flow'; confidence=0.40; reason='High movement without a strong event proxy'
            elif mtrend>=8 and motion>=mm:
                role='possible_build'; confidence=0.35; reason='Movement increases across nearby samples'
            elif mtrend<=-8 and motion>=mm:
                role='possible_settle'; confidence=0.35; reason='Movement decreases across nearby samples'
            moments.append({'t':float(row.get('t',i)),'role':role,'confidence':confidence,'reason':reason,
                           'motion':round(motion,2),'event_proxy':round(event,3),'brightness_change':round(bchange,1),
                           'detail_change':round(dchange,1),'scene_change':round(sc,3),'composition':composition,
                           'spatial_balance':round(float(row.get('spatial_balance',0.0)),3)})
        roles={}
        for m in moments: roles[m['role']]=roles.get(m['role'],0)+1
        ranked=sorted((m for m in moments if m['role'] in ('possible_scene_change','possible_impact_or_change','dynamic_flow','possible_build','possible_settle')),
                     key=lambda m:(m['scene_change']*1.4+m['event_proxy']*1.5+m['motion']/100+m['brightness_change']/100+m['detail_change']/100),reverse=True)
        selected=[]
        for m in ranked:
            if all(abs(m['t']-x['t'])>=3.0 for x in selected):
                selected.append(m)
            if len(selected)>=12: break
        # Summarise the new FPV event vocabulary across the full sampled timeline.
        fpv_totals={}
        for row in timeline:
            for tag,confidence in row.get('fpv_events',[]): fpv_totals[tag]=fpv_totals.get(tag,0)+float(confidence)
        fpv_moments=[]
        for m in selected:
            row=timeline[min(len(timeline)-1,max(0,int(m.get('t',0))))]
            m['fpv_events']=row.get('fpv_events',[])
            m['fpv_primary']=row.get('fpv_primary','LOW_ACTIVITY')
            m['fpv_confidence']=row.get('fpv_confidence',0.0)
            fpv_moments.append(m)
        return {'vision_version':3,'roles':roles,'fpv_event_totals':fpv_totals,'moments':fpv_moments,
                'confidence_note':'v3 adds FPV event proxies from temporal pixel-change and spatial-change signals. Flow/building-motion/motion-spike/reveal-view-change/reversal-instability/close-pass candidate are heuristics, not semantic trick, gap or obstacle recognition.'}
    def _director_spatial_metrics(self,frame):
        """Measure coarse 3x3 image composition using grayscale samples."""
        w,h=192,108; cells=[]
        for gy in range(3):
            y0=gy*h//3; y1=(gy+1)*h//3
            for gx in range(3):
                x0=gx*w//3; x1=(gx+1)*w//3
                vals=[frame[y*w+x] for y in range(y0,y1) for x in range(x0,x1)]
                avg=sum(vals)/max(1,len(vals)); variance=sum((v-avg)**2 for v in vals)/max(1,len(vals))
                cells.append({'brightness':avg,'detail':math.sqrt(variance)})
        center=cells[4]['brightness']; periphery=sum(c['brightness'] for j,c in enumerate(cells) if j!=4)/8.0
        top=sum(c['brightness'] for c in cells[:3])/3.0; bottom=sum(c['brightness'] for c in cells[6:])/3.0
        left=sum(c['brightness'] for c in (cells[0],cells[3],cells[6]))/3.0
        right=sum(c['brightness'] for c in (cells[2],cells[5],cells[8]))/3.0
        balance=1.0-min(1.0,abs(left-right)/255.0+abs(top-bottom)/255.0)
        if center-periphery>18: comp='center_weighted'
        elif periphery-center>18: comp='periphery_weighted'
        elif top-bottom>18: comp='upper_weighted'
        elif bottom-top>18: comp='lower_weighted'
        elif left-right>18: comp='left_weighted'
        elif right-left>18: comp='right_weighted'
        else: comp='balanced_or_diffuse'
        return {'grid_brightness':[round(c['brightness'],1) for c in cells],
                'grid_detail':[round(c['detail'],1) for c in cells],
                'composition':comp,'spatial_balance':round(balance,3),
                'center_periphery_delta':round(center-periphery,1)}
    def analyze_video(self,path):
        # v18 Director Engine: one-second sampled profile, retained as reusable subclip data.
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-i',path,'-vf','fps=1/1,scale=192:108:flags=fast_bilinear,format=gray','-f','rawvideo','-y']
        frame_size=192*108; temp_path=None; proc=None
        try:
            fd,temp_path=tempfile.mkstemp(prefix='tmc_scan_v18_',suffix='.raw');os.close(fd);cmd.append(temp_path)
            proc=subprocess.Popen(self._localize_cmd(cmd),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**self._no_console_kwargs());self.scan_proc=proc;started=time.time()
            while proc.poll() is None:
                if self.scan_cancel.is_set():
                    proc.terminate()
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
                    raise RuntimeError('SCAN_CANCELLED')
                if time.time()-started>90:
                    proc.terminate()
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
                    raise RuntimeError(f'FFmpeg footage analysis timed out after 90 seconds: {Path(path).name}')
                time.sleep(0.1)
            if proc.returncode!=0:
                try:err=(proc.stderr.read() or b'').decode('utf-8','replace').strip()[:400]
                except Exception:err=''
                raise RuntimeError(f'FFmpeg frame analysis failed (exit {proc.returncode}) | {Path(path).name} | {err}')
            raw=Path(temp_path).read_bytes();frames=[raw[i:i+frame_size] for i in range(0,len(raw)-frame_size+1,frame_size)]
            if not frames:
                empty_timeline=[]
                return {'score':0.5,'brightness':0,'detail':0,'motion':0,'samples':0,'timeline':empty_timeline,'vision':self._director_vision_profile(empty_timeline),'analysis_version':13}
            timeline=[]; brightness=[];detail=[];motion=[];event_scores=[]
            for i,f in enumerate(frames):
                vals=list(f);mean=sum(vals)/len(vals);det=math.sqrt(sum((v-mean)**2 for v in vals)/len(vals));brightness.append(mean);detail.append(det)
                mot=0.0;event=0.0
                if i:
                    a=frames[i-1];step=max(1,len(a)//6000);diffs=[abs(a[j]-f[j]) for j in range(0,len(a),step)];mot=sum(diffs)/len(diffs);motion.append(mot)
                    # Motion spike + visual-change proxy. Not action recognition.
                    event=min(1.0,max(0.0,(mot-12)/40.0)+max(0.0,(abs(det-detail[-2])-8)/45.0))
                event_scores.append(event)
                spatial=self._director_spatial_metrics(f)
                timeline.append({'t':float(i),'brightness':round(mean,1),'detail':round(det,2),'motion':round(mot,2),'motion_var':0.0,'event':round(event,3),**spatial})
            for i,row in enumerate(timeline):
                if i==0: row['scene_change']=0.0; row['spatial_change']=0.0
                else:
                    prev_grid=timeline[i-1].get('grid_brightness',[]); curr_grid=row.get('grid_brightness',[])
                    spatial_delta=sum(abs(a-b) for a,b in zip(prev_grid,curr_grid))/max(1,len(curr_grid))/255.0
                    global_delta=abs(row['brightness']-timeline[i-1]['brightness'])/255.0
                    detail_delta=abs(row['detail']-timeline[i-1]['detail'])/100.0
                    row['spatial_change']=round(spatial_delta,3)
                    row['scene_change']=round(min(1.0,0.55*spatial_delta+0.25*global_delta+0.20*detail_delta),3)
            overall_b=sum(brightness)/len(brightness);overall_d=sum(detail)/len(detail);overall_m=sum(motion)/len(motion) if motion else 0.0
            mvar=sum(abs(v-overall_m) for v in motion)/len(motion) if motion else 0.0
            # Rolling variability per sample for subclip ranking.
            for i,row in enumerate(timeline):
                neighborhood=motion[max(0,i-2):min(len(motion),i+3)]
                row['motion_var']=round(sum(abs(v-(sum(neighborhood)/len(neighborhood))) for v in neighborhood)/len(neighborhood),2) if neighborhood else 0.0
            # FPV temporal interpretation pass: compare adjacent sampled movement, then add confidence-scored event proxies.
            for i,row in enumerate(timeline):
                prev_motion=float(timeline[max(0,i-1)].get('motion',row.get('motion',0)))
                next_motion=float(timeline[min(len(timeline)-1,i+1)].get('motion',row.get('motion',0)))
                row['motion_trend']=round(next_motion-prev_motion,2)
                row.update(self._vision_fpv_interpret(row))
            exposure=max(0.0,1.0-abs(overall_b-120)/130);detail_score=min(1.0,overall_d/65);motion_score=min(1.0,overall_m/35);variability_score=min(1.0,mvar/22);event_score=min(1.0,sum(event_scores)/max(1,len(event_scores))*2)
            score=0.28*exposure+0.22*detail_score+0.18*motion_score+0.14*variability_score+0.18*event_score
            return {'score':round(score,3),'brightness':round(overall_b,1),'detail':round(overall_d,1),'motion':round(overall_m,1),'motion_variability':round(mvar,1),'event_candidates':round(event_score,3),'samples':len(frames),'timeline':timeline,'vision':self._director_vision_profile(timeline),'analysis_version':13}
        finally:
            self.scan_proc=None
            if temp_path:
                try:Path(temp_path).unlink(missing_ok=True)
                except Exception:pass
    def cancel_scan(self):
        if self.job_type=='scan' and self.running:
            self.scan_cancel.set(); self.progress_text.set('Cancelling scan…'); self._log('Scan cancellation requested; stopping FFmpeg analysis immediately.')
            p=getattr(self,'scan_proc',None)
            if p and p.poll() is None:
                try: p.terminate()
                except Exception: pass
    def scan_worker(self,folder,finish=True):
        try:
            allfiles=[p for p in Path(folder).rglob('*') if p.is_file()]
            files=[str(p) for p in allfiles if p.suffix.lower() in VIDEO_EXTS]
            ignored=len(allfiles)-len(files)
            cachepath=self.library_path(folder); cached={}
            if cachepath.exists():
                try: cached=json.loads(cachepath.read_text(encoding='utf-8')).get('files',{})
                except Exception: cached={}
            updated={}; changed=0; errors=0; total=len(files)
            self.q.put(('log',f'v{APP_VERSION} VISION BRAIN FPV SCAN: {total} supported video files; {ignored} non-video files ignored. Cached metrics will be reused. Per-file timeout: 60 seconds.'))
            if total==0:
                if finish: self.q.put(('done',False))
                return False
            for i,f in enumerate(files,1):
                if self.scan_cancel.is_set(): break
                reused=False
                try:
                    st=os.stat(f); key=str(Path(f).resolve()); old=cached.get(key)
                    if old and old.get('timeline') and old.get('analysis_version')==13 and old.get('size')==st.st_size and old.get('mtime')==st.st_mtime: metric=old; reused=True
                    else: metric=self.analyze_video(f); metric.update({'size':st.st_size,'mtime':st.st_mtime,'name':Path(f).name}); changed+=1; reused=False
                    updated[key]=metric
                    if metric.get('error'): errors+=1
                except Exception as e:
                    if self.scan_cancel.is_set() or 'SCAN_CANCELLED' in str(e):
                        break
                    errors+=1
                    try:updated[str(Path(f).resolve())]={'score':0.45,'size':os.path.getsize(f),'mtime':os.path.getmtime(f),'name':Path(f).name,'error':str(e)[:180]}
                    except: pass
                self.q.put(('progress',i,total,f'{i}/{total} — '+Path(f).name+(' (cached)' if locals().get('reused',False) else '')))
            # Preserve cached index entries for files not processed due to cancellation; fresh scan will handle them next time.
            if self.scan_cancel.is_set():
                for k,v in cached.items():
                    if k not in updated: updated[k]=v
                self.q.put(('log',f'Scan cancelled. Retained {len(updated)} completed/cached entries; partial index saved.'))
            cachepath.write_text(json.dumps({'version':13,'analysis':'v19.6.0-fpv-interpretation-v3','updated':time.time(),'files':updated},indent=2),encoding='utf-8')
            try:
                vision_path=Path(folder)/'TMC-FPV_Vision_Brain_FPV_v3_Report.txt'
                lines=[f'TMC-FPV AutoEditor v{APP_VERSION} — VISION BRAIN FPV INTERPRETATION v3 REPORT','',f'Video files indexed: {len(updated)}','', 'FPV INTERPRETATION COUNTS (heuristic event proxies)']
                totals={}
                for item in updated.values():
                    for role,count in (item.get('vision',{}).get('roles',{}) or {}).items(): totals[role]=totals.get(role,0)+int(count)
                lines.extend([f'- {role}: {count}' for role,count in sorted(totals.items())] or ['- No role data available'])
                fpv_totals={}
                for item in updated.values():
                    for tag,value in (item.get('vision',{}).get('fpv_event_totals',{}) or {}).items(): fpv_totals[tag]=fpv_totals.get(tag,0.0)+float(value)
                lines += ['', 'FPV EVENT PROXY TOTALS (confidence-weighted, not literal manoeuvre counts)']
                lines.extend([f'- {tag}: {value:.2f}' for tag,value in sorted(fpv_totals.items(),key=lambda x:x[1],reverse=True)] or ['- No FPV proxy totals'])
                lines += ['', 'TOP MOMENT CANDIDATES (FPV event proxies + composition heuristics)']
                candidates=[]
                for item in updated.values():
                    for moment in item.get('vision',{}).get('moments',[]) or []:
                        candidates.append((item.get('name','Unknown video'),moment))
                candidates.sort(key=lambda pair: pair[1].get('event_proxy',0)*1.5+pair[1].get('motion',0)/100+pair[1].get('brightness_change',0)/100+pair[1].get('detail_change',0)/100,reverse=True)
                for name,m in candidates[:40]: lines.append(f"- {name} @ {m.get('t',0):.1f}s | {m.get('role')} | FPV proxy {m.get('fpv_primary','unknown')} ({m.get('fpv_confidence',0):.2f}) | composition {m.get('composition','unknown')} | balance {m.get('spatial_balance',0):.3f} | scene-change {m.get('scene_change',0):.3f} | confidence {m.get('confidence',0):.2f} | motion {m.get('motion',0):.1f} | event proxy {m.get('event_proxy',0):.3f} | {m.get('reason','')}")
                lines += ['', 'LIMITATIONS', 'This is a low-resolution grayscale temporal/spatial heuristic. FPV event labels are proxies (flow, acceleration, change/reveal candidates, reversal/instability and close-passage candidates), not reliable trick, gap, obstacle or semantic recognition. Optical flow is not calculated; pixel-change and spatial-change signals may confuse camera movement with events.']
                vision_path.write_text('\n'.join(lines),encoding='utf-8')
                self.q.put(('log',f'DIRECTOR VISION REPORT SAVED: {vision_path}'))
            except Exception as vision_exc:
                self.q.put(('log',f'Director Vision report could not be saved: {vision_exc}'))
            self.q.put(('log',f'v{APP_VERSION} VISION BRAIN FPV SUMMARY: {changed} newly analysed; cache reused for {max(0,len(updated)-changed)}; errors {errors}; index: {cachepath}'))
            ok=not self.scan_cancel.is_set() and bool(updated)
            if finish: self.q.put(('done',ok))
            return ok
        except Exception as e:
            self.q.put(('log','Library scan error: '+str(e)))
            if finish: self.q.put(('done',False))
            return False
    def worker(self,folder,song,output,minlen,maxlen,resolution,aspect_ratio,retro,seedstr,mode,quality,fadein,fadeout,useintro,intro_path,intro_duration_str,random_transitions,transition_strength,vertical_mode,output_fps,single_source_order,highlight_entries,artistic_mode=False,music_trim=None,turn_it_up=False):
        success=False;temp=None; stage_times=[]; stage_name='Startup'; stage_clock=time.time()
        def stage(new_name):
            nonlocal stage_name,stage_clock
            now=time.time(); stage_times.append((stage_name,now-stage_clock)); stage_name=new_name; stage_clock=now
            self.q.put(('log',f'Stage started: {new_name}'))
        fps=50 if output_fps.startswith('50') else (60 if output_fps.startswith('60') else 30)
        try:
            rng=random.Random(int(seedstr)) if seedstr else random.Random()
            # v18.0 source-boundary guard: for longer source videos, avoid the first/last
            # two seconds where cameras often contain launch/stop/handling material.
            def source_bounds(source_duration):
                if source_duration > 12.0:
                    return (2.0, max(2.0, source_duration-2.0))
                return (0.0, source_duration)
            if artistic_mode: self.q.put(('log','Artistic Mode enabled: restrained creative treatments and expanded transition choices will be used where applicable.'))
            if turn_it_up: self.q.put(('log','TURN IT UP TO ELEVEN enabled: intensifying the planned edit without rerolling its selected moments or music structure.'))
            transitions_available=False
            if random_transitions or turn_it_up:
                try:
                    filters=subprocess.run([self._ffmpeg_exe(),'-hide_banner','-filters'],capture_output=True,text=True,check=True,**self._no_console_kwargs()).stdout
                    transitions_available=any(len(line.split())>1 and line.split()[1]=='xfade' for line in filters.splitlines())
                except Exception:
                    transitions_available=False
                if not transitions_available:
                    self.q.put(('log','WARNING: FFmpeg xfade filter unavailable. Random transitions will safely fall back to hard cuts.'))
            stage('Source discovery and probing'); self.q.put(('overall',3,'Pre-flight / locating source footage'))
            # Auto-scan the footage folder when the Director Engine scan index is missing/empty.
            cachepath=self.library_path(folder)
            index={}
            if cachepath.exists():
                try: index=json.loads(cachepath.read_text(encoding='utf-8')).get('files',{})
                except Exception: index={}
            if not index:
                self.q.put(('log','FOOTAGE SCAN LOG NOT FOUND: Automatically scanning the selected footage folder before generation.'))
                self.q.put(('overall',4,'Automatic footage scan — building Director Engine profiles'))
                scan_ok=self.scan_worker(folder,finish=False)
                if not scan_ok:
                    raise RuntimeError('Automatic footage scan failed or was cancelled. Run Scan Footage manually and review the scan log.')
                try: index=json.loads(cachepath.read_text(encoding='utf-8')).get('files',{})
                except Exception: index={}
                if not index: raise RuntimeError('Automatic footage scan completed but no scan index was created.')
                self.q.put(('log',f'AUTOMATIC FOOTAGE SCAN COMPLETE: {len(index)} profiles available. Continuing generation.'))
            files=[str(p) for p in Path(folder).rglob('*') if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
            if not files:raise RuntimeError('No supported video files found in the selected folder.')
            rng.shuffle(files);self.q.put(('overall',7,'Source files found'));self.q.put(('log',f'Found {len(files)} video files. Reading durations and visual scores…'))
            cachepath=self.library_path(folder)
            usable=[]
            for fi,f in enumerate(files,1):
                self.q.put(('overall',7+12*fi/max(1,len(files)),f'Checking source durations {fi}/{len(files)}'))
                try:
                    d=self.probe_duration(f)
                    if d>1.5:
                        metric=index.get(str(Path(f).resolve()),{})
                        usable.append((f,d,float(metric.get('score',0.5))))
                except Exception:self.q.put(('log',f'Skipping unreadable file: {Path(f).name}'))
            if not usable:raise RuntimeError('Could not read any usable source videos.')
            if not index: raise RuntimeError('Footage library scan index is empty or unavailable. Automatic scan did not produce usable profiles.')
            usable=[(f,d,float(index.get(str(Path(f).resolve()),{}).get('score',0.5))) for f,d,_ in usable]
            self.q.put(('overall',20,'Source analysis complete'));self.q.put(('log',f'Visual scores loaded for {len(usable)} sources.'))
            stage('Music analysis'); self.q.put(('overall',22,'Analysing music'));source_song_duration=self.probe_duration(song); songdur=source_song_duration; music_trim_segments=[]; trimmed_music=False; trimmed_audio_path=None
            if music_trim:
                for requested_start,requested_end,start_text,end_text in music_trim:
                    if requested_end>source_song_duration+0.01: raise RuntimeError(f'Music trim end {end_text} exceeds selected track duration ({source_song_duration:.2f}s).')
                    if requested_start>=source_song_duration: raise RuntimeError(f'Music trim start {start_text} is beyond the end of the selected track.')
                    music_trim_segments.append((requested_start,min(requested_end,source_song_duration),start_text,end_text))
                trimmed_music=True; crossfade=0.5 if len(music_trim_segments)>1 else 0.0
                core_duration=sum(e-a for e,a,_,_ in []) if False else sum(e-s for s,e,_,_ in music_trim_segments)-crossfade*(len(music_trim_segments)-1)
                songdur=core_duration+min(2.0,music_trim_segments[0][0])+min(2.0,source_song_duration-music_trim_segments[-1][1])
                if core_duration<0.25: raise RuntimeError('Combined selected music sections are too short to edit safely.')
                self.q.put(('log',f'MUSIC TRIM ACTIVE: {Path(song).name} | {len(music_trim_segments)} segment(s), {core_duration:.2f}s core after crossfades, buffer/fades applied.'))
            else: self.q.put(('log','Full-track music mode: original soundtrack is used without trimming or fades.'))
            cues=self._detect_transients_trim_aware(song,songdur,music_trim_segments[0][0] if trimmed_music else 0.0);self.q.put(('overall',28,'Music analysis complete'))
            intro_dur=0.0
            if useintro and intro_path:
                if not Path(intro_path).is_file(): raise RuntimeError('Selected intro/logo file is missing. Browse for it again or untick intro.')
                is_still=Path(intro_path).suffix.lower() in {'.png','.jpg','.jpeg'}
                if is_still:
                    try: intro_dur=float(intro_duration_str)
                    except ValueError: raise RuntimeError('Still-logo display duration must be a number of seconds.')
                    if intro_dur<=0: raise RuntimeError('Logo display duration must be greater than zero.')
                else:
                    intro_dur=self.probe_duration(intro_path)
                intro_dur=min(intro_dur,songdur)
                self.q.put(('log',f'Optional intro enabled: {Path(intro_path).name} for {intro_dur:.2f}s.'))
            elif useintro and not intro_path:
                self.q.put(('log','Intro checkbox is on but no file selected; skipping intro safely.'))
            main_song_duration=max(0.0,songdur-intro_dur)
            self.q.put(('overall',30,'Planning clip sequence'));self.q.put(('log',f'Song {songdur:.1f}s. Building {mode} edit from {len(usable)} usable sources at {fps}fps.'))
            base={'720p':720,'1080p':1080,'1440p':1440}.get(resolution,720)
            if aspect_ratio=='9:16 Vertical (crop)': width,height=base,int(base*16/9)
            elif aspect_ratio=='1:1 Square': width,height=base,base
            else: width,height=int(base*16/9),base
            chronological_mode=(single_source_order=='Chronological')
            stage('Director analysis'); self.q.put(('overall',30,'Building director music map'))
            music_sections=self._director_music_profile(song,main_song_duration)
            self.q.put(('overall',33,'Music narrative map complete'))
            stage('Director edit plan'); self.q.put(('log',f'v{APP_VERSION} Director refinement: arc-aware transitions preserved, source diversity and short-run visual-pattern repetition awareness enabled, WOW payoffs and decision reporting retained.'))
            segments=self._director_plan(usable,index,music_sections,cues,main_song_duration,minlen,maxlen,mode,rng,source_bounds,chronological_mode)
            if not segments: raise RuntimeError('Director Engine could not produce a usable edit plan.')
            remaining=max(0.0,main_song_duration-sum(float(s[2]) for s in segments))
            if remaining>0.08:
                # Protect the exact music duration with a real source tail, extending the last clip if possible.
                src0,start0,dur0=segments[-1]; source_d=next((d for f,d,_ in usable if f==src0),start0+dur0);lo0,hi0=source_bounds(source_d)
                extend=min(remaining,max(0.0,hi0-(start0+dur0)))
                if extend>0.05:segments[-1]=(src0,start0,dur0+extend);remaining-=extend
            if remaining>0.05:
                tail_candidates=[u for u in usable if source_bounds(u[1])[1]-source_bounds(u[1])[0]>=remaining]
                tail_candidates=tail_candidates or sorted(usable,key=lambda u:source_bounds(u[1])[1]-source_bounds(u[1])[0],reverse=True)
                src0,d0,sc0=rng.choice(tail_candidates);lo0,hi0=source_bounds(d0);tail_len=min(remaining,hi0-lo0);tail_start=rng.uniform(lo0,max(lo0,hi0-tail_len))
                if tail_len>0.05:segments.append((src0,tail_start,tail_len));remaining-=tail_len
            if remaining>0.05: raise RuntimeError(f'Director plan could not cover final {remaining:.2f}s of soundtrack with real footage.')
            # Avoid an accidental flash-frame tail: merge a very short final slot into
            # the preceding clip when that source has enough unused footage available.
            if len(segments)>1 and float(segments[-1][2])<1.05:
                psrc,pstart,pdur=segments[-2]; psource_d=next((d for f,d,_ in usable if f==psrc),pstart+pdur)
                _,pbound_end=source_bounds(psource_d)
                short_tail=float(segments[-1][2])
                if pstart+pdur+short_tail<=pbound_end+0.001:
                    segments[-2]=(psrc,pstart,pdur+short_tail);segments.pop()
                    self.q.put(('log',f'v{APP_VERSION} short final clip merged into preceding shot ({short_tail:.2f}s); avoided sub-1.05s flash cut.'))
            self.q.put(('log',f'Director plan summary: {len(segments)} clips; estimated average duration {sum(float(s[2]) for s in segments)/len(segments):.2f}s; sources {len(set(s[0] for s in segments))}; arc-based selection complete.'))
            # v19 report is written after highlight overrides so it reflects the final plan.
            # v17.8: force user-specified moments into the timeline by anchoring
            # selected planned clip slots around their timestamps. Timeline length
            # and soundtrack timing remain unchanged.
            if highlight_entries:
                if len(highlight_entries)>len(segments):
                    raise RuntimeError(f'{len(highlight_entries)} highlights were entered, but only {len(segments)} clip slots were planned. Shorten the schedule or use a longer soundtrack.')
                matched=[]
                for filename,stamp,display_stamp in highlight_entries:
                    requested_stem=Path(filename).stem.lower()
                    matches=[item for item in usable if Path(item[0]).stem.lower()==requested_stem]
                    if not matches:
                        raise RuntimeError(f'Highlight source not found: {filename}')
                    if len(matches)>1:
                        raise RuntimeError(f'Highlight filename is ambiguous (duplicates in subfolders): {filename}. Use a unique filename.')
                    src,dur,score=matches[0]
                    safe_start,safe_end=source_bounds(dur)
                    if stamp>=dur:
                        raise RuntimeError(f'Highlight timestamp {display_stamp} is beyond the end of {filename} ({dur:.2f}s).')
                    safe_stamp=max(safe_start,min(stamp,safe_end-0.01))
                    if safe_stamp!=stamp:
                        self.q.put(('log',f'Highlight {filename} at {display_stamp} adjusted to avoid the first/last two seconds of a long source.'))
                    matched.append((src,safe_stamp,dur,filename,display_stamp))
                # Spread highlight substitutions across the edit, rather than clustering them.
                slot_indices=[]
                if len(matched)==1: slot_indices=[len(segments)//2]
                else: slot_indices=[round(i*(len(segments)-1)/(len(matched)-1)) for i in range(len(matched))]
                for slot,(src,stamp,source_dur,filename,display_stamp) in zip(slot_indices,matched):
                    slot_dur=float(segments[slot][2])
                    if slot_dur<=0.05: raise RuntimeError(f'Cannot create highlight clip for {filename}.')
                    if (source_bounds(source_dur)[1]-source_bounds(source_dur)[0])+0.001<slot_dur:
                        safe_len=source_bounds(source_dur)[1]-source_bounds(source_dur)[0]
                        raise RuntimeError(f'Highlight source {filename} is shorter than the selected clip duration ({safe_len:.2f}s usable after source-end trimming, {slot_dur:.2f}s needed).')
                    # Keep the target moment near the middle of the chosen clip;
                    # clamp to source boundaries without shortening the timeline slot.
                    safe_start,safe_end=source_bounds(source_dur)
                    start=max(safe_start,min(stamp-slot_dur/2,safe_end-slot_dur))
                    if not (start<=stamp<start+slot_dur):
                        start=max(safe_start,min(stamp-slot_dur/2,safe_end-slot_dur))
                    segments[slot]=(src,start,slot_dur)
                    self.q.put(('log',f'v{APP_VERSION} highlight override applied: {filename} at {display_stamp} in timeline clip {slot+1}/{len(segments)}.'))
            # v19.5.0 Storyboard prototype: review and optionally replace planned clips before render/report.
            try:
                review_event=threading.Event()
                self.q.put(('storyboard',segments,usable,review_event))
                self.q.put(('log','Storyboard review opened — waiting for approval or clip replacements.'))
                while not review_event.wait(0.2):
                    if self.render_cancel.is_set(): raise RuntimeError('RENDER_CANCELLED')
                if getattr(self,'_storyboard_open_failed',False): raise RuntimeError('Storyboard review failed to open; rendering blocked.')
            except RuntimeError: raise
            except Exception as storyboard_exc:
                raise RuntimeError(f'STORYBOARD REVIEW REQUIRED — render blocked: {storyboard_exc}')
            # v19.6.0 Final Edit Decision Report: report the actual post-override timeline.
            try:
                report_path=Path(output).with_suffix('').parent/(Path(output).stem+'_Director_Report.txt')
                decisions=list(getattr(self,'last_director_decisions',[]))
                # Align report entries to the final rendered segment list, including tail repairs and highlight overrides.
                while len(decisions)<len(segments):
                    i=len(decisions);src,start,dur=segments[i]
                    decisions.append({'time':sum(float(x[2]) for x in segments[:i]),'duration':float(dur),'start':float(start),'source':Path(src).name,'arc':'timeline repair','target':'continuity','motion':0.0,'motion_raw':0.0,'event':'unknown','event_strength':0.0,'progression':'unknown','score':0.0,'role_fit':0.0,'cut_cue':'Tail coverage repair','cut_cue_time':None,'wow_rank':0,'wow_score':0.0,'payoff':False})
                decisions=decisions[:len(segments)]
                for i,(src,start,dur) in enumerate(segments):
                    d=decisions[i]
                    changed=(Path(src).name!=d.get('source') or abs(float(start)-float(d.get('start',start)))>0.01)
                    d['source']=Path(src).name;d['start']=float(start);d['duration']=float(dur)
                    if changed:d['override']='Highlight schedule / final timeline adjustment'
                state_counts={}
                for d in decisions:state_counts[d.get('arc','unknown')]=state_counts.get(d.get('arc','unknown'),0)+1
                report_lines=[f'TMC-FPV AutoEditor v{APP_VERSION} — DIRECTOR EDIT DECISION REPORT','',f'Output: {Path(output).name}',f'Editing style: {mode}',f'Music duration: {main_song_duration:.2f}s',f'Final timeline clips: {len(segments)}',f'Unique sources: {len(set(seg[0] for seg in segments))}','', 'NARRATIVE ARC OVERVIEW']
                report_lines += [f'- {state}: {count} clips' for state,count in state_counts.items()]
                report_lines += ['', 'WOW MOMENTS IDENTIFIED']
                used_wow=[d for d in decisions if d.get('wow_rank',0) and not d.get('override')]
                for moment in getattr(self,'wow_moments',[]):
                    deployments=[d for d in used_wow if d.get('wow_rank')==moment.get('rank')]
                    status=f'USED in timeline at {deployments[0]["time"]:.2f}s' if deployments else 'reserved candidate; not selected in final timeline'
                    report_lines.append(f'#{moment["rank"]} | {moment["source"]} | source {moment["start"]:.1f}s | {moment["event"]} | WOW {moment["score"]:.2f} | {status}')
                report_lines += ['', 'SHOT-BY-SHOT EDIT DECISIONS']
                for i,d in enumerate(decisions,1):
                    cue=d.get('cut_cue') or 'Director timing'
                    cue_time=d.get('cut_cue_time')
                    cue_str=f'{cue} at {cue_time:.2f}s' if isinstance(cue_time,(int,float)) else cue
                    reasoning={'breather':'low-intensity, smoother movement and reduced event pressure','opening':'establishing/controlled movement to introduce the edit','flow':'balanced sustained movement for continuity','build':'rising movement, variation or event intensity to increase momentum','peak':'high-motion/event footage for musical impact','finale':'payoff-oriented footage for the closing section'}.get(d.get('arc'),'continuity')
                    extra=f' | OVERRIDE: {d["override"]}' if d.get('override') else ''
                    report_lines.append(f'{i:02d}. Timeline {d["time"]:.2f}-{d["time"]+d["duration"]:.2f}s ({d["duration"]:.2f}s) | Arc {d.get("arc","unknown")} / role {d.get("target","unknown")} | {d["source"]} source {d.get("start",0):.2f}s | cut cue: {cue_str} | visual motion {d.get("motion",0):.2f} (raw {d.get("motion_raw",0):.1f}) | event {d.get("event","unknown")} ({d.get("event_strength",0):.2f}) | FPV proxy {d.get("fpv_primary","n/a")} ({d.get("fpv_strength",0):.2f}) | progression {d.get("progression","unknown")} | role fit {d.get("role_fit",0):.3f} | candidate score {d.get("score",0):.3f} | WOW #{d.get("wow_rank",0)} payoff={d.get("payoff",False)} | intent: {reasoning}{extra}')
                report_lines += ['', 'INTERPRETATION / LIMITATIONS', 'Arc roles now influence visual selection separately from the editing-style preset. Fast-cut mode changes pacing/intensity without overriding narrative role matching. Visual movement and event values remain heuristic proxies, not semantic manoeuvre recognition. Cut-cue labels record the cue selected by the timing logic; they do not claim every edit is caused by an audio cue. The report reflects the final timeline after user highlight substitutions and tail coverage repairs.']
                report_path.write_text('\n'.join(report_lines),encoding='utf-8')
                self.q.put(('log',f'v{APP_VERSION} DIRECTOR REPORT SAVED: {report_path}'))
            except Exception as report_exc:
                self.q.put(('log',f'Director report could not be saved: {report_exc}'))
            crf={'Standard (CRF 23)':23,'High (CRF 20)':20,'Very high (CRF 18)':18}.get(quality,20)
            stage('Clip planning'); temp=Path(tempfile.mkdtemp(prefix='tmcfpv_autoeditor_v19_0_'));self.q.put(('overall',35,'Clip plan complete'));self.q.put(('log',f'Preparing {len(segments)} clips…'));self.q.put(('progress',0,len(segments),'Rendering clips: 0/'+str(len(segments))))
            stage('Clip rendering'); concatfile=temp/'concat.txt'; last_artistic_effect=None
            with concatfile.open('w',encoding='utf-8') as cf:
                for i,(src,start,dur) in enumerate(segments,1):
                    if self.render_cancel.is_set(): raise RuntimeError('RENDER_CANCELLED')
                    clip=temp/f'clip_{i:04d}.mp4'
                    # Detect vertical source aspect ratio. Horizontal clips keep the v10 treatment.
                    try:
                        srcw,srch=self.probe_video_dimensions(src)
                    except Exception:
                        srcw,srch=width,height
                    if aspect_ratio!='16:9 Landscape':
                        vf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1'
                    elif abs((srcw/srch)-(16/9))>0.02:
                        # v17.6: all non-16:9 source footage receives fit/fill handling.
                        if vertical_mode=='Original (fit)':
                            vf=f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps},setsar=1'
                        elif srch>srcw:
                            # Portrait: 50% zoom means 150% of fit scale, centred.
                            fit_scale=min(width/srcw,height/srch); zoom_scale=fit_scale*1.5
                            sw=max(1,int(srcw*zoom_scale)); sh=max(1,int(srch*zoom_scale))
                            vf=f'scale={sw}:{sh},crop={width}:{height},fps={fps},setsar=1'
                        else:
                            # 4:3 and other non-portrait non-16:9 footage fill the frame when zoom is enabled.
                            vf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1'
                    else:
                        vf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1'
                    if retro:vf+=',eq=saturation=0.58:contrast=0.84:brightness=0.035,colorbalance=rs=0.065:gs=0.025:bs=-0.045,gblur=sigma=0.30,noise=alls=14:allf=t,vignette=PI/5'
                    elif turn_it_up: vf+=',eq=contrast=1.12:saturation=1.12,unsharp=5:5:0.45:3:3:0.0'
                    # Artistic Mode v17.9: restrained per-clip treatments, one at most,
                    # no consecutive repeats; avoid stacking on the retro treatment.
                    if artistic_mode and not retro:
                        artistic_pool=[
                            ('monochrome','hue=s=0'),
                            ('warm cinematic grade','colorbalance=rs=0.12:gs=0.025:bs=-0.085'),
                            ('cool cinematic grade','colorbalance=rs=-0.075:gs=0.025:bs=0.10'),
                            ('punchy contrast','eq=contrast=1.22:saturation=1.28'),
                            ('soft faded look','eq=contrast=0.86:saturation=0.72:brightness=0.035'),
                            ('vignette','vignette=PI/3'),
                            ('film grain','noise=alls=18:allf=t'),
                            ('sepia tone','colorchannelmixer=rr=0.393:rg=0.769:rb=0.189:gr=0.349:gg=0.686:gb=0.168:br=0.272:bg=0.534:bb=0.131'),
                            ('vivid colour','eq=saturation=1.35:contrast=1.08'),
                            ('cool shadow tint','colorbalance=rs=-0.06:bs=0.12:rm=-0.025:bm=0.06')
                        ]
                        if rng.random()<(0.62 if turn_it_up else 0.33):
                            choices=[item for item in artistic_pool if item[0]!=last_artistic_effect] if 'last_artistic_effect' in locals() else artistic_pool
                            chosen_effect=rng.choice(choices)
                            vf+=','+chosen_effect[1]
                            last_artistic_effect=chosen_effect[0]
                            self.q.put(('log',f'Artistic treatment: {chosen_effect[0]} on clip {i}/{len(segments)}'))
                    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',f'{start:.3f}','-i',src,'-t',f'{dur:.3f}','-an','-vf',vf,*self.video_encoder_args(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(clip)]
                    self.run_render_process(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                    s=str(clip).replace('\\','/').replace("'","'\\''");cf.write("file '"+s+"'\n")
                    # Storyboard thumbs were extracted from source footage before approval/render.
                    self.q.put(('overall',35+40*i/max(1,len(segments)),f'Rendering clips {i}/{len(segments)}'));self.q.put(('progress',i,len(segments),f'Rendering clips: {i}/{len(segments)}'));
                    if i%5==0 or i==len(segments):self.q.put(('log',f'Rendered {i}/{len(segments)} clips'))
            stage('Final montage assembly / transitions'); silent=temp/'montage.mp4'
            self.q.put(('overall',77,'Assembling montage / transitions'))
            if segments:
                if random_transitions and transitions_available and len(segments)>1:
                    # Random short xfade transitions between montage clips only; intro is concatenated separately later.
                    trans_names=['fade','dissolve','wipeleft','wiperight','slideleft','slideright']
                    if artistic_mode or turn_it_up:
                        # Artistic transition names from FFmpeg's xfade family; still selected sparingly.
                        trans_names += ['circleopen','circleclose','radial','pixelize','hblur','fadeblack','fadewhite','smoothleft','smoothright','smoothup','smoothdown','wipeup','wipedown','zoomin']
                    strength_cfg={'Subtle':0.20,'Balanced':0.42,'Strong':0.65,'Heavy':0.85}
                    if turn_it_up: strength_cfg={'Subtle':0.36,'Balanced':0.58,'Strong':0.78,'Heavy':0.92}
                    base_probability=strength_cfg.get(transition_strength,0.42)
                    if artistic_mode: base_probability=min(0.95,base_probability+0.18)
                    filter_parts=[]; current='v0'; accumulated=float(segments[0][2]); last_transition=None; transition_count=0; transition_duration_total=0.0; transition_log_counts={}
                    for idx in range(len(segments)):
                        filter_parts.append(f'[{idx}:v]setpts=PTS-STARTPTS,fps={fps},settb=AVTB,setsar=1,format=yuv420p[v{idx}]')
                    # Adaptive transition policy uses the upcoming narrative arc as a music-energy proxy.
                    arc_policy={'breather':(0.80,0.55,['fade','dissolve','fadeblack']),'release':(0.72,0.48,['fade','dissolve','fadeblack']),'recovery':(0.68,0.42,['fade','dissolve']),'flow':(0.48,0.28,['fade','dissolve','smoothleft','smoothright']),'build':(0.32,0.18,['wipeleft','wiperight','slideleft','slideright']),'peak':(0.18,0.12,['wipeleft','wiperight','slideleft','slideright']),'finale':(0.25,0.16,['fade','wipeleft','wiperight'])}
                    transition_notes=[]
                    for idx in range(1,len(segments)):
                        outlabel=f'x{idx}'; arc=decisions[idx].get('arc','flow').lower() if idx<len(decisions) else 'flow'
                        multiplier,dur,types=arc_policy.get(arc,(0.45,0.24,['fade','dissolve','wipeleft','wiperight']))
                        chance=min(0.95,max(0.05,base_probability*multiplier))
                        types=list(types)
                        if artistic_mode and arc in ('build','peak','finale'): types+=['circleopen','radial','pixelize','hblur','smoothup','smoothdown','wipeup','wipedown','zoomin']
                        if rng.random()>=chance:
                            filter_parts.append(f'[{current}][v{idx}]concat=n=2:v=1:a=0[{outlabel}]'); accumulated+=float(segments[idx][2]); transition_notes.append(f'{idx+1}: hard cut ({arc})')
                        else:
                            options=[t for t in types if t!=last_transition] or types; trans=rng.choice(options); last_transition=trans; transition_count+=1; transition_duration_total+=dur; transition_log_counts[arc]=transition_log_counts.get(arc,0)+1
                            offset=max(0.0,accumulated-dur); filter_parts.append(f'[{current}][v{idx}]xfade=transition={trans}:duration={dur:.3f}:offset={offset:.3f}[{outlabel}]'); accumulated+=float(segments[idx][2])-dur; transition_notes.append(f'{idx+1}: {trans} {dur:.2f}s ({arc})')
                        current=outlabel
                    filtergraph=';'.join(filter_parts)
                    transition_inputs=[]
                    for i,cliprow in enumerate(segments): transition_inputs.extend(['-i',str(temp/f'clip_{i+1:04d}.mp4')])
                    estimated_montage_duration=max(0.1,sum(float(row[2]) for row in segments)-transition_duration_total)
                    assembly_cmd=['ffmpeg','-hide_banner','-loglevel','error','-y',*transition_inputs,'-filter_complex',filtergraph,'-map',f'[{current}]','-an',*self.video_encoder_args(crf),'-pix_fmt','yuv420p',str(silent)]
                    self.run_ffmpeg_assembly_progress(assembly_cmd,estimated_montage_duration)
                    self.q.put(('log',f'Audio-led adaptive transitions applied: base strength={transition_strength}; arc counts={transition_log_counts}; {transition_count} transitions; {transition_duration_total:.2f}s total overlap. Breathers use softer/longer dissolves; builds and peaks favour short wipes/hard cuts. Artistic Mode: {artistic_mode}.'))
                else:
                    if random_transitions and len(segments)>1 and not transitions_available:
                        self.q.put(('log','Transition fallback active: hard cuts used to prevent FFmpeg filter failure.'))
                    self.run_ffmpeg_assembly_progress(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concatfile),'-c','copy',str(silent)],sum(float(row[2]) for row in segments))
            else:
                silent=None
            # Normalize the supplied intro to the chosen output size/frame rate/codec, then concatenate it ahead of the montage.
            stage('Preparing intro and visual sections'); self.q.put(('overall',82,'Preparing intro and visuals'));visuals=[]
            if useintro and intro_path and intro_dur>0:
                intro_norm=temp/'intro_normalized.mp4'
                ivf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1'
                intro_ext=Path(intro_path).suffix.lower()
                if intro_ext in {'.png','.jpg','.jpeg'}:
                    intro_cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',intro_path,'-t',f'{intro_dur:.3f}','-an','-vf',ivf,*self.video_encoder_args(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(intro_norm)]
                else:
                    intro_cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',intro_path,'-t',f'{intro_dur:.3f}','-an','-vf',ivf,*self.video_encoder_args(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(intro_norm)]
                self.run_render_process(intro_cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                visuals.append(intro_norm)
            if silent is not None: visuals.append(silent)
            if not visuals: raise RuntimeError('No video segments were generated.')
            concatvisual=temp/'visuals_concat.txt'
            with concatvisual.open('w',encoding='utf-8') as vf: 
                for v in visuals: vf.write("file '"+str(v).replace('\\','/').replace("'","'\\''")+"'\n")
            combined=temp/'combined_visuals.mp4'
            stage('Combining intro and montage'); self.q.put(('overall',88,'Combining visual sections'));self.run_render_process(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concatvisual),'-c','copy',str(combined)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            Path(output).parent.mkdir(parents=True,exist_ok=True)
            final_vf=[]
            final_duration=songdur
            # xfade overlaps shorten the montage. Fill any resulting gap with
            # moving footage, not tpad's cloned final frame (the freeze bug).
            combined_duration=self.probe_duration(str(combined))
            pad_duration=max(0.0,final_duration-combined_duration)
            if pad_duration>0.04:
                tail_source,tail_source_dur,_=rng.choice(usable)
                tail_lo,tail_hi=source_bounds(tail_source_dur)
                tail_available=max(0.0,tail_hi-tail_lo)
                tail_start=rng.uniform(tail_lo,max(tail_lo,tail_hi-min(pad_duration,tail_available)))
                tail=temp/'transition_tail.mp4'
                try:
                    tail_w,tail_h=self.probe_video_dimensions(tail_source)
                except Exception:
                    tail_w,tail_h=width,height
                if aspect_ratio!='16:9 Landscape':
                    tail_vf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1'
                elif abs((tail_w/tail_h)-(16/9))>0.02:
                    if vertical_mode=='Original (fit)':
                        tail_vf=f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps},setsar=1'
                    elif tail_h>tail_w:
                        fit_scale=min(width/tail_w,height/tail_h); zoom_scale=fit_scale*1.5
                        sw=max(1,int(tail_w*zoom_scale)); sh=max(1,int(tail_h*zoom_scale))
                        tail_vf=f'scale={sw}:{sh},crop={width}:{height},fps={fps},setsar=1'
                    else:
                        tail_vf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1'
                else:
                    tail_vf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},setsar=1'
                if retro: tail_vf+=',eq=saturation=0.58:contrast=0.84:brightness=0.035,colorbalance=rs=0.065:gs=0.025:bs=-0.045,gblur=sigma=0.30,noise=alls=14:allf=t,vignette=PI/5'
                tail_len=pad_duration
                if tail_available+0.001<tail_len:
                    self.q.put(('log',f'Transition-tail source {Path(tail_source).name} is shorter than {tail_len:.2f}s; looping source footage to avoid a frozen end frame.'))
                    tail_cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-stream_loop','-1','-ss',f'{tail_start:.3f}','-i',tail_source,'-t',f'{tail_len:.3f}','-an','-vf',tail_vf,*self.video_encoder_args(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(tail)]
                else:
                    tail_cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',f'{tail_start:.3f}','-i',tail_source,'-t',f'{tail_len:.3f}','-an','-vf',tail_vf,*self.video_encoder_args(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(tail)]
                self.run_render_process(tail_cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                combined_with_tail=temp/'combined_with_real_tail.mp4'
                tail_concat=temp/'tail_concat.txt'
                with tail_concat.open('w',encoding='utf-8') as tf:
                    for v in (combined,tail): tf.write("file '"+str(v).replace('\\','/').replace("'","'\\''")+"'\n")
                self.run_render_process(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(tail_concat),'-c','copy',str(combined_with_tail)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                combined=combined_with_tail
                self.q.put(('log',f'v{APP_VERSION} moving footage tail appended for {pad_duration:.2f}s to prevent final-frame freeze.'))
            if fadein: final_vf.append('fade=t=in:st=0:d=1.5')
            if fadeout: final_vf.append(f'fade=t=out:st={max(0.0,final_duration-1.5):.3f}:d=1.5')
            final_cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(combined)]
            if trimmed_music:
                trimmed_audio_path=temp/'trimmed_music.wav'; af_parts=[]
                for idx,(seg_start,seg_end,_,_) in enumerate(music_trim_segments):
                    audio_start=max(0.0,seg_start-2.0) if idx==0 else seg_start
                    audio_end=min(source_song_duration,seg_end+2.0) if idx==len(music_trim_segments)-1 else seg_end
                    af_parts.append(f'[{idx}:a]atrim=start={audio_start:.6f}:end={audio_end:.6f},asetpts=PTS-STARTPTS[a{idx}]')
                if len(music_trim_segments)==1:
                    first_start=max(0.0,music_trim_segments[0][0]-2.0); last_end=min(source_song_duration,music_trim_segments[-1][1]+2.0)
                    filtergraph=f'[0:a]atrim=start={first_start:.6f}:end={last_end:.6f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=2,afade=t=out:st={max(0.0,songdur-2.0):.3}:d=2[aout]'
                else:
                    for idx in range(1,len(music_trim_segments)):
                        label=f'xf{idx}'; af_parts.append(f'[xf{idx-1}][a{idx}]acrossfade=d=0.5:c1=tri:c2=tri[{label}]')
                    filtergraph=';'.join(af_parts)+f';[xf{len(music_trim_segments)-1}]afade=t=in:st=0:d={min(2.0,songdur):.3},afade=t=out:st={max(0.0,songdur-2.0):.3}:d={min(2.0,songdur):.3}[aout]'
                audio_inputs=['-i',song]*len(music_trim_segments)
                self.run_render_process(['ffmpeg','-hide_banner','-loglevel','error','-y',*audio_inputs,'-filter_complex',filtergraph,'-map','[aout]','-t',f'{songdur:.3f}','-c:a','pcm_s16le',str(trimmed_audio_path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                final_cmd += ['-i',str(trimmed_audio_path)]
            else: final_cmd += ['-i',song]
            final_cmd += ['-map','0:v:0','-map','1:a:0']
            if final_vf: final_cmd += ['-vf',','.join(final_vf)]
            final_cmd += [*self.video_encoder_args(crf),'-r',str(fps),'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',output]
            stage('Final encode and audio mux'); self.q.put(('overall',90,'Final encoding / muxing'));self.run_ffmpeg_final_progress(final_cmd,final_duration)
            self.q.put(('overall',100,'Final MP4 complete'));self.q.put(('log',f'Completed! Output: {output}'));success=True
        except subprocess.CalledProcessError as e:
            err=(e.stderr or b'').decode(errors='replace')[-2000:];self.q.put(('log','FFmpeg error: '+err))
        except Exception as e:
            if str(e)=='RENDER_CANCELLED': self.q.put(('log','Render cancelled by user. Temporary render files will be removed.'))
            else: self.q.put(('log','Error: '+str(e)))
        finally:
            stage_times.append((stage_name,time.time()-stage_clock))
            if stage_times: self.q.put(('stage_summary',stage_times))
            if self.render_cancel.is_set():
                try:
                    if Path(output).exists(): Path(output).unlink()
                except Exception: pass
            if temp is not None:
                if success: shutil.rmtree(temp,ignore_errors=True)
                else: self.q.put(('log',f'Recovery files retained in temporary work folder: {temp}'))
            self.q.put(('done',success))

if __name__=='__main__':
    root=tk.Tk()
    try:ttk.Style().theme_use('vista')
    except:pass
    AutoVideoApp(root);root.mainloop()
