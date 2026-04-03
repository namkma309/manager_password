import string
import secrets
import json
import base64
import uuid
import customtkinter as ctk
from PIL import Image
import qrcode

from crypto_py import SecurityManager
from storage import get_config, set_config, get_all_entries, add_entry, delete_entry

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AuraVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Manager Password")
        self.geometry("750x650")
        self.resizable(False, False)

        self.aes_key = None
        self.vault_data = [] 
        
        self.editing_id = None
        self.pass_visible_state = {}
        self.pass_labels = {}
        self.toggle_btns = {}

        # Nếu chưa có cấu hình trên SQLite -> Setup. Nếu có -> form Đăng nhập Đa cổng.
        saved_totp = get_config("totp_secret")
        if not saved_totp:
            self.show_setup_master_frame()
        else:
            self.show_login_frame()

    # ========================== GIAI ĐOẠN SETUP 1 ==========================
    def show_setup_master_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(frame, text="Thiết Lập Giai Đoạn 1: Khởi Tạo Khóa Chính", font=("Outfit", 26, "bold"), text_color="#8b5cf6").pack(pady=(20, 5))
        ctk.CTkLabel(frame, text="Vui lòng cung cấp Mật khẩu chính (Master Password) để hệ thống thiết lập Khóa mã hóa.\nKhuyến nghị ghi nhớ cẩn thận dữ liệu này.", font=("Outfit", 14), justify="center").pack(pady=(0, 20))

        self.pass_entry = ctk.CTkEntry(frame, placeholder_text="Nhập Mật khẩu chính (Master Password)...", show="*", width=380, height=45, corner_radius=12)
        self.pass_entry.pack(pady=10)
        self.pass_entry.bind("<Return>", lambda event: self.process_setup_step_1())

        self.btn_next = ctk.CTkButton(frame, text="Xác Nhận & Tiếp Tục", width=200, height=45, corner_radius=12, fg_color="#3b82f6", font=("Outfit", 15, "bold"), command=self.process_setup_step_1)
        self.btn_next.pack(pady=20)

        self.err_lbl_1 = ctk.CTkLabel(frame, text="", text_color="#ef4444", font=("Outfit", 13))
        self.err_lbl_1.pack(pady=5)

    def process_setup_step_1(self):
        master_password = self.pass_entry.get().strip()
        if not master_password:
            self.err_lbl_1.configure(text="Lỗi Giao Thức: Vui lòng cung cấp Mật khẩu chính trước khi tiếp tục.")
            return

        # Tính toán thông số PBKDF2 dựa trên hàm băm SHA
        self.temp_pass_signature = SecurityManager.hash_data(master_password)  # Băm đối chiếu
        self.temp_salt = SecurityManager.generate_salt()
        self.temp_aes_key = SecurityManager.derive_key(master_password, self.temp_salt)
        
        self.show_setup_otp_frame()

    # ========================== GIAI ĐOẠN SETUP 2 ==========================
    def show_setup_otp_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        ctk.CTkLabel(frame, text="Thiết Lập Giai Đoạn 2: Xác Thực Đa Yếu Tố (TOTP)", font=("Outfit", 26, "bold"), text_color="#22c55e").pack(pady=(10, 5))
        ctk.CTkLabel(frame, text="Vui lòng quét Mã QR dưới đây bằng ứng dụng Google Authenticator\nđể hoàn tất quy trình liên kết bảo mật chuẩn.", font=("Outfit", 14), justify="center").pack()

        self.temp_totp_secret = SecurityManager.generate_totp_secret()
        uri = SecurityManager.get_totp_uri(self.temp_totp_secret, "Manager_Password_User")

        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((200, 200))
        
        qr_image = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 200))
        qr_label = ctk.CTkLabel(frame, image=qr_image, text="")
        qr_label.pack(pady=10)

        self.otp_entry = ctk.CTkEntry(frame, placeholder_text="Nhập mã xác minh 6 chữ số...", width=260, height=45, corner_radius=12, font=("Outfit", 18, "bold"), justify="center")
        self.otp_entry.pack(pady=10)
        self.otp_entry.bind("<Return>", lambda event: self.process_setup_step_2())

        ctk.CTkButton(frame, text="Xác Minh và Hoàn Tất Thiết Lập", width=260, height=45, corner_radius=12, fg_color="#f59e0b", font=("Outfit", 15, "bold"), command=self.process_setup_step_2).pack(pady=5)

        self.err_lbl_2 = ctk.CTkLabel(frame, text="", text_color="#ef4444", font=("Outfit", 13))
        self.err_lbl_2.pack(pady=5)

    def process_setup_step_2(self):
        code = self.otp_entry.get().strip()
        if not SecurityManager.verify_totp(self.temp_totp_secret, code):
            self.err_lbl_2.configure(text="Lỗi Xác Thực: Mã xác minh TOTP không hợp lệ hoặc đã quá dư lượng thời gian.")
            return

        self.aes_key = self.temp_aes_key
        
        # SQL Insert cấu hình lõi
        set_config("signature", self.temp_pass_signature) 
        set_config("salt", base64.b64encode(self.temp_salt).decode('utf-8'))
        set_config("totp_secret", self.temp_totp_secret)
        set_config("app_aes_key", base64.b64encode(self.aes_key).decode('utf-8'))

        self.show_vault_frame()

    # ========================== ĐĂNG NHẬP ĐA CỔNG (OTP & MASTER PASS) ==========================
    def show_login_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=40, pady=50)

        ctk.CTkLabel(frame, text="Manager Password", font=("Outfit", 34, "bold"), text_color="#8b5cf6").pack(pady=(10, 5))
        ctk.CTkLabel(frame, text="Yêu cầu xác thực bảo mật: Lựa chọn 1 trong 2 phương thức để mở Két", font=("Outfit", 14)).pack(pady=(0, 20))

        self.login_tabs = ctk.CTkTabview(frame, width=320, height=220, corner_radius=12)
        self.login_tabs.pack(pady=10)

        # Tab 1: OTP
        self.login_tabs.add("Mã Smart OTP")
        self.otp_entry = ctk.CTkEntry(self.login_tabs.tab("Mã Smart OTP"), placeholder_text="Mã TOTP", width=220, height=45, corner_radius=8, font=("Outfit", 20, "bold"), justify="center")
        self.otp_entry.pack(pady=20)
        self.otp_entry.bind("<Return>", lambda event: self.handle_login_otp())
        ctk.CTkButton(self.login_tabs.tab("Mã Smart OTP"), text="Xác Thực OTP", width=220, height=40, corner_radius=8, fg_color="#f59e0b", font=("Outfit", 14, "bold"), command=self.handle_login_otp).pack()

        # Tab 2: Master Password
        self.login_tabs.add("Khóa Master Pass")
        self.pass_entry_login = ctk.CTkEntry(self.login_tabs.tab("Khóa Master Pass"), placeholder_text="Nhập Master Password", show="*", width=220, height=45, corner_radius=8)
        self.pass_entry_login.pack(pady=20)
        self.pass_entry_login.bind("<Return>", lambda event: self.handle_login_master())
        ctk.CTkButton(self.login_tabs.tab("Khóa Master Pass"), text="Xác Thực Mật Khẩu", width=220, height=40, corner_radius=8, fg_color="#3b82f6", font=("Outfit", 14, "bold"), command=self.handle_login_master).pack()

        self.error_label = ctk.CTkLabel(frame, text="", text_color="#ef4444", font=("Outfit", 13))
        self.error_label.pack(pady=10)

    def handle_login_otp(self):
        code = self.otp_entry.get().strip()
        saved_secret = get_config("totp_secret")
        
        if not SecurityManager.verify_totp(saved_secret, code):
            self.error_label.configure(text="Lỗi Giao Thức Ủy Quyền: Mã TOTP cung cấp không hợp lệ.")
            return
            
        self.aes_key = base64.b64decode(get_config("app_aes_key"))
        self.load_vault_datastore()

    def handle_login_master(self):
        master_password = self.pass_entry_login.get().strip()
        if not master_password:
            self.error_label.configure(text="Yêu cầu đầu vào: Xin hãy điền Mật Khẩu Khóa Chính.")
            return
            
        saved_signature = get_config("signature")
        hashed_input = SecurityManager.hash_data(master_password)
        
        # So sánh hàm băm tiêu chuẩn để mở khóa
        if hashed_input != saved_signature:
            self.error_label.configure(text="Lỗi Ủy Quyền: Mật khẩu chính (Master Pass) không khớp CSDL.")
            return
            
        # Nạp lại Khóa ngầm từ thuật toán PBKDF2
        saved_salt_b64 = get_config("salt")
        salt_bytes = base64.b64decode(saved_salt_b64)
        self.aes_key = SecurityManager.derive_key(master_password, salt_bytes)
        
        self.load_vault_datastore()

    def load_vault_datastore(self):
        self.error_label.configure(text="")
        self.vault_data.clear()
        
        db_entries = get_all_entries()
        for entry in db_entries:
            decrypted_json = SecurityManager.decrypt_data(
                self.aes_key, entry["iv"], entry["ciphertext"]
            )
            if decrypted_json:
                dec_obj = json.loads(decrypted_json)
                dec_obj['original_id'] = entry['id']
                self.vault_data.append(dec_obj)
        
        self.show_vault_frame()

    # ========================== KHO DỮ LIỆU ĐÃ GIẢI MÃ ==========================
    def show_vault_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.vault_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.vault_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        header = ctk.CTkFrame(self.vault_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header, text="Phân Hệ Quản Trị Dữ Liệu Bảo Mật", font=("Outfit", 22, "bold"), text_color="#22c55e").pack(side="left")
        ctk.CTkButton(header, text="Đăng Xuất Phiên", width=120, height=35, fg_color="#ef4444", hover_color="#dc2626", corner_radius=8, command=self.logout).pack(side="right")

        add_frame = ctk.CTkFrame(self.vault_frame, corner_radius=12)
        add_frame.pack(fill="x", pady=(0, 10), ipadx=10, ipady=10)

        self.in_title = ctk.CTkEntry(add_frame, placeholder_text="Định danh hệ thống (VD: Google)", width=200)
        self.in_title.grid(row=0, column=0, padx=5, pady=5)
        
        self.in_user = ctk.CTkEntry(add_frame, placeholder_text="Tài khoản / Email truy cập", width=200)
        self.in_user.grid(row=0, column=1, padx=5, pady=5)
        
        self.in_pass = ctk.CTkEntry(add_frame, placeholder_text="Mật khẩu bảo mật", width=150)
        self.in_pass.grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkButton(add_frame, text="Khởi tạo ngẫu nhiên", width=130, fg_color="#3b82f6", command=self.generate_random_pass).grid(row=0, column=3, padx=5, pady=5)

        self.btn_save = ctk.CTkButton(add_frame, text="Thêm Bản Ghi Mới Vào Hệ Thống", width=410, command=self.save_entry)
        self.btn_save.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        self.btn_cancel = ctk.CTkButton(add_frame, text="Hủy thao tác điều chỉnh", width=150, fg_color="transparent", border_width=1, state="disabled", text_color_disabled="gray", command=self.cancel_edit)
        self.btn_cancel.grid(row=1, column=2, padx=5, pady=5)

        self.error_add = ctk.CTkLabel(add_frame, text="", text_color="#ef4444", font=("Outfit", 12))
        self.error_add.grid(row=2, column=0, columnspan=4)

        self.scroll_list = ctk.CTkScrollableFrame(self.vault_frame, corner_radius=12, fg_color="#1e293b", height=320)
        self.scroll_list.pack(fill="both", expand=True)

        self.render_list()

    def generate_random_pass(self):
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+"
        pw = ''.join(secrets.choice(chars) for _ in range(16))
        self.in_pass.delete(0, 'end')
        self.in_pass.insert(0, pw)

    def cancel_edit(self):
        self.editing_id = None
        self.in_title.delete(0, 'end')
        self.in_user.delete(0, 'end')
        self.in_pass.delete(0, 'end')
        self.btn_save.configure(text="Thêm Bản Ghi Mới Vào Hệ Thống", fg_color=['#3a7ebf', '#1f538d'])
        self.btn_cancel.configure(state="disabled")
        self.error_add.configure(text="")

    def invoke_edit(self, item):
        self.editing_id = item['original_id']
        self.in_title.delete(0, 'end')
        self.in_title.insert(0, item['title'])
        self.in_user.delete(0, 'end')
        self.in_user.insert(0, item['username'])
        self.in_pass.delete(0, 'end')
        self.in_pass.insert(0, item['password'])
        
        self.btn_save.configure(text="Áp Dụng Cập Nhật Dữ Liệu", fg_color="#f59e0b", hover_color="#d97706")
        self.btn_cancel.configure(state="normal")
        self.error_add.configure(text="Thông Báo: Hệ thống đang chuyển sang trạng thái phân quyền hiệu chỉnh tệp...", text_color="#f59e0b")

    def save_entry(self):
        v_title = self.in_title.get()
        v_user = self.in_user.get()
        v_pass = self.in_pass.get()

        if not v_title or not v_pass:
            self.error_add.configure(text="Lỗi Chỉ Thị: Yêu cầu cung cấp đầy đủ thông số Định danh và Mật khẩu.")
            return
        
        if self.editing_id:
            # Sửa thông tin = Xoá dòng cũ và chèn dòng mới (Bản chất AES không thể cập nhật văn bản tĩnh)
            self.vault_data = [x for x in self.vault_data if x["original_id"] != self.editing_id]
            delete_entry(self.editing_id)

        new_obj = {
            "title": v_title,
            "username": v_user if v_user else "Không cấu hình",
            "password": v_pass
        }

        json_str = json.dumps(new_obj)
        encrypted_res = SecurityManager.encrypt_data(self.aes_key, json_str)
        
        raw_id = self.editing_id if self.editing_id else uuid.uuid4().hex
        
        add_entry(raw_id, encrypted_res["iv"], encrypted_res["ciphertext"])

        new_obj["original_id"] = raw_id
        
        self.vault_data.insert(0, new_obj)

        self.cancel_edit()
        self.error_add.configure(text="Thông Báo: Thao tác biên dịch Bản mã và ghi CSDL hoàn thành.", text_color="#22c55e")
        self.render_list()

    def toggle_password(self, item_id):
        self.pass_visible_state[item_id] = not self.pass_visible_state.get(item_id, False)
        is_visible = self.pass_visible_state[item_id]
        
        target_item = next((x for x in self.vault_data if x['original_id'] == item_id), None)
        if target_item:
            disp_pass = target_item['password'] if is_visible else "••••••••"
            if item_id in self.pass_labels:
                self.pass_labels[item_id].configure(text=disp_pass)
            if item_id in self.toggle_btns:
                self.toggle_btns[item_id].configure(text="👁" if not is_visible else "🙈")

    def render_list(self):
        self.pass_labels.clear()
        self.toggle_btns.clear()
        
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        if len(self.vault_data) == 0:
            lbl = ctk.CTkLabel(self.scroll_list, text="Trạng thái phân hệ: Hiện tại thiết bị lưu trữ đang trống. Vui lòng thiết lập Bản mã mới.", text_color="gray")
            lbl.pack(pady=40)
            return

        for idx, item in enumerate(self.vault_data):
            row = ctk.CTkFrame(self.scroll_list, corner_radius=8, fg_color="#334155")
            row.pack(fill="x", padx=5, pady=5)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", padx=10, pady=5)
            
            ctk.CTkLabel(info_frame, text=f"{item['title']} - {item['username']}", anchor="w", font=("Outfit", 14, "bold")).pack(anchor="w")
            
            is_visible = self.pass_visible_state.get(item['original_id'], False)
            disp_pass = item['password'] if is_visible else "••••••••"
            lbl_pass = ctk.CTkLabel(info_frame, text=f"{disp_pass}", anchor="w", font=("Outfit", 12), text_color="#94a3b8")
            lbl_pass.pack(anchor="w")
            self.pass_labels[item['original_id']] = lbl_pass

            action_frame = ctk.CTkFrame(row, fg_color="transparent")
            action_frame.pack(side="right", padx=10, pady=10)

            btn_tog = ctk.CTkButton(action_frame, text="👁" if not is_visible else "🙈", width=40, fg_color="transparent", border_width=1, command=lambda i=item['original_id']: self.toggle_password(i))
            btn_tog.pack(side="left", padx=3)
            self.toggle_btns[item['original_id']] = btn_tog
            
            ctk.CTkButton(action_frame, text="Copy", width=65, fg_color="#6366f1", hover_color="#4f46e5", command=lambda pw=item['password']: self.copy_to_clipboard(pw)).pack(side="left", padx=3)
            ctk.CTkButton(action_frame, text="Sửa", width=90, fg_color="#f59e0b", hover_color="#d97706", command=lambda it=item: self.invoke_edit(it)).pack(side="left", padx=3)
            ctk.CTkButton(action_frame, text="Xóa", width=70, fg_color="#ef4444", hover_color="#dc2626", command=lambda i=item['original_id']: self.delete_entry(i)).pack(side="left", padx=3)

    def delete_entry(self, entry_id):
        self.vault_data = [x for x in self.vault_data if x["original_id"] != entry_id]
        delete_entry(entry_id) # Trực tiếp can thiệp SQL
        self.render_list()

    def copy_to_clipboard(self, pw):
        self.clipboard_clear()
        self.clipboard_append(pw)
        self.error_add.configure(text="Trạng thái hệ thống: Đã copy mật khẩu vào bộ nhớ tạm", text_color="#22c55e")

    def logout(self):
        self.aes_key = None
        self.vault_data.clear()
        self.pass_visible_state.clear()
        self.pass_labels.clear()
        self.toggle_btns.clear()
        self.show_login_frame()

if __name__ == "__main__":
    app = AuraVaultApp()
    app.mainloop()
