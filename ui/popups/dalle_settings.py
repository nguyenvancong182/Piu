"""
DalleSettingsWindow class for Piu application.
Manages DALL-E image generation settings.
"""
import customtkinter as ctk
import logging
import os
from tkinter import filedialog, messagebox
import threading
import time

from utils.helpers import get_default_downloads_folder, safe_int
from ui.widgets.menu_utils import textbox_right_click_menu

class DalleSettingsWindow(ctk.CTkToplevel):

    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app

        self.title("🎨 Cài đặt Tạo Ảnh DALL-E")
        self.geometry("620x520") # Kích thước mong muốn
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()

        try:
            master_app.update_idletasks()
            self.update_idletasks()
            popup_actual_width = 620
            popup_actual_height = 520

            x = master_app.winfo_x() + (master_app.winfo_width() // 2) - (popup_actual_width // 2)
            y = master_app.winfo_y() + (master_app.winfo_height() // 2) - (popup_actual_height // 2)
            
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            if x + popup_actual_width > screen_width: position_x = screen_width - popup_actual_width
            else: position_x = x
            if y + popup_actual_height > screen_height: position_y = screen_height - popup_actual_height
            else: position_y = y
            if position_x < 0: position_x = 0
            if position_y < 0: position_y = 0
                
            self.geometry(f"{popup_actual_width}x{popup_actual_height}+{position_x}+{position_y}")
        except Exception as e:
            logging.warning(f"Không thể căn giữa cửa sổ DALL-E: {e}")

        # --- KHAI BÁO StringVars VÀ ĐỌC TỪ self.master_app.cfg ---
        self.dalle_model_var = ctk.StringVar(value=self.master_app.cfg.get("dalle_model_setting", "dall-e-3"))
        self.num_images_var = ctk.StringVar(value=str(self.master_app.cfg.get("dalle_num_images_setting", 1)))
        self.dalle_cost_saver_mode_var = ctk.BooleanVar(value=self.master_app.cfg.get("dalle_cost_saver_mode", False))
        self.image_size_var = ctk.StringVar(value=self.master_app.cfg.get(f"dalle_imagesize_{self.dalle_model_var.get()}_setting", ""))

        dalle_output_folder_candidate = self.master_app.cfg.get("dalle_output_folder_setting") # Ưu tiên config đã lưu
        if not dalle_output_folder_candidate or not os.path.isdir(dalle_output_folder_candidate):
            # Nếu không có trong config hoặc không hợp lệ, thử lấy từ output_path của tab Subtitle
            dalle_output_folder_candidate = self.master_app.output_path_var.get()
            if not dalle_output_folder_candidate or not os.path.isdir(dalle_output_folder_candidate):
                dalle_output_folder_candidate = get_default_downloads_folder() # Cuối cùng là thư mục Downloads mặc định

        self.output_folder_var = ctk.StringVar(value=dalle_output_folder_candidate)

        self.last_generation_params = None
        self.dalle3_quality_var = ctk.StringVar(value=self.master_app.cfg.get("dalle_quality_d3_setting", "standard"))
        self.dalle3_style_var = ctk.StringVar(value=self.master_app.cfg.get("dalle_style_d3_setting", "vivid"))

        # --- BẮT ĐẦU TẠO CÁC WIDGET UI ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=15, pady=15)

        # --- KHUNG CHỨA CÁC TÙY CHỌN Ở TRÊN CÙNG (Dùng grid bên trong frame này) ---
        top_options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_options_frame.pack(fill="x", pady=(0, 10), anchor="n") # Pack frame này vào main_frame

        # Cấu hình cột cho top_options_frame
        top_options_frame.grid_columnconfigure(0, weight=0, minsize=100)  # Label Model
        top_options_frame.grid_columnconfigure(1, weight=1)               # OptionMenu Model
        top_options_frame.grid_columnconfigure(2, weight=0, minsize=90)  # Label Số lượng
        top_options_frame.grid_columnconfigure(3, weight=0, minsize=60)   # Entry Số lượng
        top_options_frame.grid_columnconfigure(4, weight=0, minsize=100) # Label Kích thước
        top_options_frame.grid_columnconfigure(5, weight=1)               # OptionMenu Kích thước

        # Hàng 0: Model, Số lượng, Kích thước
        model_label = ctk.CTkLabel(top_options_frame, text="Model DALL-E:")
        model_label.grid(row=0, column=0, padx=(0, 2), pady=5, sticky="w")
        dalle_models = ["dall-e-3", "dall-e-2"]
        self.dalle_model_optionmenu = ctk.CTkOptionMenu(
            top_options_frame, variable=self.dalle_model_var,
            values=dalle_models, command=self._on_dalle_model_changed
        )
        self.dalle_model_optionmenu.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        num_images_label = ctk.CTkLabel(top_options_frame, text="Số lượng ảnh:")
        num_images_label.grid(row=0, column=2, padx=(5, 2), pady=5, sticky="w")
        self.num_images_entry = ctk.CTkEntry(top_options_frame, textvariable=self.num_images_var, width=50) # Giảm width một chút
        self.num_images_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky="w") # sticky "w"

        image_size_label = ctk.CTkLabel(top_options_frame, text="Kích thước ảnh:")
        image_size_label.grid(row=0, column=4, padx=(5, 2), pady=5, sticky="w")
        self.image_size_optionmenu = ctk.CTkOptionMenu(top_options_frame, variable=self.image_size_var, values=[""])
        self.image_size_optionmenu.grid(row=0, column=5, padx=(0, 0), pady=5, sticky="ew")

        # Hàng 1: Quality và Style cho DALL-E 3 (trong một frame con riêng, vẫn dùng grid)
        self.dalle3_options_frame = ctk.CTkFrame(top_options_frame, fg_color="transparent")
        self.dalle3_options_frame.grid(row=1, column=0, columnspan=6, padx=0, pady=(0,5), sticky="ew") # Kéo dài 6 cột
        # Cấu hình cột cho dalle3_options_frame
        self.dalle3_options_frame.grid_columnconfigure(0, weight=0, minsize=150) # Label Quality
        self.dalle3_options_frame.grid_columnconfigure(1, weight=1)              # Menu Quality
        self.dalle3_options_frame.grid_columnconfigure(2, weight=0, minsize=140) # Label Style
        self.dalle3_options_frame.grid_columnconfigure(3, weight=1)              # Menu Style
        
        quality_label = ctk.CTkLabel(self.dalle3_options_frame, text="Chất lượng (DALL-E 3):")
        quality_label.grid(row=0, column=0, padx=(0, 2), pady=5, sticky="w")
        quality_menu = ctk.CTkOptionMenu(
            self.dalle3_options_frame, variable=self.dalle3_quality_var, values=["standard", "hd"]
        )
        quality_menu.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        style_label = ctk.CTkLabel(self.dalle3_options_frame, text="Phong cách (DALL-E 3):")
        style_label.grid(row=0, column=2, padx=(5, 2), pady=5, sticky="w")
        style_menu = ctk.CTkOptionMenu(
            self.dalle3_options_frame, variable=self.dalle3_style_var, values=["natural", "vivid"]
        )
        style_menu.grid(row=0, column=3, padx=(0, 0), pady=5, sticky="ew")

        # Hàng 2: Checkbox "Tiết kiệm chi phí" (trong một frame con riêng, vẫn dùng grid)
        cost_saver_frame = ctk.CTkFrame(top_options_frame, fg_color="transparent")
        cost_saver_frame.grid(row=2, column=0, columnspan=6, padx=0, pady=(5, 5), sticky="w") # Kéo dài 6 cột, căn trái

        self.cost_saver_checkbox = ctk.CTkCheckBox(
            cost_saver_frame,
            text="Tiết kiệm chi phí (Tạo 1 prompt DALL-E chung từ tóm tắt kịch bản)",
            variable=self.dalle_cost_saver_mode_var
        )
        self.cost_saver_checkbox.pack(side="left", anchor="w") # Dùng pack trong frame con này


        # --- Ô nhập Prompt ---
        prompt_label = ctk.CTkLabel(self.main_frame, text="Mô tả ảnh (Prompt cho DALL-E):")
        prompt_label.pack(anchor="w", padx=5, pady=(10, 2)) # pady trên để tạo khoảng cách với top_options_frame
        self.prompt_textbox = ctk.CTkTextbox(self.main_frame, height=160, wrap="word" , border_width=1, border_color="gray50") # Giảm height
        self.prompt_textbox.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.prompt_textbox.insert("1.0", "Một kim tự tháp Ai Cập cổ đại hùng vĩ dưới ánh hoàng hôn, phong cách điện ảnh.")

        self.prompt_textbox.bind("<Button-3>", textbox_right_click_menu)

        # --- Chọn Thư mục lưu ảnh ---
        folder_label = ctk.CTkLabel(self.main_frame, text="Lưu ảnh vào thư mục:")
        folder_label.pack(anchor="w", padx=5, pady=(5, 2))
        folder_path_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        folder_path_frame.pack(fill="x", pady=(0, 10))
        
        self.selected_folder_label = ctk.CTkLabel(folder_path_frame, textvariable=self.output_folder_var, wraplength=280, anchor="w", text_color="gray") # Giảm wraplength
        self.selected_folder_label.pack(side="left", padx=(5, 5), expand=True, fill="x")
        
        select_folder_button = ctk.CTkButton(folder_path_frame, text="Chọn thư mục...", width=110, command=self._select_output_folder) # Giảm width
        select_folder_button.pack(side="left", padx=(0, 3))
        
        open_folder_button = ctk.CTkButton(folder_path_frame, text="📂 Mở", width=70, command=self._open_output_folder) # Rút gọn text và width
        open_folder_button.pack(side="left", padx=(0, 5))


        # --- CÁC NÚT CHÍNH (ĐẢM BẢO ĐƯỢC PACK CUỐI CÙNG) ---
        buttons_main_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        buttons_main_frame.pack(side="bottom", fill="x", pady=(10, 0)) # pady trên để tách biệt

        # Các nút này pack vào buttons_main_frame từ phải sang trái
        self.cancel_button = ctk.CTkButton(buttons_main_frame, text="Hủy", width=100, command=self._on_close_dalle_window)
        self.cancel_button.pack(side="right", padx=(5, 0), pady=5) # padx=(left, right)

        self.generate_button = ctk.CTkButton(buttons_main_frame, text="🎨 Tạo Ảnh", width=130, command=self._initiate_dalle_generation, fg_color="#1f6aa5")
        self.generate_button.pack(side="right", padx=5, pady=5)

        self.redraw_button = ctk.CTkButton(
            buttons_main_frame, text="✏️ Vẽ lại", width=100,
            command=self._initiate_redraw, state="disabled"
        )
        self.redraw_button.pack(side="right", padx=(0, 5), pady=5)
        
        # --- Cập nhật ban đầu ---
        self.protocol("WM_DELETE_WINDOW", self._on_close_dalle_window)
        self.after(10, lambda: self._on_dalle_model_changed(self.dalle_model_var.get())) # Gọi để cập nhật size list và hiển thị DALL-E 3 options
        self._update_google_label() # Gọi để cập nhật label đường dẫn google key ban đầu
        #self.after(10, self._update_dependent_controls_state)
        

    # Thêm hàm _update_google_label nếu nó chưa có hoặc để đảm bảo nó được gọi đúng
    def _update_google_label(self, *args): # Thêm *args để có thể dùng với trace
        """ Cập nhật label hiển thị đường dẫn file Google Key """
        # Cần đảm bảo self.google_path_label đã được tạo nếu hàm này được gọi từ __init__ của cửa sổ khác
        if hasattr(self, 'google_key_path_var') and hasattr(self, 'google_path_label') and self.google_path_label.winfo_exists():
            path = self.google_key_path_var.get()
            self.google_path_label.configure(text=path if path else "(Chưa chọn file)")
        pass # Bỏ qua nếu không phải trong APISettingsWindow


# Hàm này sẽ được gọi khi người dùng nhấn nút "🎨 Tạo Ảnh"
    def _save_dalle_settings_to_config(self):
        """Lưu các cài đặt DALL-E hiện tại từ UI vào self.master_app.cfg."""
        if not hasattr(self.master_app, 'cfg'):
            logging.error("[DALL-E Settings] master_app.cfg không tồn tại. Không thể lưu cài đặt DALL-E.")
            return False

        try:
            current_model = self.dalle_model_var.get()
            self.master_app.cfg["dalle_model_setting"] = current_model
            try:
                num_img_user_requested = int(self.num_images_var.get())
                app_max_total_images = 10 # Bạn có thể thay đổi giới hạn này
                self.master_app.cfg["dalle_num_images_setting"] = max(1, min(num_img_user_requested, app_max_total_images))
                logging.info(f"[DALL-E Settings] Số lượng ảnh được cấu hình (sau khi giới hạn bởi app): {self.master_app.cfg['dalle_num_images_setting']}")
            except ValueError:
                # Nếu giá trị không hợp lệ, giữ lại giá trị cũ trong cfg hoặc đặt mặc định là 1
                default_num_images = 1
                self.master_app.cfg["dalle_num_images_setting"] = self.master_app.cfg.get("dalle_num_images_setting", default_num_images)
                logging.warning(f"[DALL-E Settings] Số lượng ảnh nhập vào không hợp lệ. Sử dụng giá trị: {self.master_app.cfg['dalle_num_images_setting']}")

            # Lưu kích thước dựa trên model hiện tại
            current_size = self.image_size_var.get()
            if current_size: # Chỉ lưu nếu có giá trị
                 self.master_app.cfg[f"dalle_imagesize_{current_model}_setting"] = current_size


            if current_model == "dall-e-3":
                self.master_app.cfg["dalle_quality_d3_setting"] = self.dalle3_quality_var.get()
                self.master_app.cfg["dalle_style_d3_setting"] = self.dalle3_style_var.get()

            output_folder = self.output_folder_var.get()
            if output_folder and os.path.isdir(output_folder): # Chỉ lưu nếu là thư mục hợp lệ
                self.master_app.cfg["dalle_output_folder_setting"] = output_folder
            else:
                logging.warning(f"[DALL-E Settings] Đường dẫn thư mục output DALL-E không hợp lệ '{output_folder}', không lưu.")

            if hasattr(self, 'dalle_cost_saver_mode_var'): # Kiểm tra xem biến đã tồn tại chưa
                self.master_app.cfg["dalle_cost_saver_mode"] = self.dalle_cost_saver_mode_var.get()
            else:
                # Nếu biến chưa có, có thể bạn muốn đặt giá trị mặc định vào config
                self.master_app.cfg["dalle_cost_saver_mode"] = False 
                logging.warning("[DALL-E Settings] dalle_cost_saver_mode_var không tồn tại khi lưu, đặt mặc định là False.")

            # Gọi hàm lưu config tổng của ứng dụng chính
            if hasattr(self.master_app, 'save_current_config') and callable(self.master_app.save_current_config):
                self.master_app.save_current_config()
                logging.info("[DALL-E Settings] Đã lưu các cài đặt DALL-E vào config chung.")
                return True
            else:
                logging.error("[DALL-E Settings] Không tìm thấy hàm save_current_config trên master_app.")
                return False
        except Exception as e:
            logging.error(f"[DALL-E Settings] Lỗi khi lưu cài đặt DALL-E: {e}", exc_info=True)
            return False


# Hàm này gọi hàm _save_dalle_settings_to_config để lưu cài đặt
    def _on_close_dalle_window(self):
        """Được gọi khi người dùng đóng cửa sổ DALL-E (ví dụ, bằng nút X).
        Lưu cài đặt trước khi đóng.
        """
        logging.info("[DALL-E Popup] Cửa sổ DALL-E đang đóng, thực hiện lưu cài đặt...")
        self._save_dalle_settings_to_config() # Gọi hàm lưu bạn đã tạo
        self.destroy() # Sau đó đóng cửa sổ
    

    def _on_dalle_model_changed(self, selected_model):
        logging.info(f"[DALL-E Popup] Model DALL-E thay đổi thành: {selected_model}")
        supported_sizes = []
        default_size = ""
        if selected_model == "dall-e-3":
            supported_sizes = ["1024x1024", "1792x1024", "1024x1792"]
            default_size = "1792x1024"
        elif selected_model == "dall-e-2":
            supported_sizes = ["256x256", "512x512", "1024x1024"]
            default_size = "1024x1024"
        else:
            supported_sizes = ["1792x1024"] # Mặc định an toàn
            default_size = "1792x1024"

        if hasattr(self, 'image_size_optionmenu'):
            self.image_size_optionmenu.configure(values=supported_sizes)
            current_size_var_value = self.image_size_var.get()
            if current_size_var_value in supported_sizes:
                self.image_size_var.set(current_size_var_value)
            elif supported_sizes:
                self.image_size_var.set(default_size if default_size in supported_sizes else supported_sizes[0])
            else:
                self.image_size_var.set("")
        else:
            logging.warning("Không tìm thấy image_size_optionmenu để cập nhật kích thước.")

        # --- PHẦN GRID ---
        if hasattr(self, 'dalle3_options_frame'): # Kiểm tra xem frame đã tồn tại chưa
            if selected_model == "dall-e-3":
                # Hiển thị frame bằng grid, đặt nó vào hàng 1, kéo dài 6 cột
                self.dalle3_options_frame.grid(row=1, column=0, columnspan=6, padx=5, pady=(0,5), sticky="ew")
                logging.debug("Đã grid dalle3_options_frame (hiển thị).")
            else: # Nếu không phải dall-e-3
                # Ẩn frame bằng grid_remove
                self.dalle3_options_frame.grid_remove()
                logging.debug("Đã grid_remove dalle3_options_frame (ẩn).")

    def _select_output_folder(self):
        folder_selected = filedialog.askdirectory(initialdir=self.output_folder_var.get(), parent=self)
        if folder_selected:
            self.output_folder_var.set(folder_selected)
            logging.info(f"[DALL-E Popup] Đã chọn thư mục lưu ảnh: {folder_selected}")


# Hảm nút mở ảnh
    def _open_output_folder(self):
        folder_path = self.output_folder_var.get()
        if folder_path and os.path.isdir(folder_path):
            logging.info(f"[DALL-E Popup] Yêu cầu mở thư mục output: {folder_path}")
            try:
                # Sử dụng hàm open_file_with_default_app từ master_app (SubtitleApp)
                if hasattr(self.master_app, 'open_file_with_default_app') and \
                   callable(self.master_app.open_file_with_default_app):
                    self.master_app.open_file_with_default_app(folder_path)
                else:
                    logging.warning("[DALL-E Popup] Không tìm thấy open_file_with_default_app trên master_app. Thử os.startfile (Windows).")
                    if platform.system() == "Windows":
                        os.startfile(folder_path)
                    elif platform.system() == "Darwin": # macOS
                        subprocess.Popen(["open", folder_path])
                    else: # Linux
                        subprocess.Popen(["xdg-open", folder_path])
            except Exception as e:
                logging.error(f"[DALL-E Popup] Lỗi khi mở thư mục '{folder_path}': {e}")
                messagebox.showerror("Lỗi Mở Thư Mục", f"Không thể mở thư mục:\n{folder_path}\n\nLỗi: {e}", parent=self)
        elif folder_path:
            messagebox.showwarning("Đường dẫn không hợp lệ",
                                   f"Đường dẫn thư mục đã chọn không hợp lệ hoặc không tồn tại:\n{folder_path}",
                                   parent=self)
        else:
            messagebox.showwarning("Chưa chọn thư mục",
                                   "Vui lòng chọn một thư mục hợp lệ trước.",
                                   parent=self)


    def _initiate_dalle_generation(self, is_redraw=False):
        prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
        selected_dalle_model = self.dalle_model_var.get() # Lấy model đã chọn
        try:
            num_images_str = self.num_images_var.get()
            if not num_images_str.isdigit(): # Kiểm tra có phải là số không
                messagebox.showerror("Số lượng không hợp lệ", "Số lượng ảnh phải là một số nguyên dương.", parent=self)
                return
            num_images = int(num_images_str)

            app_max_total_images = 16 
            if not (1 <= num_images <= app_max_total_images):
                messagebox.showerror("Số lượng không hợp lệ", f"Số lượng ảnh cho phép từ 1 đến {app_max_total_images}.", parent=self)
                return
        except ValueError:
            messagebox.showerror("Số lượng không hợp lệ", "Vui lòng nhập một số nguyên dương cho số lượng ảnh.", parent=self)
            return

        size = self.image_size_var.get()
        output_folder = self.output_folder_var.get()

        if not prompt:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập mô tả ảnh (Prompt).", parent=self)
            return
        if not output_folder or not os.path.isdir(output_folder):
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn một thư mục hợp lệ để lưu ảnh.", parent=self)
            return
        if not size: 
            messagebox.showwarning("Thiếu kích thước", "Vui lòng chọn kích thước ảnh.", parent=self)
            return
        #self._save_dalle_settings_to_config() # Cân nhắc việc có nên lưu tự động ở đây không

        self.last_generation_params = {
            "prompt": prompt, "num_images": num_images, "size": size,
            "output_folder": output_folder, "dalle_model": selected_dalle_model
        }

        button_text_while_processing = "🎨 Đang vẽ lại..." if is_redraw else "🎨 Đang tạo..."
        
        if hasattr(self, 'generate_button') and self.generate_button.winfo_exists():
            self.generate_button.configure(state="disabled", text=button_text_while_processing)
        
        if hasattr(self, 'redraw_button') and self.redraw_button.winfo_exists():
            self.redraw_button.configure(state="disabled")
            
        if hasattr(self, 'cancel_button') and self.cancel_button.winfo_exists(): # Nút "Hủy" của popup DALL-E
            self.cancel_button.configure(state="disabled")
            
        self.update_idletasks() 

        logging.info(f"[DALL-E Popup] Yêu cầu {'Vẽ lại' if is_redraw else 'Tạo ảnh'}: Model='{selected_dalle_model}', Prompt='{prompt[:30]}...', Số lượng={num_images}, Kích thước='{size}', Thư mục='{output_folder}'")

        thread = threading.Thread(
            target=self._perform_dalle_generation_thread,
            args=(self.master_app, prompt, num_images, size, output_folder, selected_dalle_model),
            daemon=True, name="DalleGenerationThread"
        )
        thread.start()

        logging.info("[DALL-E Popup] Đã bắt đầu luồng tạo ảnh. Đang tự động đóng cửa sổ DALL-E...")
        self._on_close_dalle_window()


    def _initiate_redraw(self):
        if self.last_generation_params:
            logging.info(f"[DALL-E Popup] Yêu cầu Vẽ lại với params đã lưu: {self.last_generation_params}")
            self.prompt_textbox.delete("1.0", "end")
            self.prompt_textbox.insert("1.0", self.last_generation_params["prompt"])
            self.num_images_var.set(str(self.last_generation_params["num_images"]))
            self.dalle_model_var.set(self.last_generation_params["dalle_model"])
            # Gọi _on_dalle_model_changed để cập nhật size list và sau đó set size
            self._on_dalle_model_changed(self.last_generation_params["dalle_model"])
            self.image_size_var.set(self.last_generation_params["size"])
            self.output_folder_var.set(self.last_generation_params["output_folder"])
            self._initiate_dalle_generation(is_redraw=True)
        else:
            messagebox.showinfo("Thông báo", "Chưa có thông tin để 'Vẽ lại'.\nVui lòng tạo ảnh ít nhất một lần.", parent=self)


    def _perform_dalle_generation_thread(self, master_app_ref, prompt, num_images_requested, size, output_folder, selected_dalle_model):

        active_main_dalle_button = None
        if hasattr(master_app_ref, 'current_view'):
            current_view_on_master = master_app_ref.current_view
            if current_view_on_master == "≡ Tạo Phụ Đề":
                active_main_dalle_button = getattr(master_app_ref, 'dalle_button_sub_tab', None)
            elif current_view_on_master == "♪ Thuyết Minh":
                active_main_dalle_button = getattr(master_app_ref, 'dalle_button_dub_tab', None)

            # Log để kiểm tra
            logging.debug(f"[DALL-E Thread Start] Current master view: '{current_view_on_master}'. Active button target: {'Found' if active_main_dalle_button else 'Not Found'}")

        # Cập nhật nút trên cửa sổ chính (nếu tìm thấy)
        if active_main_dalle_button and active_main_dalle_button.winfo_exists():
            master_app_ref.after(0, lambda btn=active_main_dalle_button: btn.configure(text="🎨 Đang vẽ...", state=ctk.DISABLED))
            logging.info(f"[DALL-E Thread Start] Đã đặt nút DALL-E trên app chính ({active_main_dalle_button.winfo_name()}) sang trạng thái xử lý.")
        else:
            # Dự phòng: Nếu không xác định được nút cụ thể theo view, thử cập nhật cả hai (nếu chúng tồn tại)
            # Điều này đảm bảo có phản hồi ngay cả khi logic current_view có vấn đề
            logging.warning(f"[DALL-E Thread Start] Không tìm thấy nút DALL-E cụ thể theo view '{getattr(master_app_ref, 'current_view', 'N/A')}'. Thử cập nhật cả hai nút chính.")
            if hasattr(master_app_ref, 'dalle_button_sub_tab') and master_app_ref.dalle_button_sub_tab.winfo_exists():
                master_app_ref.after(0, lambda: master_app_ref.dalle_button_sub_tab.configure(text="🎨 Đang vẽ...", state=ctk.DISABLED))
            if hasattr(master_app_ref, 'dalle_button_dub_tab') and master_app_ref.dalle_button_dub_tab.winfo_exists():
                master_app_ref.after(0, lambda: master_app_ref.dalle_button_dub_tab.configure(text="🎨 Đang vẽ...", state=ctk.DISABLED))

        if hasattr(master_app_ref, 'is_dalle_processing'):
            master_app_ref.is_dalle_processing = True
        if hasattr(master_app_ref, 'start_time'):
            master_app_ref.start_time = time.time() # Đặt start_time của app chính

        # Gọi hàm cập nhật UI của app chính để bật nút Dừng
        if hasattr(master_app_ref, '_set_subtitle_tab_ui_state'):
            master_app_ref.after(0, lambda: master_app_ref._set_subtitle_tab_ui_state(subbing_active=False))
            
        if hasattr(master_app_ref, 'update_time_realtime') and callable(master_app_ref.update_time_realtime):
            master_app_ref.after(0, master_app_ref.update_time_realtime) # Kích hoạt vòng lặp timer của app chính

        # Hàm _update_ui_from_thread (sửa lại một chút để đơn giản hóa việc truyền parent)
        def _update_ui_from_thread(callback_func, *args_for_callback):
            parent_win_for_msgbox = self if self and self.winfo_exists() else master_app_ref
            def _task():
                try: # Thêm try-except ở đây để bắt lỗi nếu parent_win_for_msgbox không hợp lệ
                    if hasattr(messagebox, callback_func.__name__):
                        callback_func(*args_for_callback, parent=parent_win_for_msgbox)
                    else:
                        callback_func(*args_for_callback)
                except Exception as e_ui_task:
                    logging.error(f"Lỗi khi thực thi callback UI trong _task của DALL-E: {e_ui_task}")

            if master_app_ref and hasattr(master_app_ref, 'after'):
                master_app_ref.after(0, _task)
            elif self and hasattr(self, 'after'): # Fallback
                 self.after(0, _task)

        try:
            api_key = master_app_ref.openai_key_var.get()
            if not api_key:
                logging.error("[DALL-E Thread] Thiếu OpenAI API Key.")
                _update_ui_from_thread(messagebox.showerror, "Lỗi API Key", "OpenAI API Key chưa được cấu hình trong ứng dụng.")
                _update_ui_from_thread(self._reset_buttons_after_generation, False, "Lỗi: Thiếu API Key")
                return

            from openai import OpenAI # Import an toàn hơn ở đây
            client = OpenAI(api_key=api_key, timeout=180.0)

            if hasattr(master_app_ref, 'update_status'):
                # Cập nhật trạng thái ban đầu trước khi vào vòng lặp
                master_app_ref.after(0, lambda: master_app_ref.update_status(f"🎨 PIU: Chuẩn bị tạo {num_images_requested} ảnh..."))

            generated_image_urls = []
            image_data_list = []
            actual_api_calls_needed = 1
            images_per_api_call = 1

            if selected_dalle_model == "dall-e-2":
                images_per_api_call = min(num_images_requested, 10) # DALL-E 2 có thể tạo tối đa 10 ảnh/lần
                actual_api_calls_needed = (num_images_requested + images_per_api_call - 1) // images_per_api_call # Tính số lần gọi API cần thiết
            elif selected_dalle_model == "dall-e-3":
                images_per_api_call = 1 # DALL-E 3 chỉ tạo 1 ảnh/lần
                actual_api_calls_needed = num_images_requested # Số lần gọi API bằng số ảnh yêu cầu

            total_images_generated_so_far = 0 # Biến đếm tổng số ảnh đã được API trả về

            for call_idx in range(actual_api_calls_needed):
                if master_app_ref.stop_event.is_set(): 
                    logging.info("[DALL-E Thread] Yêu cầu dừng từ ứng dụng.")
                    _update_ui_from_thread(self._reset_buttons_after_generation, False, "Đã hủy bởi người dùng.")
                    return

                images_this_call = images_per_api_call
                if selected_dalle_model == "dall-e-2" and call_idx == actual_api_calls_needed - 1: # Lần gọi cuối cho DALL-E 2
                    remaining_images = num_images_requested - total_images_generated_so_far
                    if remaining_images > 0:
                        images_this_call = remaining_images

                start_image_num_this_call = total_images_generated_so_far + 1
                end_image_num_this_call = total_images_generated_so_far + images_this_call

                status_msg_api_call = f"🎨 DALL-E: Gọi API tạo ảnh {start_image_num_this_call}-{end_image_num_this_call}/{num_images_requested}..."
                if images_this_call == 1 and num_images_requested > 1 : # DALL-E 3 tạo từng ảnh
                    status_msg_api_call = f"🎨 DALL-E: Gọi API tạo ảnh {start_image_num_this_call}/{num_images_requested}..."
                elif images_this_call == 1 and num_images_requested == 1:
                    status_msg_api_call = f"🎨 DALL-E: Gọi API tạo ảnh..."


                if hasattr(master_app_ref, 'update_status'):
                    master_app_ref.after(0, lambda msg=status_msg_api_call: master_app_ref.update_status(msg))

                logging.info(f"[DALL-E Thread] Gọi API DALL-E (lần {call_idx+1}/{actual_api_calls_needed}), Model: {selected_dalle_model}, n={images_this_call}")
                try:

                    if selected_dalle_model == "dall-e-3":
                        quality_val = self.dalle3_quality_var.get()
                        style_val = self.dalle3_style_var.get()
                        response = client.images.generate(
                            model=selected_dalle_model, prompt=prompt,
                            n=images_this_call, size=size,
                            quality=quality_val, style=style_val,
                            response_format="url"
                        )
                    else: # dall-e-2
                        response = client.images.generate(
                            model=selected_dalle_model, prompt=prompt,
                            n=images_this_call, size=size,
                            response_format="url"
                        )

                    if response.data:
                        for item in response.data:
                            if item.url: generated_image_urls.append(item.url)
                            elif item.b64_json: image_data_list.append(item.b64_json)
                        total_images_generated_so_far += len(response.data) # Cập nhật tổng số ảnh đã có kết quả
                except Exception as api_err:
                    # xử lý lỗi ...
                    logging.error(f"[DALL-E Thread] Lỗi khi gọi API DALL-E lần {call_idx+1}: {api_err}", exc_info=True)
                    _update_ui_from_thread(messagebox.showerror, "Lỗi API DALL-E", f"Không thể tạo ảnh (lần {call_idx+1}):\n{api_err}")
                    _update_ui_from_thread(self._reset_buttons_after_generation, False, f"Lỗi API DALL-E: {str(api_err)[:100]}")
                    return
            # --- KẾT THÚC VÒNG LẶP GỌI API ---

            # Đếm tổng số ảnh đã được API trả về thành công
            total_images_generated = len(generated_image_urls) + len(image_data_list)
            if total_images_generated > 0:
                # Gọi hàm theo dõi, tính mỗi ảnh là 1 "call" cho OpenAI
                self._track_api_call(service_name="openai_calls", units=total_images_generated)

            if not generated_image_urls and not image_data_list:
                logging.warning("[DALL-E Thread] Không có URL/dữ liệu ảnh nào được tạo.")
                _update_ui_from_thread(messagebox.showwarning, "Không có ảnh", "DALL-E không trả về ảnh nào.")
                _update_ui_from_thread(self._reset_buttons_after_generation, False, "Không có ảnh được tạo")
                return

            # Cập nhật trạng thái trước khi tải
            total_images_to_download = len(generated_image_urls) + len(image_data_list)
            if hasattr(master_app_ref, 'update_status'):
                 master_app_ref.after(0, lambda: master_app_ref.update_status(f"🎨 PIU: Chuẩn bị tải {total_images_to_download} ảnh..."))


            saved_file_paths = []
            current_timestamp = int(time.time())

            # Tải ảnh từ URL
            for i, img_url in enumerate(generated_image_urls):
                if master_app_ref.stop_event.is_set(): # Kiểm tra dừng trước mỗi lần tải
                    # ... (xử lý dừng)
                    logging.info("[DALL-E Thread] Yêu cầu dừng từ ứng dụng khi đang tải ảnh.")
                    _update_ui_from_thread(self._reset_buttons_after_generation, False, "Đã hủy bởi người dùng.")
                    return

                # Cập nhật trạng thái tải từng ảnh
                if hasattr(master_app_ref, 'update_status'):
                    status_msg_download = f"🎨 PIU: Đang tải ảnh {i+1}/{total_images_to_download}..."
                    master_app_ref.after(0, lambda msg=status_msg_download: master_app_ref.update_status(msg))
                try:
                    img_response = requests.get(img_url, timeout=60)
                    img_response.raise_for_status()
                    safe_prompt_part = "".join(filter(str.isalnum, prompt))[:20]
                    file_name = f"dalle_{safe_prompt_part}_{current_timestamp}_{i}.png"
                    file_path = os.path.join(output_folder, file_name)
                    with open(file_path, "wb") as f: f.write(img_response.content)
                    saved_file_paths.append(file_path)
                    logging.info(f"[DALL-E Thread] Đã lưu ảnh từ URL: {file_path}")
                except Exception as download_err:
                    logging.error(f"[DALL-E Thread] Lỗi tải ảnh từ URL {img_url}: {download_err}")

            # Xử lý ảnh từ base64
            for i, b64_data in enumerate(image_data_list):
                if master_app_ref.stop_event.is_set(): # Kiểm tra dừng
                    logging.info("[DALL-E Thread] Yêu cầu dừng từ ứng dụng khi đang xử lý ảnh base64.")
                    _update_ui_from_thread(self._reset_buttons_after_generation, False, "Đã hủy bởi người dùng.")
                    return
                # Cập nhật trạng thái xử lý từng ảnh base64
                if hasattr(master_app_ref, 'update_status'):
                    status_msg_b64 = f"🎨 PIU: Đang xử lý ảnh base64 {i+1+len(generated_image_urls)}/{total_images_to_download}..."
                    master_app_ref.after(0, lambda msg=status_msg_b64: master_app_ref.update_status(msg))
                try:
                    img_bytes = base64.b64decode(b64_data)
                    safe_prompt_part = "".join(filter(str.isalnum, prompt))[:20]
                    file_name = f"dalle_{safe_prompt_part}_{current_timestamp}_b64_{i}.png" # Thêm _b64 để phân biệt
                    file_path = os.path.join(output_folder, file_name)
                    with open(file_path, "wb") as f: f.write(img_bytes)
                    saved_file_paths.append(file_path)
                    logging.info(f"[DALL-E Thread] Đã lưu ảnh từ base64: {file_path}")
                except Exception as b64_err:
                    logging.error(f"[DALL-E Thread] Lỗi xử lý ảnh base64: {b64_err}")

            if saved_file_paths:
                msg = f"Đã tạo và lưu thành công {len(saved_file_paths)} ảnh vào thư mục:\n{output_folder}"
                logging.info(f"[DALL-E Thread] {msg}")
                _update_ui_from_thread(messagebox.showinfo, "Hoàn thành", msg)
                _update_ui_from_thread(self._reset_buttons_after_generation, True, f"Đã tạo {len(saved_file_paths)} ảnh.")
            else:
                _update_ui_from_thread(messagebox.showwarning, "Lỗi lưu ảnh", "Không thể lưu bất kỳ ảnh nào đã tạo.")
                _update_ui_from_thread(self._reset_buttons_after_generation, False, "Lỗi lưu ảnh")

        except ImportError:
            logging.error("[DALL-E Thread] Lỗi: Thiếu thư viện OpenAI (trong thread).")
            _update_ui_from_thread(messagebox.showerror, "Lỗi Thư Viện", "Thư viện OpenAI cần thiết chưa được cài đặt.")
            _update_ui_from_thread(self._reset_buttons_after_generation, False, "Lỗi: Thiếu thư viện OpenAI")
        except Exception as e:
            logging.error(f"[DALL-E Thread] Lỗi không mong muốn trong quá trình tạo ảnh DALL-E: {e}", exc_info=True)
            _update_ui_from_thread(messagebox.showerror, "Lỗi Không Mong Muốn", f"Đã xảy ra lỗi:\n{e}")
            _update_ui_from_thread(self._reset_buttons_after_generation, False, f"Lỗi: {str(e)[:100]}")

# Bên trong lớp DalleSettingsWindow
    def _reset_buttons_after_generation(self, success, status_message="Hoàn tất"):
        # --- KHÔI PHỤC NÚT TRÊN APP CHÍNH ---
        active_main_dalle_button_reset = None
        # Sử dụng self.master_app (chính là master_app_ref đã truyền vào thread)
        if hasattr(self.master_app, 'current_view'):
            current_view_on_master_at_reset = self.master_app.current_view
            if current_view_on_master_at_reset == "≡ Tạo Phụ Đề":
                active_main_dalle_button_reset = getattr(self.master_app, 'dalle_button_sub_tab', None)
            elif current_view_on_master_at_reset == "♪ Thuyết Minh":
                active_main_dalle_button_reset = getattr(self.master_app, 'dalle_button_dub_tab', None)

            logging.debug(f"[DALL-E Reset] Current master view: '{current_view_on_master_at_reset}'. Button to reset: {'Found' if active_main_dalle_button_reset else 'Not Found'}")

        if active_main_dalle_button_reset and active_main_dalle_button_reset.winfo_exists():
            self.master_app.after(0, lambda btn=active_main_dalle_button_reset: btn.configure(text="🎨 Tạo Ảnh AI", state=ctk.NORMAL))
            logging.info(f"[DALL-E Reset] Đã khôi phục nút DALL-E trên app chính ({active_main_dalle_button_reset.winfo_name()}) về trạng thái chờ.")
        else:
            # Dự phòng: Nếu không xác định được nút cụ thể, thử khôi phục cả hai
            logging.warning(f"[DALL-E Reset] Không tìm thấy nút DALL-E cụ thể theo view '{getattr(self.master_app, 'current_view', 'N/A')}'. Thử khôi phục cả hai nút chính.")
            if hasattr(self.master_app, 'dalle_button_sub_tab') and self.master_app.dalle_button_sub_tab.winfo_exists():
                self.master_app.after(0, lambda: self.master_app.dalle_button_sub_tab.configure(text="🎨 Tạo Ảnh AI", state=ctk.NORMAL))
            if hasattr(self.master_app, 'dalle_button_dub_tab') and self.master_app.dalle_button_dub_tab.winfo_exists():
                self.master_app.after(0, lambda: self.master_app.dalle_button_dub_tab.configure(text="🎨 Tạo Ảnh AI", state=ctk.NORMAL))

        if hasattr(self, 'generate_button') and self.generate_button.winfo_exists():
            self.generate_button.configure(state="normal", text="🎨 Tạo Ảnh")
        if hasattr(self, 'redraw_button') and self.redraw_button.winfo_exists():
            self.redraw_button.configure(state="normal" if self.last_generation_params else "disabled")
        if hasattr(self, 'cancel_button') and self.cancel_button.winfo_exists():
            # Quyết định state cho nút cancel ở đây, có thể là "normal"
            self.cancel_button.configure(state="normal")

        final_status_app = f"✅ PIU: {status_message}" if success else f"❌ PIU: {status_message}"
        if hasattr(self.master_app, 'update_status'):
            self.master_app.update_status(final_status_app)

        if hasattr(self.master_app, 'is_dalle_processing'):
            self.master_app.is_dalle_processing = False
            logging.debug("[DALL-E Popup] Đã đặt master_app.is_dalle_processing = False")

        # --- BẬT ÂM THANH HIỆN ---
        if success: # Chỉ phát âm thanh khi thành công (hoặc bạn có thể thay đổi điều kiện)
            try:
                play_sound_on_task_complete = False
                sound_file_to_play = ""

                if hasattr(self.master_app, 'download_sound_var'):
                    play_sound_on_task_complete = self.master_app.download_sound_var.get()
                if hasattr(self.master_app, 'download_sound_path_var'):
                    sound_file_to_play = self.master_app.download_sound_path_var.get()
                if play_sound_on_task_complete and \
                   sound_file_to_play and \
                   os.path.isfile(sound_file_to_play) and \
                   'PLAYSOUND_AVAILABLE' in globals() and PLAYSOUND_AVAILABLE and \
                   'play_sound_async' in globals() and callable(play_sound_async):

                    logging.info(f"[DALL-E Popup] Tạo ảnh DALL-E xong, sẽ phát âm thanh: {sound_file_to_play}")
                    play_sound_async(sound_file_to_play)
                elif play_sound_on_task_complete:
                    logging.warning(f"[DALL-E Popup] Đã bật âm thanh hoàn thành nhưng đường dẫn file '{sound_file_to_play}' không hợp lệ, file không tồn tại, hoặc thư viện/hàm 'playsound' không khả dụng.")

            except Exception as sound_err:
                logging.warning(f"[DALL-E Popup] Không thể phát âm thanh báo hoàn tất DALL-E: {sound_err}")

        # Tùy chọn đóng popup nếu thành công
        #if success and self.winfo_exists(): # Thêm kiểm tra self.winfo_exists()
        #     try:
        #         self.destroy()
        #     except Exception as e_destroy:
        #         logging.error(f"Lỗi khi tự động đóng cửa sổ DALL-E: {e_destroy}")



# =====================================================================================================================================
# LỚP WIDGET TOOLTIP (CHÚ THÍCH KHI DI CHUỘT) - PHIÊN BẢN SỬA LỖI CĂN GIỮA & MÀU SẮC
# =====================================================================================================================================
# ----- LỚP TOOLTIP ĐÃ ĐƯỢC TÁCH RA ui/widgets/tooltip.py -----

# =====================================================================================================================================
# LỚP CỬA SỔ QUẢN LÝ METADATA YOUTUBE
# =====================================================================================================================================

