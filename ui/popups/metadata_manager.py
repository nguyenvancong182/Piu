"""
MetadataManagerWindow class for Piu application.
Manages metadata for YouTube batch uploads.
"""
import customtkinter as ctk
import logging
import os
import json
import csv
from tkinter import filedialog, messagebox
from ui.widgets.menu_utils import textbox_right_click_menu


class MetadataManagerWindow(ctk.CTkToplevel):
    """
    Cửa sổ chuyên dụng để quản lý metadata (tiêu đề, mô tả, tags...) 
    cho các video sẽ được upload hàng loạt. Hỗ trợ nhập liệu trực tiếp, 
    lưu/mở file JSON và nhập/xuất từ file CSV.
    >>> PHIÊN BẢN NÂNG CẤP: Giao diện và logic tự động lưu khi đóng. <<<
    """

    # HÀM KHỞI TẠO ĐÃ ĐƯỢC CẬP NHẬT GIAO DIỆN VÀ LOGIC
    def __init__(self, master_app):
        super().__init__(master_app)
        
        self.transient(master_app)
        self.withdraw() 
        self.master_app = master_app
        self.title("🗂 Trình Quản lý Metadata Hàng loạt cho YouTube")

        self.desired_popup_width = 950
        self.desired_popup_height = 700      

        self.grab_set()
        self.all_rows = []

        # --- Tạo các widget giao diện ---
        toolbar_frame = ctk.CTkFrame(self)
        toolbar_frame.pack(fill="x", padx=10, pady=10)
        toolbar_frame.grid_columnconfigure((0, 6), weight=1)
        ctk.CTkButton(toolbar_frame, text="💾 Mở File Master JSON...", command=self._load_from_master_json).grid(row=0, column=1, padx=5)
        ctk.CTkButton(toolbar_frame, text="✅ Lưu File Master JSON", command=self._save_to_master_json, fg_color="#1f6aa5").grid(row=0, column=2, padx=5)
        ctk.CTkLabel(toolbar_frame, text="|").grid(row=0, column=3, padx=10)
        ctk.CTkButton(toolbar_frame, text="📥 Nhập từ CSV...", command=self._import_from_csv).grid(row=0, column=4, padx=5)
        ctk.CTkButton(toolbar_frame, text="📤 Xuất ra CSV...", command=self._export_to_csv).grid(row=0, column=5, padx=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(expand=True, fill="both", padx=10, pady=0)

        # GÁN SỰ KIỆN LĂN CHUỘT CHO CỬA SỔ NÀY
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        bottom_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(bottom_frame, text="🗑 Xóa tất cả", command=self._clear_all_rows, fg_color="#E53935", hover_color="#C62828").grid(row=0, column=0, sticky="w")
        
        # KHUNG CHỨA NÚT THÊM VÀ CHECKBOX
        center_controls_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        center_controls_frame.grid(row=0, column=1) # Đặt vào giữa
        ctk.CTkButton(center_controls_frame, text="+ Thêm Video Mới", command=self._add_video_entry_row).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(center_controls_frame, text="Tự động tăng số thumbnail", variable=self.master_app.metadata_auto_increment_thumb_var).pack(side="left")
        # KẾT THÚC KHUNG

        ctk.CTkButton(bottom_frame, text="Lưu & Đóng", command=self._save_and_close, fg_color="#1D8348", hover_color="#145A32").grid(row=0, column=2, sticky="e")

        self._load_initial_data() 
        self.after(50, self._center_window)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # Hàm xử lý sự kiện lăn chuột để tăng tốc độ cuộn
    def _on_mouse_wheel(self, event):
        """Hàm xử lý sự kiện lăn chuột để tăng tốc độ cuộn."""
        if not self.scrollable_frame or not self.scrollable_frame.winfo_exists():
            return

        # Tốc độ lăn chuột, bạn có thể điều chỉnh số này
        scroll_speed_multiplier = 36 
        
        # Xử lý cho Windows (event.delta) và các hệ điều hành khác (event.num)
        # CustomTkinter đã chuẩn hóa event.delta nên chỉ cần kiểm tra nó
        if event.delta > 0:
            self.scrollable_frame._parent_canvas.yview_scroll(-1 * scroll_speed_multiplier, "units")
        elif event.delta < 0:
            self.scrollable_frame._parent_canvas.yview_scroll(1 * scroll_speed_multiplier, "units")
        
        # Ngăn không cho sự kiện lăn chuột mặc định (chậm hơn) được thực thi
        return "break"

    
    # Hàm helper để căn giữa cửa sổ
    def _center_window(self):
        try:
            # Lấy các thông số của cửa sổ chính
            master_x = self.master_app.winfo_x()
            master_y = self.master_app.winfo_y()
            master_width = self.master_app.winfo_width()
            master_height = self.master_app.winfo_height()

            # Sử dụng trực tiếp kích thước đã lưu trong self
            popup_width = self.desired_popup_width
            popup_height = self.desired_popup_height

            # Tính toán vị trí để căn giữa
            center_x = master_x + (master_width // 2) - (popup_width // 2)
            center_y = master_y + (master_height // 2) - (popup_height // 2)

            # Đảm bảo cửa sổ không bị hiện ra ngoài màn hình
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            
            if center_x + popup_width > screen_width:
                center_x = screen_width - popup_width
            if center_y + popup_height > screen_height:
                center_y = screen_height - popup_height
            if center_x < 0:
                center_x = 0
            if center_y < 0:
                center_y = 0

            # Áp dụng vị trí và kích thước cuối cùng
            self.geometry(f"{popup_width}x{popup_height}+{int(center_x)}+{int(center_y)}")
            
            # Buộc ứng dụng phải xử lý hết các tác vụ chờ,
            self.update_idletasks()
            
            # Hiện cửa sổ lên sau khi mọi thứ đã được tính toán và sắp xếp xong
            self.deiconify() 
            
        except Exception as e:
            logging.warning(f"Không thể căn giữa cửa sổ Metadata: {e}")
            # Nếu có lỗi, vẫn phải hiện cửa sổ lên để không bị treo
            self.deiconify()

    # HÀM MỚI: Tách logic thu thập dữ liệu
    def _collect_data_from_ui(self):
        master_data = {}
        empty_key_count = 0
        for i, row_widgets in enumerate(self.all_rows):
            key = row_widgets["key"].get().strip()
            if not key:
                empty_key_count += 1
                continue
            master_data[key] = {
                "title": row_widgets["title"].get().strip(),
                "description": row_widgets["description"].get("1.0", "end-1c").strip(),
                "tags": row_widgets["tags"].get().strip(),
                "thumbnail": row_widgets["thumbnail"].get().strip(),
                "playlist": row_widgets["playlist"].get().strip()
            }
        if empty_key_count > 0:
            logging.warning(f"MetadataManager: Đã bỏ qua {empty_key_count} hàng vì 'Key' trống.")
        return master_data

    # HÀM MỚI: Tự động lưu và đóng cửa sổ
    def _save_and_close(self):
        logging.info("Yêu cầu đóng cửa sổ Metadata, thực hiện lưu tự động...")
        master_data = self._collect_data_from_ui()
        if not master_data:
            self.destroy()
            return
            
        save_path = self.master_app.cfg.get('last_master_metadata_path')

        if not save_path or not os.path.isdir(os.path.dirname(save_path)):
            save_path = filedialog.asksaveasfilename(
                title="Lưu File Master Metadata (Lần đầu)",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile="master_metadata.json",
                parent=self
            )
            if not save_path:
                self.destroy()
                return

        try:
            with open(save_path, 'w', encoding='utf-8') as json_file:
                json.dump(master_data, json_file, ensure_ascii=False, indent=2)
            
            self.master_app.cfg['last_master_metadata_path'] = save_path
            self.master_app.save_current_config()
            self.master_app._load_master_metadata_cache()
            
            logging.info(f"Đã tự động lưu thành công metadata vào: {save_path}")
        except Exception as e:
            logging.error(f"Lỗi khi tự động lưu file Master JSON: {e}", exc_info=True)

        self.destroy()

# Hàm tạo giao diện Popup
    def _add_video_entry_row(self, key="", title="", desc="", tags="", thumb="", playlist=""):

        # BƯỚC 1: KHỞI TẠO DICTIONARY WIDGET NGAY TỪ ĐẦU
        row_widgets = {}

        # Frame chính cho cả hàng
        row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=("gray88", "#2B2B2B"), border_width=1, border_color="gray50")
        row_frame.pack(fill="x", pady=(5, 3), padx=5)
        row_frame.grid_columnconfigure(1, weight=1)
        row_widgets["frame"] = row_frame # Thêm vào dict

        # Cột 0: Số thứ tự (STT)
        stt_label = ctk.CTkLabel(row_frame, text="", font=("Segoe UI", 16, "bold"), width=35)
        stt_label.grid(row=0, column=0, rowspan=6, padx=(5, 10), pady=10, sticky="n")
        row_widgets["stt_label"] = stt_label # Thêm vào dict

        # Cột 2: Frame chứa các nút điều khiển
        controls_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=2, padx=5, pady=5, sticky="ne")

        # BƯỚC 2: TẠO CÁC NÚT VÀ TRUYỀN LAMBDA VỚI BIẾN row_widgets ĐÃ TỒN TẠI
        # Nút Xóa
        delete_button = ctk.CTkButton(controls_frame, text="✕", fg_color="transparent", hover_color="#E53935", text_color=("gray10", "gray80"), width=28, height=28,
                                      command=lambda rw=row_widgets: self._remove_video_entry_row(rw))
        delete_button.pack(side="right", padx=(2,0))

        # Nút Nhân bản
        duplicate_button = ctk.CTkButton(controls_frame, text="❐", fg_color="transparent", hover_color="#4A4D50", text_color=("gray10", "gray80"), width=28, height=28,
                                         command=lambda rw=row_widgets: self._duplicate_row(rw))
        duplicate_button.pack(side="right")

        # Cột 1: Frame chứa toàn bộ nội dung chính (labels và ô nhập)
        content_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        content_frame.grid(row=0, column=1, rowspan=6, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(1, weight=1)

        # BƯỚC 3: TẠO CÁC WIDGET NHẬP LIỆU VÀ THÊM VÀO DICTIONARY
        # Hàng 0: Key
        ctk.CTkLabel(content_frame, text="Key:", anchor="e").grid(row=0, column=0, padx=(0, 5), pady=2, sticky="e")
        key_entry = ctk.CTkEntry(content_frame, placeholder_text="Tên file gốc không đuôi, ví dụ: Piu_Tap_1")
        key_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        key_entry.insert(0, key)
        key_entry.bind("<Button-3>", textbox_right_click_menu) # <<< THÊM DÒNG NÀY
        row_widgets["key"] = key_entry

        # Hàng 1: Title
        ctk.CTkLabel(content_frame, text="Tiêu đề:", anchor="e").grid(row=1, column=0, padx=(0, 5), pady=2, sticky="e")
        title_entry = ctk.CTkEntry(content_frame, placeholder_text="Tiêu đề sẽ hiển thị trên YouTube")
        title_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        title_entry.insert(0, title)
        title_entry.bind("<Button-3>", textbox_right_click_menu) # <<< THÊM DÒNG NÀY
        row_widgets["title"] = title_entry

        # Hàng 2: Description
        ctk.CTkLabel(content_frame, text="Mô tả:", anchor="ne").grid(row=2, column=0, padx=(0, 5), pady=(5, 2), sticky="e")
        desc_textbox = ctk.CTkTextbox(content_frame, height=100, wrap="word")
        desc_textbox.grid(row=2, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        desc_textbox.insert("1.0", desc)
        desc_textbox.bind("<Button-3>", textbox_right_click_menu) # <<< THÊM DÒNG NÀY
        row_widgets["description"] = desc_textbox

        # Hàng 3: Tags
        ctk.CTkLabel(content_frame, text="Tags:", anchor="e").grid(row=3, column=0, padx=(0, 5), pady=2, sticky="e")
        tags_entry = ctk.CTkEntry(content_frame, placeholder_text="Các tag, cách nhau bởi dấu phẩy")
        tags_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        tags_entry.insert(0, tags)
        tags_entry.bind("<Button-3>", textbox_right_click_menu) # <<< THÊM DÒNG NÀY
        row_widgets["tags"] = tags_entry

        # Hàng 4: Playlist
        ctk.CTkLabel(content_frame, text="Playlist:", anchor="e").grid(row=4, column=0, padx=(0, 5), pady=2, sticky="e")
        playlist_entry = ctk.CTkEntry(content_frame, placeholder_text="Tên playlist (tùy chọn)")
        playlist_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        playlist_entry.insert(0, playlist)
        playlist_entry.bind("<Button-3>", textbox_right_click_menu) # <<< THÊM DÒNG NÀY
        row_widgets["playlist"] = playlist_entry

        # Hàng 5: Thumbnail
        ctk.CTkLabel(content_frame, text="Thumbnail:", anchor="e").grid(row=5, column=0, padx=(0, 5), pady=2, sticky="e")
        thumb_entry = ctk.CTkEntry(content_frame, placeholder_text="Đường dẫn đầy đủ đến file ảnh")
        thumb_entry.grid(row=5, column=1, padx=5, pady=2, sticky="ew")
        thumb_entry.insert(0, thumb)
        thumb_entry.bind("<Button-3>", textbox_right_click_menu) # <<< THÊM DÒNG NÀY
        row_widgets["thumbnail"] = thumb_entry

        def _select_thumb_file():
            path = filedialog.askopenfilename(title="Chọn ảnh Thumbnail", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")])
            if path:
                thumb_entry.delete(0, "end")
                thumb_entry.insert(0, path)

        ctk.CTkButton(content_frame, text="Chọn...", width=80, command=_select_thumb_file).grid(row=5, column=2, padx=(5,0), pady=2)

        # (Tùy chọn) Thêm các nút vừa tạo vào dictionary
        row_widgets['delete_button'] = delete_button
        row_widgets['duplicate_button'] = duplicate_button
        
        # BƯỚC 4: THÊM DICTIONARY ĐÃ HOÀN THIỆN VÀO DANH SÁCH CHUNG (CHỈ 1 LẦN)
        self.all_rows.append(row_widgets)
        self._update_row_numbers()

    def _remove_video_entry_row(self, row_widgets_to_remove):
        """Xóa một hàng widget khỏi giao diện và khỏi danh sách theo dõi."""
        try:
            self.all_rows.remove(row_widgets_to_remove)
            row_widgets_to_remove["frame"].destroy()
            logging.info("Đã xóa một hàng metadata.")
            self._update_row_numbers() # Cập nhật lại STT sau khi xóa
        except (ValueError, AttributeError) as e:
            logging.error(f"Lỗi khi xóa hàng metadata: {e}")


# Nhân bản một hàng dữ liệu và chèn nó ngay bên dưới hàng gốc
    def _duplicate_row(self, source_row_widgets):
        """
        (PHIÊN BẢN NÂNG CẤP VỚI TỰ ĐỘNG TĂNG SỐ VÀ THUMBNAIL)
        Nhân bản một hàng dữ liệu, tự động tăng số thứ tự ở cuối key và thumbnail,
        chèn nó ngay bên dưới hàng gốc, và tự động cuộn đến.
        """
        logging.info("Đang nhân bản một hàng metadata (với logic tăng số)...")
        try:
            source_index = self.all_rows.index(source_row_widgets)
            key = source_row_widgets["key"].get().strip()
            title = source_row_widgets["title"].get().strip()
            desc = source_row_widgets["description"].get("1.0", "end-1c").strip()
            tags = source_row_widgets["tags"].get().strip()
            thumb = source_row_widgets["thumbnail"].get().strip()
            playlist = source_row_widgets["playlist"].get().strip()

            all_existing_keys = {row["key"].get().strip() for row in self.all_rows}

            # --- Logic thông minh để tạo key mới (giữ nguyên) ---
            new_key = ""
            match_key = re.search(r'(\d+)$', key)
            if match_key:
                base_name_key = key[:match_key.start()]
                current_number_key = int(match_key.group(1))
                next_number_key = current_number_key + 1
                while True:
                    candidate_key = f"{base_name_key}{next_number_key}"
                    if candidate_key not in all_existing_keys:
                        new_key = candidate_key
                        break
                    next_number_key += 1
            else:
                next_number_key = 2
                while True:
                    candidate_key = f"{key}_{next_number_key}"
                    if candidate_key not in all_existing_keys:
                        new_key = candidate_key
                        break
                    next_number_key += 1
            
            # <<< BẮT ĐẦU KHỐI LOGIC MỚI CHO THUMBNAIL >>>
            new_thumb = thumb # Mặc định là giữ nguyên đường dẫn cũ
            if self.master_app.metadata_auto_increment_thumb_var.get() and thumb:
                try:
                    dir_name = os.path.dirname(thumb)
                    base_name = os.path.basename(thumb)
                    filename_no_ext, ext = os.path.splitext(base_name)

                    # Tìm số cuối cùng trong tên file
                    match_thumb = re.search(r'(\d+)(?!.*\d)', filename_no_ext)

                    if match_thumb:
                        number_str = match_thumb.group(1)
                        original_length = len(number_str) # Giữ lại số 0 ở đầu (ví dụ: 01, 007)
                        number = int(number_str)
                        new_number = number + 1
                        
                        # Thay thế số cũ bằng số mới
                        start, end = match_thumb.span(1)
                        new_filename_no_ext = filename_no_ext[:start] + str(new_number).zfill(original_length) + filename_no_ext[end:]
                        
                        # Ghép lại thành đường dẫn hoàn chỉnh
                        new_base_name = new_filename_no_ext + ext
                        new_thumb = os.path.join(dir_name, new_base_name)
                        logging.info(f"Đã tự động tăng thumbnail: '{thumb}' -> '{new_thumb}'")
                    else:
                        logging.warning(f"Không tìm thấy số để tăng trong tên thumbnail: '{base_name}'")
                except Exception as e_thumb:
                    logging.error(f"Lỗi khi xử lý tăng số thumbnail: {e_thumb}")
            # <<< KẾT THÚC KHỐI LOGIC MỚI CHO THUMBNAIL >>>

            self._add_video_entry_row(
                key=new_key,
                title=title,
                desc=desc,
                tags=tags,
                thumb=new_thumb, # <<< SỬA Ở ĐÂY
                playlist=playlist
            )

            new_row_widget_dict = self.all_rows.pop() 
            self.all_rows.insert(source_index + 1, new_row_widget_dict)
            new_row_widget_dict["frame"].pack_configure(after=source_row_widgets["frame"])
            self._update_row_numbers()
            self.after(50, lambda: self._scroll_to_widget(new_row_widget_dict["frame"]))

            logging.info(f"Đã nhân bản hàng có key '{key}' thành '{new_key}'.")

        except (ValueError, IndexError) as e:
            logging.error(f"Lỗi khi nhân bản hàng: Không tìm thấy hàng gốc trong danh sách. Lỗi: {e}")
        except Exception as e:
            logging.error(f"Lỗi không mong muốn khi nhân bản hàng: {e}", exc_info=True)


    def _scroll_to_widget(self, widget_to_see):
        """Hàm helper để cuộn CTkScrollableFrame đến một widget cụ thể."""
        try:
            self.update_idletasks() # Bắt buộc giao diện phải tính toán xong vị trí
            
            # Lấy vị trí tương đối của widget so với khung cuộn
            widget_y = widget_to_see.winfo_y()
            
            # Lấy chiều cao tổng của toàn bộ nội dung bên trong khung cuộn
            content_height = self.scrollable_frame._parent_canvas.winfo_height()
            
            # Tính toán vị trí cần cuộn đến (từ 0.0 đến 1.0)
            # Chỉ cuộn nếu widget nằm ngoài tầm nhìn
            scroll_position = self.scrollable_frame._parent_canvas.yview()
            if not (scroll_position[0] < (widget_y / content_height) < scroll_position[1]):
                 self.scrollable_frame._parent_canvas.yview_moveto(widget_y / content_height)

        except Exception as e:
            logging.warning(f"Lỗi khi tự động cuộn đến widget: {e}")


# Xóa tất cả các hàng nhập liệu sau khi hỏi xác nhận
    def _clear_all_rows(self):
        """Xóa tất cả các hàng nhập liệu sau khi hỏi xác nhận."""
        if not self.all_rows:
            return # Không có gì để xóa

        answer = messagebox.askyesno(
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa tất cả {len(self.all_rows)} mục đang có không?",
            icon='warning',
            parent=self
        )
        if answer:
            # Lặp qua một bản sao của list để có thể xóa an toàn
            for row_widgets in list(self.all_rows):
                self._remove_video_entry_row(row_widgets)
            logging.info("Đã xóa tất cả các hàng metadata.")

# Duyệt qua tất cả các hàng và cập nhật lại nhãn số thứ tự
    def _update_row_numbers(self):
        """Duyệt qua tất cả các hàng và cập nhật lại nhãn số thứ tự."""
        for i, row_widgets in enumerate(self.all_rows):
            stt_label = row_widgets.get("stt_label")
            if stt_label and stt_label.winfo_exists():
                stt_label.configure(text=f"{i + 1}.")


# Thu thập dữ liệu từ tất cả các hàng UI và lưu vào một file JSON
    def _save_to_master_json(self):
        """Thu thập dữ liệu từ tất cả các hàng UI và lưu vào một file JSON."""
        logging.info("Bắt đầu quá trình lưu file Master JSON.")
        
        # 1. Kiểm tra xem có dữ liệu để lưu không
        if not self.all_rows:
            messagebox.showinfo("Thông báo", "Không có dữ liệu để lưu.", parent=self)
            return

        # 2. Tạo dictionary để chứa dữ liệu
        master_data = {}
        empty_key_count = 0

        # 3. Lặp qua từng hàng widget để lấy dữ liệu
        for i, row_widgets in enumerate(self.all_rows):
            key = row_widgets["key"].get().strip()
            
            # Kiểm tra xem key có bị trống không
            if not key:
                empty_key_count += 1
                continue # Bỏ qua hàng này nếu key trống

            # Lấy dữ liệu từ các ô nhập liệu khác
            master_data[key] = {
                "title": row_widgets["title"].get().strip(),
                "description": row_widgets["description"].get("1.0", "end-1c").strip(),
                "tags": row_widgets["tags"].get().strip(),
                "thumbnail": row_widgets["thumbnail"].get().strip(),
                "playlist": row_widgets["playlist"].get().strip()
            }
        
        # 4. Cảnh báo nếu có hàng bị bỏ qua do key trống
        if empty_key_count > 0:
            messagebox.showwarning("Cảnh báo", 
                                  f"Đã bỏ qua {empty_key_count} hàng vì 'Key (Tên file gốc)' bị để trống.", 
                                  parent=self)
        
        if not master_data:
            messagebox.showerror("Lỗi", "Không có dữ liệu hợp lệ (Key không được để trống) để lưu.", parent=self)
            return

        # 5. Mở hộp thoại "Save As" để người dùng chọn nơi lưu file
        file_path = filedialog.asksaveasfilename(
            title="Lưu File Master Metadata",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="master_metadata.json",
            parent=self
        )

        if not file_path:
            logging.info("Người dùng đã hủy lưu file Master JSON.")
            return

        # 6. Ghi dictionary vào file JSON
        try:
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(master_data, json_file, ensure_ascii=False, indent=2) # indent=2 để file JSON đẹp và dễ đọc
            
            logging.info(f"Đã lưu thành công metadata vào: {file_path}")
            messagebox.showinfo("Thành công", f"Đã lưu thành công {len(master_data)} mục vào file:\n{os.path.basename(file_path)}", parent=self)

            # Lưu lại đường dẫn file vừa lưu vào app chính để có thể tự động tải lần sau
            if hasattr(self.master_app, 'cfg'):
                self.master_app.cfg['last_master_metadata_path'] = file_path
                # self.master_app.save_current_config() # Cân nhắc chỉ lưu khi đóng app
            
        except Exception as e:
            logging.error(f"Lỗi khi lưu file Master JSON: {e}", exc_info=True)
            messagebox.showerror("Lỗi Lưu File", f"Không thể lưu file.\nLỗi: {e}", parent=self)

            
# Mở hộp thoại để chọn và tải dữ liệu từ một file Master JSON
    def _load_from_master_json(self):
        """Mở hộp thoại để chọn và tải dữ liệu từ một file Master JSON."""
        file_path = filedialog.askopenfilename(
            title="Mở File Master Metadata",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self
        )
        if file_path:
            self._load_and_populate_from_path(file_path)


# Tự động tải dữ liệu từ file master JSON được lưu cuối cùng trong config.
    def _load_initial_data(self):
        """Tự động tải dữ liệu từ file master JSON được lưu cuối cùng trong config."""
        last_file_path = self.master_app.cfg.get('last_master_metadata_path')
        if last_file_path and os.path.exists(last_file_path):
            logging.info(f"[MetadataManager] Tìm thấy file master metadata cuối cùng. Đang tự động tải: {last_file_path}")
            self._load_and_populate_from_path(last_file_path)
        else:
            # Nếu không có file nào được lưu, thêm một hàng mẫu
            self._add_video_entry_row()


#  Xóa các hàng hiện tại và vẽ lại toàn bộ giao diện từ một DANH SÁCH các dictionary.
    def _populate_ui_from_data(self, data_list): # Sửa tên tham số cho rõ ràng
        """
        (PHIÊN BẢN SỬA LỖI)
        Xóa các hàng hiện tại và vẽ lại toàn bộ giao diện từ một DANH SÁCH các dictionary.
        """
        # 1. Xóa tất cả các hàng hiện có trên giao diện
        for row_widgets in self.all_rows:
            row_widgets["frame"].destroy()
        self.all_rows.clear() # Dọn dẹp danh sách theo dõi

        # 2. Tạo các hàng mới từ dữ liệu đã nhập
        # Sửa vòng lặp for để duyệt qua một list, không phải dict.items()
        for item_data in data_list:
            # Lấy dữ liệu từ mỗi dictionary trong list
            key = item_data.get('identifier', '')
            title = item_data.get('title', '')
            desc = item_data.get('description', '')
            tags = item_data.get('tags', '')
            thumb = item_data.get('thumbnail', '')
            playlist = item_data.get('playlist', '')
            
            # Gọi hàm tạo hàng giao diện của bạn
            self._add_video_entry_row(
                key=key,
                title=title,
                desc=desc,
                tags=tags,
                thumb=thumb,
                playlist=playlist
            )


# 2 Hàm Nhập Xuất File Csv
    def _import_from_csv(self):
        """Mở hộp thoại để chọn và nhập dữ liệu từ file CSV."""
        csv_path = filedialog.askopenfilename(
            title="Chọn file CSV chứa Metadata",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=self
        )
        if not csv_path:
            return

        try:
            imported_data = {} # Dùng dictionary để tránh key trùng lặp
            with open(csv_path, mode='r', newline='', encoding='utf-8-sig') as csv_file:
                # Dùng DictReader để đọc theo tên cột, rất tiện lợi và an toàn
                reader = csv.DictReader(csv_file)
                # Lấy tên các cột, loại bỏ khoảng trắng thừa
                fieldnames = [name.strip() for name in reader.fieldnames]
                if 'identifier' not in fieldnames:
                    messagebox.showerror("Lỗi Cột", "File CSV phải có một cột tên là 'identifier' để làm key định danh.", parent=self)
                    return

                for row in reader:
                    # Lấy key và đảm bảo nó không rỗng
                    identifier = row.get('identifier', '').strip()
                    if identifier:
                        # Chỉ lấy các key hợp lệ từ fieldnames
                        clean_row = {key.strip(): val for key, val in row.items() if key.strip() in fieldnames}
                        imported_data[identifier] = clean_row
            
            # Gọi hàm helper để điền dữ liệu lên UI
            # Chuyển đổi từ dict của dict sang list của dict để tương thích
            data_list_for_ui = []
            for key, metadata in imported_data.items():
                metadata['identifier'] = key # Đảm bảo 'identifier' có trong metadata
                data_list_for_ui.append(metadata)

            self._populate_ui_from_data(data_list_for_ui)
            messagebox.showinfo("Thành công", f"Đã nhập và hiển thị thành công {len(data_list_for_ui)} mục từ file CSV.", parent=self)

        except Exception as e:
            logging.error(f"Lỗi khi nhập file CSV: {e}", exc_info=True)
            messagebox.showerror("Lỗi Nhập File", f"Không thể xử lý file CSV.\nLỗi: {e}", parent=self)


    def _export_to_csv(self):
        """Thu thập dữ liệu hiện tại trên UI và xuất ra file CSV."""
        if not self.all_rows:
            messagebox.showinfo("Thông báo", "Không có dữ liệu để xuất.", parent=self)
            return

        csv_path = filedialog.asksaveasfilename(
            title="Lưu Metadata ra file CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="piu_metadata_export.csv",
            parent=self
        )
        if not csv_path:
            return

        try:
            # Định nghĩa các tên cột cho file CSV (thứ tự sẽ được ghi theo list này)
            fieldnames = ['identifier', 'title', 'description', 'tags', 'thumbnail', 'playlist']
            
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader() # Ghi dòng tiêu đề

                # Lặp qua các widget trên giao diện để lấy dữ liệu
                for row_widgets in self.all_rows:
                    writer.writerow({
                        'identifier': row_widgets['key'].get(),
                        'title': row_widgets['title'].get(),
                        'description': row_widgets['description'].get("1.0", "end-1c"), # Lấy từ Textbox
                        'tags': row_widgets['tags'].get(),
                        'thumbnail': row_widgets['thumbnail'].get(),
                        'playlist': row_widgets['playlist'].get()
                    })
            
            messagebox.showinfo("Thành công", f"Đã xuất thành công {len(self.all_rows)} mục ra file CSV.", parent=self)
        except Exception as e:
            logging.error(f"Lỗi khi xuất ra file CSV: {e}", exc_info=True)
            messagebox.showerror("Lỗi Xuất File", f"Không thể lưu file CSV.\nLỗi: {e}", parent=self)

# Hàm helper: Đọc dữ liệu từ một đường dẫn file JSON và điền vào UI
    def _load_and_populate_from_path(self, file_path):
        """Hàm helper: Đọc dữ liệu từ một đường dẫn file JSON và điền vào UI."""
        if not file_path or not os.path.exists(file_path):
            logging.warning(f"Đường dẫn file metadata không hợp lệ: {file_path}")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                master_data_dict = json.load(f)

            if not isinstance(master_data_dict, dict):
                messagebox.showerror("Lỗi Định Dạng", "File JSON không chứa dữ liệu hợp lệ.", parent=self)
                return

            data_list_for_ui = []
            for key, metadata in master_data_dict.items():
                metadata['identifier'] = key
                data_list_for_ui.append(metadata)

            self._populate_ui_from_data(data_list_for_ui)
            
            # Cập nhật đường dẫn file đã mở thành công
            if hasattr(self.master_app, 'cfg'):
                self.master_app.cfg['last_master_metadata_path'] = file_path

        except json.JSONDecodeError as e:
            error_message = f"File JSON có lỗi cú pháp!\n\nLỗi: {e.msg}\nTại dòng: {e.lineno}\nTại cột: {e.colno}"
            logging.error(f"Lỗi parse JSON file '{file_path}': {e}")
            messagebox.showerror("Lỗi Cú Pháp JSON", error_message, parent=self)
        except Exception as e:
            logging.error(f"Lỗi khi mở file Master JSON '{file_path}': {e}", exc_info=True)
            messagebox.showerror("Lỗi Mở File", f"Không thể đọc file.\nLỗi: {e}", parent=self)


# ----- KẾT THÚC LỚP METADATAMANAGER WINDOW -----           


# =====================================================================================================================================
# LỚP GIAO DIỆN VÀ LOGIC CHO TAB AI BIÊN TẬP HÀNG LOẠT (PHIÊN BẢN 3 TEXTBOX)
# =====================================================================================================================================

