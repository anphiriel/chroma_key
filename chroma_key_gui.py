"""
chroma_key_gui.py

Tkinter GUI for the Chroma Key Compositor demonstration

Author: Anelia Gaydardzhieva (https://github.com/anphiriel)
(c) 2025, MIT License 

GUI layer for demonstrating a Chroma Key Compositor using Tkinter
It references the chroma_key_core module for the underlying compositing and processing
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter.ttk as ttk

# Import the function from the other file
from chroma_key_core import perform_chroma_key

class ToolTip:
    """
    A simple tooltip that appears on widget hover
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None

        widget.bind("<Enter>", self._show_tooltip)
        widget.bind("<Leave>", self._hide_tooltip)

    def _show_tooltip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 40
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, borderwidth=1, relief="solid")
        # dark background + light text
        label.configure(background="#333333", foreground="#ffffff")
        label.pack(ipadx=5, ipady=2)

    def _hide_tooltip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class ChromaKeyApp:
    """
    A Tkinter-based demonstration for greenscreen (chroma key) replacement
    """

    def __init__(self):
        # main window
        self.root = tk.Tk()
        self.root.title("Chroma Key Compositor")
        self.root.geometry("1050x550")

        # default keying/color settings
        self.bg_color = (0, 255, 0)
        self.tolerance = 25
        self.softness = 0
        self.color_spill = 0

        # foreground adjustments
        self.fg_brightness = 0
        self.fg_contrast = 1.0

        # background adjustments
        self.bg_brightness = 0
        self.bg_contrast = 1.0

        # bounding box color pick
        self.selecting_region = False
        self.x0 = self.y0 = self.x1 = self.y1 = 0
        self.color_picked = False

        # foreground load
        self.fg_cap_path = None
        self.fg_cap = None

        # background image
        self.bg_image_path = None
        self.bg_image = None

        # background video
        self.bg_cap_path = None
        self.bg_cap = None # ?????????????????????????????????????????????
        # background image or video load - check
        self.bg_is_video = False        
        # reverse checkbox
        self.bg_video_is_reversed = tk.BooleanVar(value=False)

        # background video processing
        self.bg_total_frames = 0
        self.bg_index = 0
        self.bg_frames = []

        # build ui
        self._setup_ui()
        self.root.mainloop()

    # --------------------------------------------------
    # Setup UI
    # --------------------------------------------------
    def _setup_ui(self):
        """
        Builds the  user interface, organizing frames and controls
        """        
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # styles
        style.configure("TFrame", background="#404040")
        style.configure("TLabel", background="#404040", foreground="#ffffff")
        style.configure("TLabelframe", background="#404040", foreground="#cccccc", borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background="#404040", foreground="#cccccc")
        style.configure("TCheckbutton", background="#404040", foreground="#cccccc")
        style.map("TCheckbutton", background=[("active", "#666666"), ("pressed", "#666666")])
        style.configure("TButton", background="#777777", foreground="#ffffff", borderwidth=1, relief="solid")
        style.map("TButton", background=[("active", "#666666"), ("pressed", "#666666")])
        style.configure("TScale", background="#404040")
        style.configure("Horizontal.TScale", troughcolor="#333333")
        style.configure("TinyInfo.TLabel", font=("Helvetica", 11, "bold"), foreground="#999999", padding=1)

        # main grid layout
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill="both", expand=True)

        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="y")

        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True)

        top_frame = ttk.Labelframe(left_panel, text="Source Setup")
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        # top 3 buttons
        self.create_button_with_info(parent=top_frame, text="Load Foreground", command=self.load_fg_video, row=0, tooltip_text="Choose a main (foreground) video file to remove its background")
        self.create_button_with_info(parent=top_frame, text="Pick Chroma Key Color", command=self.pick_color_from_video, row=1, tooltip_text="Select the color in your foreground video to key out (e.g., greenscreen)")
        self.create_button_with_info(parent=top_frame, text="Load Background", command=self.load_background, row=2, tooltip_text="Choose an image or video to replace the keyed-out background")

        # reverse background checkbox
        self.reverse_bg_check = ttk.Checkbutton(top_frame, text="Reverse Background Playback", variable=self.bg_video_is_reversed, command=self.update_preview)
        self.reverse_bg_check.grid(row=3, column=0, pady=5, sticky="w", padx=(5,0))
        self.reverse_bg_check.config(state="disabled")
        reverse_info = ttk.Label(top_frame, text="?", style="TinyInfo.TLabel")
        reverse_info.grid(row=3, column=1, sticky="w", padx=5)
        ToolTip(reverse_info, "Play the selected background video in reverse instead of forward")

        # chroma key settings frame
        key_frame = ttk.Labelframe(left_panel, text="Chroma Key Settings")
        key_frame.pack(side="top", fill="x", padx=10, pady=10)
        # chroma key settings elements
        self.create_slider_with_info(key_frame, "Tolerance", self.tolerance, self.update_tolerance, 0, 100, "Adjust how wide the hue range is around the keyed color")
        self.create_slider_with_info( key_frame, "Edge Softness", self.softness, self.update_softness, 0, 25, "Blur the transition between the keyed area and foreground to reduce hard edges")
        self.create_slider_with_info( key_frame, "Color Spill Removal", self.color_spill, self.update_cast_removal, 0, 100, "Reduce any color spill (e.g., green tint) on the foreground subject")

        # foreground adjustments frame
        fg_frame = ttk.Labelframe(left_panel, text="Foreground Adjustments")
        fg_frame.pack(side="top", fill="x", padx=10, pady=10)
        # foreground adjustments elements
        self.create_slider_with_info(fg_frame, "Brightness", self.fg_brightness, self.update_fg_brightness, -50, 50, "Fine-tune how light or dark the foreground (main video) appears")
        self.create_slider_with_info(fg_frame, "Contrast", int(self.fg_contrast * 100), self.update_fg_contrast, 50, 150, "Increase or decrease contrast in the foreground to make details stand out")

        # background adjustments frame
        bg_frame = ttk.Labelframe(left_panel, text="Background Adjustments")
        bg_frame.pack(side="top", fill="x", padx=10, pady=10)
        # background adjustments elements
        self.create_slider_with_info(bg_frame, "Brightness", self.bg_brightness, self.update_bg_brightness, -50, 50, "Adjust how bright or dark the background (image/video) appears")
        self.create_slider_with_info(bg_frame, "Contrast", int(self.bg_contrast * 100), self.update_bg_contrast, 50, 150, "Enhance or reduce contrast in the background for improved visual balance")

        # right side: video preview
        video_frame = ttk.Frame(right_panel)
        video_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(125, 15))

        # video preview element
        self.video_label = ttk.Label(video_frame, text="Video Preview", anchor="center", background="#000000", foreground="#ffffff")
        self.video_label.pack(fill="both", expand=True)

        # action buttons frames
        bottom_frame = ttk.Frame(right_panel)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        actions_frame = ttk.Frame(bottom_frame)
        actions_frame.pack(side="right")
        actions_frame.columnconfigure(0, weight=0)
        actions_frame.columnconfigure(1, weight=0)
        actions_frame.columnconfigure(2, weight=0)
        actions_frame.columnconfigure(3, weight=0)

        # action buttons
        self.create_button_with_info(parent=actions_frame, text="Preview Composited Video", command=self.preview_composited_video, row=0, col=0, tooltip_text="Play the main video with the chosen background (preview might be at reduced FPS)")
        self.create_button_with_info(parent=actions_frame, text="Export Composited Video", command=self.export_composited_video, row=0, col=2, tooltip_text="Render and save the final video with the keyed-out background replaced")

    # ----------------------------------------------------------------------
    # Element builders - buttons and sliders
    # ----------------------------------------------------------------------
    def create_button_with_info(self, parent, text, command, row=0, col=0, tooltip_text=""):
        btn = ttk.Button(parent, text=text, command=command)
        btn.grid(row=row, column=col, pady=(5, 5), padx=(5,0), sticky="ew")

        info_lbl = ttk.Label(parent, text="?", style="TinyInfo.TLabel")
        info_lbl.grid(row=row, column=col+1, sticky="w", padx=5)
        ToolTip(info_lbl, tooltip_text)

    def create_slider_with_info(self, parent, label_text, default_value, command, min_val, max_val, tooltip_text):
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill="x", pady=5)

        row_frame.columnconfigure(0, minsize=85)
        row_frame.columnconfigure(1, weight=1)
        row_frame.columnconfigure(2, minsize=37)
        row_frame.columnconfigure(3, minsize=10)

        lbl = ttk.Label(row_frame, text=label_text)
        lbl.grid(row=0, column=0, padx=(5,5), sticky="w")

        value_lbl = ttk.Label(row_frame, text=str(default_value))
        value_lbl.grid(row=0, column=2, padx=(5,5), sticky="w")

        def slider_callback(val):
            val_str = f"{int(float(val))}"
            value_lbl.config(text=val_str)
            command(val)

        scale = ttk.Scale(row_frame, from_=min_val, to=max_val, orient="horizontal", command=slider_callback, length=180)
        scale.set(default_value)
        scale.grid(row=0, column=1, sticky="e", padx=(0,5))

        info_lbl = ttk.Label(row_frame, text="?", style="TinyInfo.TLabel")
        info_lbl.grid(row=0, column=3, sticky="w", padx=(0,5))
        ToolTip(info_lbl, tooltip_text)

    # -------------------------------------------------
    # Foreground video load and color select
    # -------------------------------------------------
    def load_fg_video(self):
        self.fg_cap_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
        if not self.fg_cap_path:
            messagebox.showerror("Error", "No video file selected.")
            return
        threading.Thread(target=self._load_fg_video_worker, args=(self.fg_cap_path,)).start()
        self.root.after(0, lambda: self._show_loading_popup("Loading Foreground Video...\nPlease wait."))

    def _load_fg_video_worker(self, path):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self.root.after(0, lambda: self._finish_loading(False, "Failed to open foreground video."))
            return
        self.fg_cap = cap
        self.root.after(0, lambda: self._finish_loading(True, "Foreground video loaded successfully."))
        self.root.after(0, self.update_preview)

    def pick_color_from_video(self):
        if not self.fg_cap or not self.fg_cap.isOpened():
            messagebox.showerror("Error", "Load a video first.")
            return
        self.fg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.color_picked = False
        self.selecting_region = False
        self.x0 = self.y0 = self.x1 = self.y1 = 0

        cv2.namedWindow("Pick Color from Video")
        cv2.setMouseCallback("Pick Color from Video", self._pick_color_callback)

        while True:
            ret, frame = self.fg_cap.read()
            if not ret:
                self.fg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            if self.selecting_region:
                cv2.rectangle(frame, (self.x0, self.y0), (self.x1, self.y1), (0, 255, 255), 2)

            cv2.imshow("Pick Color from Video", frame)
            key = cv2.waitKey(1) & 0xFF
            if self.color_picked:
                break
            if key == 27 or cv2.getWindowProperty("Pick Color from Video", cv2.WND_PROP_VISIBLE) < 1:
                break
        cv2.destroyWindow("Pick Color from Video")

    def _pick_color_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.selecting_region = True
            self.x0, self.y0 = x, y
            self.x1, self.y1 = x, y
        elif event == cv2.EVENT_MOUSEMOVE and self.selecting_region:
            self.x1, self.y1 = x, y
        elif event == cv2.EVENT_LBUTTONUP:
            self.selecting_region = False
            self.x1, self.y1 = x, y
            x0, x1 = sorted([self.x0, self.x1])
            y0, y1 = sorted([self.y0, self.y1])
            ret, frame = self.fg_cap.read()
            if ret and (x1 > x0) and (y1 > y0):
                roi = frame[y0:y1, x0:x1]
                b_mean = np.mean(roi[:, :, 0])
                g_mean = np.mean(roi[:, :, 1])
                r_mean = np.mean(roi[:, :, 2])
                self.bg_color = (int(r_mean), int(g_mean), int(b_mean))
                messagebox.showinfo("Selected Color", f"Avg Color in Box: R={int(r_mean)}, G={int(g_mean)}, B={int(b_mean)}")
            self.color_picked = True

    # -------------------------------------------------
    # Background video/image load
    # -------------------------------------------------
    def load_background(self):
        popup = tk.Toplevel(self.root)
        popup.title("Select Background Type")
        popup.geometry("300x150")
        popup.resizable(False, False)
        lbl = ttk.Label(popup, text="Choose Background Type:")
        lbl.pack(pady=20)
        img_btn = ttk.Button(popup, text="Image", command=lambda: self._set_background_choice(popup, "image"))
        img_btn.pack(pady=5)
        vid_btn = ttk.Button(popup, text="Video", command=lambda: self._set_background_choice(popup, "video"))
        vid_btn.pack(pady=5)
        cancel_btn = ttk.Button(popup, text="Cancel", command=popup.destroy)
        cancel_btn.pack(pady=5)

    def _set_background_choice(self, popup, choice):
        popup.destroy()
        if choice == "image":
            self.load_bg_image()
        else:
            self.load_background_video()

    def load_background_video(self):
        self.bg_cap_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4")])
        if not self.bg_cap_path:
            messagebox.showerror("Error", "No video file selected.")
            return
        threading.Thread(target=self._load_background_video_worker, args=(self.bg_cap_path,)).start()
        self.root.after(0, lambda: self._show_loading_popup("Loading Background Video...\nPlease wait."))

    def _load_background_video_worker(self, path):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self.root.after(0, lambda: self._finish_loading(False, "Failed to open background video."))
            self.reverse_bg_check.config(state="disabled")
            return
        temp_frames = []
        while True:
            ret, frm = cap.read()
            if not ret:
                break
            temp_frames.append(frm)
        cap.release()
        if len(temp_frames) < 1:
            self.root.after(0, lambda: self._finish_loading(False, "Background video has no valid frames."))
            self.reverse_bg_check.config(state="disabled")
            return

        self.bg_frames = temp_frames
        self.bg_total_frames = len(self.bg_frames)
        self.bg_index = 0
        self.bg_is_video = True
        self.reverse_bg_check.config(state="normal")
        self.root.after(0, lambda: self._finish_loading(True, "Background video loaded successfully."))
        self.root.after(0, self.update_preview)

    def load_bg_image(self):
        self.bg_image_path = filedialog.askopenfilename( filetypes=[("Image files", ("*.png", "*.jpg", "*.jpeg"))])
        if not self.bg_image_path:
            messagebox.showerror("Error", "No background image selected.")
            return
        img = cv2.imread(self.bg_image_path)
        if img is None:
            messagebox.showerror("Error", "Failed to load image.")
            self.reverse_bg_check.config(state="disabled")
        else:
            messagebox.showinfo("Info", "Background image loaded successfully.")
            self.bg_is_video = False
            self.bg_image = img
            self.reverse_bg_check.config(state="disabled")
            self.update_preview()

    # -------------------------------------------------
    # Slider callbacks
    # -------------------------------------------------
    def update_tolerance(self, val):
        self.tolerance = int(float(val))
        self.update_preview()

    def update_softness(self, val):
        self.softness = int(float(val))
        self.update_preview()

    def update_cast_removal(self, val):
        self.color_spill = int(float(val))
        self.update_preview()

    def update_fg_brightness(self, val):
        self.fg_brightness = int(float(val))
        self.update_preview()

    def update_fg_contrast(self, val):
        self.fg_contrast = float(val) / 100.0
        self.update_preview()

    def update_bg_brightness(self, val):
        self.bg_brightness = int(float(val))
        self.update_preview()

    def update_bg_contrast(self, val):
        self.bg_contrast = float(val) / 100.0
        self.update_preview()

    # -------------------------------------------------
    # Video preview
    # -------------------------------------------------
    def update_preview(self):
        """
        Plays the foreground video with the chosen background
        If Reverse is selected, background frames move backwards
        """
        if not self.fg_cap or not self.fg_cap.isOpened():
            return
        ret, frame = self.fg_cap.read()
        if not ret:
            self.fg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
        out_frame = self.apply_chroma_key(frame)
        self.display_frame(out_frame)

    def apply_chroma_key(self, frame):
        adjusted_foreground = cv2.convertScaleAbs(frame, alpha=self.fg_contrast, beta=self.fg_brightness)
        if self.bg_is_video and self.bg_frames:
            if self.bg_video_is_reversed.get():
                self.bg_index -= 1
                if self.bg_index < 0:
                    self.bg_index = self.bg_total_frames - 1
            else:
                self.bg_index += 1
                if self.bg_index >= self.bg_total_frames:
                    self.bg_index = 0

            raw_bg = self.bg_frames[self.bg_index]
            adjusted_bg = cv2.convertScaleAbs(raw_bg, alpha=self.bg_contrast, beta=self.bg_brightness)
            bg_source = adjusted_bg
            bg_is_video_flag = False
        elif self.bg_image is not None:
            adjusted_bg = cv2.convertScaleAbs(self.bg_image, alpha=self.bg_contrast, beta=self.bg_brightness)
            bg_source = adjusted_bg
            bg_is_video_flag = False
        else:
            return adjusted_foreground

        # chroma_key_core call
        return perform_chroma_key(
            adjusted_foreground,
            bg_source,
            bg_is_video_flag,
            (self.bg_color[2], self.bg_color[1], self.bg_color[0]),
            self.tolerance,
            self.softness,
            self.color_spill
        )

    def display_frame(self, frame):
        w = self.video_label.winfo_width()
        h = self.video_label.winfo_height()
        if w < 2 or h < 2:
            return

        fh, fw = frame.shape[:2]
        scale = min(w / fw, h / fh)
        nw = int(fw * scale)
        nh = int(fh * scale)

        resized = cv2.resize(frame, (nw, nh))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.video_label.config(image=img, text="")
        self.video_label.image = img

    # -------------------------------------------------
    # Action buttons
    # -------------------------------------------------
    def preview_composited_video(self):
        """
        Updates the displayed frame in real time after adjustments or new background
        """
        if not self.fg_cap or not self.fg_cap.isOpened() or (self.bg_image is None and not self.bg_frames):
            messagebox.showerror("Error", "Load a video and background image/video first.")
            return

        fps = self.fg_cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        delay = int(1000 / fps)

        self.fg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if not self.bg_video_is_reversed.get():
            self.bg_index = 0
        else:
            self.bg_index = self.bg_total_frames - 1
        while True:
            ret, frame = self.fg_cap.read()
            if not ret:
                print("End of video.")
                break
            outf = self.apply_chroma_key(frame)
            cv2.imshow("Composited Video", outf)
            k = cv2.waitKey(delay) & 0xFF
            if k == 27:
                break
        cv2.destroyAllWindows()

    def export_composited_video(self):
        if not self.fg_cap or not self.fg_cap.isOpened() or (self.bg_image is None and not self.bg_frames):
            messagebox.showerror("Error", "Load a video and background image/video first.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4"), ("AVI Video", "*.avi")], title="Save Composited Video As...")
        if not out_path:
            return
        self.saving_thread = threading.Thread(target=self._save_video_worker, args=(out_path,))
        self.saving_thread.start()

    def _save_video_worker(self, out_path):
        self.root.after(0, self._show_saving_popup)
        cap = self.fg_cap
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.bg_index = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out_frame = self.apply_chroma_key(frame)
            writer.write(out_frame)
            frame_count += 1
        writer.release()
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.root.after(0, lambda: self._finish_saving(out_path, frame_count, total_frames))

    # ---------------------------------------------------------
    # Popups
    # ---------------------------------------------------------
    def _show_loading_popup(self, message="Loading... Please wait."):
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("Loading...")
        lbl = ttk.Label(self.loading_window, text=message)
        lbl.pack(padx=20, pady=20)

    def _finish_loading(self, success=True, msg=None):
        if hasattr(self, 'loading_window') and self.loading_window:
            self.loading_window.destroy()
        if msg:
            if success:
                messagebox.showinfo("Info", msg)
            else:
                messagebox.showerror("Error", msg)

    def _show_saving_popup(self):
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Saving Video...")
        lbl = ttk.Label(self.progress_window, text="Saving video in background. Please wait...")
        lbl.pack(padx=20, pady=20)

    def _finish_saving(self, out_path, frame_count, total_frames):
        if hasattr(self, 'progress_window'):
            self.progress_window.destroy()
        messagebox.showinfo("Success", f"Video saved to {out_path}.\nFrames: {frame_count}/{total_frames}")

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    ChromaKeyApp()
