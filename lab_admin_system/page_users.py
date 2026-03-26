import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

class UsersPage(ctk.CTkFrame):
    def __init__(self, parent, spreadsheet):
        super().__init__(parent, fg_color="#F8F9FA")
        
        self.spreadsheet = spreadsheet
        self.current_overlay = None
        
        self.headers = ["UserID", "Name", "Year", "Advisor", "RegisDate", "Status"]
        
        self.current_tab = "Users"
        self.users_cache = []
        
        self.render_ui()

    def refresh_page(self):
        self.close_overlay()
        self.load_data_from_sheet()
        self.render_list()

    def close_overlay(self):
        if self.current_overlay:
            self.current_overlay.destroy()
            self.current_overlay = None

    # ==================== ดึงข้อมูลข้าม Sheet ====================
    def load_data_from_sheet(self):
        try:
            if not self.spreadsheet: return
            
            # 1. แอบไปอ่าน Sheet Bookings เพื่อหา "เวลาจองล่าสุด" ของผู้ใช้แต่ละคน
            bookings_sheet = self.spreadsheet.worksheet("Bookings")
            b_values = bookings_sheet.get_all_values()
            last_bookings = {} 
            
            if len(b_values) > 1:
                b_headers = b_values[0]
                for row in b_values[1:]:
                    b_dict = dict(zip(b_headers, row))
                    u_name = b_dict.get('Name', '').strip()
                    timestamp_str = b_dict.get('Timestamp', '').strip()
                    
                    if u_name and timestamp_str:
                        try:
                            # แปลง Timestamp จาก Sheet Bookings
                            ts = datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S")
                            if u_name not in last_bookings or ts > last_bookings[u_name]:
                                last_bookings[u_name] = ts
                        except:
                            pass 

            # 2. โหลดข้อมูล Users
            users_sheet = self.spreadsheet.worksheet("Users")
            all_values = users_sheet.get_all_values()
            self.users_cache = []
            
            if len(all_values) > 1:
                headers = all_values[0]
                for i, row in enumerate(all_values[1:], start=2):
                    row_dict = {headers[j]: (row[j] if j < len(row) else "") for j in range(len(headers))}
                    row_dict['_row_num'] = i
                    
                    u_name = row_dict.get('Name', '').strip()
                    row_dict['_last_booking'] = last_bookings.get(u_name, datetime.min)
                    
                    self.users_cache.append(row_dict)
        except Exception as e:
            print(f"Error loading users: {e}")

    # ==================== กล่องเพิ่ม/แก้ไข ผู้ใช้งาน ====================
    def show_user_form(self, user_data=None, row_num=None):
        self.close_overlay()
        
        self.current_overlay = ctk.CTkFrame(self, width=450, height=520, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
        self.current_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.current_overlay.pack_propagate(False)

        is_edit = user_data is not None
        title_text = "แก้ไขข้อมูลผู้ใช้" if is_edit else "เพิ่มผู้ใช้ใหม่"

        head_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent", corner_radius=0)
        head_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(head_frame, text=title_text, font=("Arial", 18, "bold"), text_color="#202124").pack(side="left", padx=20, pady=10)
        ctk.CTkButton(head_frame, text="✖", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", command=self.close_overlay).pack(side="right", padx=10)

        form_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(form_frame, text="รหัสผู้ใช้ / รหัสนักศึกษา (UserID):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w")
        id_entry = ctk.CTkEntry(form_frame, height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        id_entry.pack(fill="x", pady=(0, 10))
        if is_edit: id_entry.insert(0, user_data.get('UserID', ''))

        ctk.CTkLabel(form_frame, text="ชื่อ-นามสกุล (Name):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w")
        name_entry = ctk.CTkEntry(form_frame, height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        name_entry.pack(fill="x", pady=(0, 10))
        if is_edit: name_entry.insert(0, user_data.get('Name', ''))

        ctk.CTkLabel(form_frame, text="ชั้นปี/ตำแหน่ง (Year):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w")
        year_entry = ctk.CTkEntry(form_frame, height=35, fg_color="#F8F9FA", border_color="#DADCE0", placeholder_text="เช่น ป.โท มหิดล, ปี 4")
        year_entry.pack(fill="x", pady=(0, 10))
        if is_edit: year_entry.insert(0, user_data.get('Year', ''))

        ctk.CTkLabel(form_frame, text="อาจารย์ที่ปรึกษา (Advisor):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w")
        advisor_entry = ctk.CTkEntry(form_frame, height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        advisor_entry.pack(fill="x", pady=(0, 15))
        if is_edit: advisor_entry.insert(0, user_data.get('Advisor', ''))

        def save_user():
            u_id = id_entry.get().strip()
            u_name = name_entry.get().strip()
            u_year = year_entry.get().strip()
            u_advisor = advisor_entry.get().strip()

            if not u_id or not u_name:
                messagebox.showwarning("แจ้งเตือน", "กรุณาระบุ รหัสผู้ใช้ และ ชื่อ-นามสกุล ให้ครบถ้วน")
                return

            try:
                sheet = self.spreadsheet.worksheet("Users")
                headers = sheet.row_values(1)
                
                new_row = [""] * len(headers)
                if 'UserID' in headers: new_row[headers.index('UserID')] = u_id
                if 'Name' in headers: new_row[headers.index('Name')] = u_name
                if 'Year' in headers: new_row[headers.index('Year')] = u_year
                if 'Advisor' in headers: new_row[headers.index('Advisor')] = u_advisor
                
                if not is_edit and 'RegisDate' in headers:
                    new_row[headers.index('RegisDate')] = datetime.now().strftime("%d/%m/%Y %H:%M")

                if is_edit:
                    old_status = user_data.get('Status', 'Active')
                    old_regis = user_data.get('RegisDate', '')
                    if 'Status' in headers: new_row[headers.index('Status')] = old_status
                    if 'RegisDate' in headers: new_row[headers.index('RegisDate')] = old_regis
                    for col_idx, val in enumerate(new_row, start=1):
                        sheet.update_cell(row_num, col_idx, val)
                else:
                    if 'Status' in headers: new_row[headers.index('Status')] = "Active"
                    sheet.append_row(new_row)

                self.refresh_page()
            except Exception as e:
                messagebox.showerror("Error", f"บันทึกข้อมูลไม่สำเร็จ: {e}")

        ctk.CTkButton(self.current_overlay, text="💾 บันทึกข้อมูล", fg_color="#1A73E8", hover_color="#174EA6", height=45, corner_radius=6, font=("Arial", 14, "bold"), command=save_user).pack(fill="x", padx=20, pady=(10, 20))

    def toggle_user_status(self, current_status, row_num):
        new_status = "Banned" if current_status.lower() == "active" else "Active"
        msg = f"คุณต้องการเปลี่ยนสถานะผู้ใช้นี้เป็น '{new_status}' ใช่หรือไม่?"
        if messagebox.askyesno("ยืนยัน", msg):
            try:
                sheet = self.spreadsheet.worksheet("Users")
                headers = sheet.row_values(1)
                if 'Status' in headers:
                    sheet.update_cell(row_num, headers.index('Status') + 1, new_status)
                self.refresh_page()
            except Exception as e:
                messagebox.showerror("Error", f"เปลี่ยนสถานะไม่สำเร็จ: {e}")

    def delete_user(self, user_name, row_num):
        if messagebox.askyesno("ยืนยันการลบ", f"ลบข้อมูลผู้ใช้ '{user_name}' ถาวรใช่หรือไม่?"):
            try:
                self.spreadsheet.worksheet("Users").delete_rows(row_num)
                self.refresh_page()
            except Exception as e:
                messagebox.showerror("Error", f"ลบข้อมูลไม่สำเร็จ: {e}")

    # ==================== วาดหน้าจอ UI ====================
    def render_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.load_data_from_sheet()

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header_frame, text="จัดการสิทธิ์ผู้ใช้งาน", font=("Arial", 26, "bold"), text_color="#202124").pack(side="left")

        tab_frame = ctk.CTkFrame(header_frame, fg_color="#E8EAED", corner_radius=8)
        tab_frame.pack(side="left", padx=20)
        
        def switch_tab(tab_name):
            self.current_tab = tab_name
            btn_users.configure(fg_color="#FFFFFF" if tab_name == "Users" else "transparent", text_color="#1A73E8" if tab_name == "Users" else "#5F6368")
            btn_admins.configure(fg_color="#FFFFFF" if tab_name == "Admins" else "transparent", text_color="#1A73E8" if tab_name == "Admins" else "#5F6368")
            self.render_list()

        btn_users = ctk.CTkButton(tab_frame, text="👥 ผู้ใช้ทั่วไป", font=("Arial", 14, "bold"), fg_color="#FFFFFF", text_color="#1A73E8", hover_color="#F1F3F4", corner_radius=6, height=35, command=lambda: switch_tab("Users"))
        btn_users.pack(side="left", padx=2, pady=2)
        
        btn_admins = ctk.CTkButton(tab_frame, text="🛡️ แอดมิน (OAuth)", font=("Arial", 14, "bold"), fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", corner_radius=6, height=35, command=lambda: switch_tab("Admins"))
        btn_admins.pack(side="left", padx=2, pady=2)

        btn_add = ctk.CTkButton(header_frame, text="+ เพิ่มผู้ใช้ใหม่", font=("Arial", 14, "bold"), fg_color="#1E8E3E", hover_color="#137333", height=40, corner_radius=6, command=lambda: self.show_user_form())
        btn_add.pack(side="right", padx=5)

        control_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#DADCE0", height=60)
        control_frame.pack(fill="x", pady=(0, 15))
        control_frame.pack_propagate(False)

        ctk.CTkLabel(control_frame, text="🔍", font=("Arial", 16)).pack(side="left", padx=(15, 5))
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.render_list())
        
        search_entry = ctk.CTkEntry(control_frame, textvariable=self.search_var, placeholder_text="ค้นหาชื่อ, รหัสนักศึกษา...", width=300, fg_color="#F8F9FA", border_width=0)
        search_entry.pack(side="left", pady=10)

        ctk.CTkLabel(control_frame, text="เรียงตาม:", font=("Arial", 13), text_color="#5F6368").pack(side="right", padx=(5, 15))
        
        self.sort_var = ctk.StringVar(value="ตัวอักษร (A-Z)")
        sort_combo = ctk.CTkComboBox(control_frame, variable=self.sort_var, 
                                     values=["ตัวอักษร (A-Z)", "เวลาลงทะเบียน (ใหม่สุด)", "จองรายการล่าสุด"], 
                                     width=180, fg_color="#F8F9FA", border_color="#DADCE0", command=lambda e: self.render_list())
        sort_combo.pack(side="right", padx=5)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.list_frame.pack(fill="both", expand=True)
        
        self.render_list()

    # ==================== จัดเรียงและวาดการ์ดรายชื่อ ====================
    def render_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if self.current_tab == "Admins":
            self.render_admin_view()
            return

        query = self.search_var.get().lower()
        filtered_users = []
        for u in self.users_cache:
            if query in u.get('Name', '').lower() or query in u.get('UserID', '').lower():
                filtered_users.append(u)

        sort_mode = self.sort_var.get()
        if sort_mode == "ตัวอักษร (A-Z)":
            filtered_users.sort(key=lambda x: x.get('Name', ''))
            
        elif sort_mode == "เวลาลงทะเบียน (ใหม่สุด)":
            # ฟังก์ชันช่วยแปลง Text ให้เป็นตัวแปร Datetime ก่อนเอาไปเรียงลำดับ
            def parse_regis_date(user):
                d_str = user.get('RegisDate', '').strip()
                if not d_str: return datetime.min
                try:
                    # แปลงรูปแบบ 09/01/2026 15:27 ให้เป็น Datetime ของจริง
                    return datetime.strptime(d_str, "%d/%m/%Y %H:%M")
                except ValueError:
                    try:
                        # เผื่ออนาคตแอดมินพิมพ์เองแล้วลืมใส่เวลา
                        return datetime.strptime(d_str, "%d/%m/%Y")
                    except ValueError:
                        # ถ้าพิมพ์มั่วๆ มา ให้เด้งไปอยู่ล่างสุด
                        return datetime.min
            
            filtered_users.sort(key=parse_regis_date, reverse=True)
            
        elif sort_mode == "จองรายการล่าสุด":
            filtered_users.sort(key=lambda x: x.get('_last_booking', datetime.min), reverse=True)

        if not filtered_users:
            ctk.CTkLabel(self.list_frame, text="ไม่พบข้อมูลผู้ใช้งาน", font=("Arial", 16), text_color="#A0A0A0").pack(pady=50)
            return

        for user in filtered_users:
            u_id = user.get('UserID', '-')
            u_name = user.get('Name', 'Unknown')
            u_year = user.get('Year', '-')
            u_advisor = user.get('Advisor', '-')
            u_regis = user.get('RegisDate', '-')
            u_status = user.get('Status', 'Active')
            
            last_bk = user.get('_last_booking', datetime.min)
            str_last_bk = last_bk.strftime("%d/%m/%Y %H:%M") if last_bk != datetime.min else "ไม่เคยทำรายการ"
            
            r_num = user.get('_row_num')

            card = ctk.CTkFrame(self.list_frame, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#DADCE0")
            card.pack(fill="x", pady=5, padx=2)
            card.grid_columnconfigure(0, weight=1) 
            card.grid_columnconfigure(1, weight=0) 

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
            
            ctk.CTkLabel(info_frame, text=f"👤 {u_name}  (ID: {u_id})", font=("Arial", 16, "bold"), text_color="#1A73E8", anchor="w").pack(fill="x")
            
            sub_info = f"🎓 ชั้นปี: {u_year}   |   👨‍🏫 ที่ปรึกษา: {u_advisor}"
            sub_info += f"   |   📅 ลงทะเบียน: {u_regis}"
            sub_info += f"   |   ⏱ จองล่าสุด: {str_last_bk}" 
            
            ctk.CTkLabel(info_frame, text=sub_info, font=("Arial", 13), text_color="#5F6368", anchor="w", justify="left").pack(fill="x", pady=(2, 0))

            action_frame = ctk.CTkFrame(card, fg_color="transparent")
            action_frame.grid(row=0, column=1, sticky="e", padx=20, pady=15)

            is_active = u_status.lower() == "active"
            badge_color = "#E6F4EA" if is_active else "#FCE8E6"
            text_color = "#137333" if is_active else "#C5221F"
            status_text = "🟢 ปกติ (Active)" if is_active else "🔴 ระงับสิทธิ์"
            
            badge = ctk.CTkFrame(action_frame, fg_color=badge_color, corner_radius=15, height=32, width=130)
            badge.pack(side="left", padx=10)
            badge.pack_propagate(False)
            ctk.CTkLabel(badge, text=status_text, font=("Arial", 12, "bold"), text_color=text_color).pack(expand=True, fill="both")

            toggle_btn_text = "ระงับสิทธิ์" if is_active else "ปลดระงับ"
            toggle_btn_color = "#FCE8E6" if is_active else "#E6F4EA"
            toggle_txt_color = "#D93025" if is_active else "#137333"
            
            ctk.CTkButton(action_frame, text=toggle_btn_text, font=("Arial", 12, "bold"), width=80, height=32,
                          fg_color=toggle_btn_color, text_color=toggle_txt_color, hover_color="#E8EAED",
                          command=lambda s=u_status, r=r_num: self.toggle_user_status(s, r)).pack(side="left", padx=3)

            ctk.CTkButton(action_frame, text="✏️ แก้ไข", width=60, height=32, fg_color="#F8F9FA", text_color="#1A73E8", border_width=1, border_color="#DADCE0", hover_color="#E8F0FE",
                          command=lambda u=user, r=r_num: self.show_user_form(u, r)).pack(side="left", padx=3)
            
            ctk.CTkButton(action_frame, text="🗑️", width=35, height=32, fg_color="#F8F9FA", text_color="#D93025", border_width=1, border_color="#DADCE0", hover_color="#FCE8E6",
                          command=lambda n=u_name, r=r_num: self.delete_user(n, r)).pack(side="left", padx=3)

    # ==================== วาดหน้าจอสำหรับแท็บ Admin ====================
    def render_admin_view(self):
        admin_card = ctk.CTkFrame(self.list_frame, fg_color="#F0F4F8", corner_radius=12, border_width=1, border_color="#1A73E8")
        admin_card.pack(fill="x", pady=20, padx=20)
        
        ctk.CTkLabel(admin_card, text="🛡️ การจัดการสิทธิ์ผู้ดูแลระบบ (Admin Access)", font=("Arial", 18, "bold"), text_color="#1A73E8").pack(pady=(20, 5))
        ctk.CTkLabel(admin_card, text="เพิ่มบัญชี Google (Gmail) ที่จะได้รับอนุญาตให้ล็อกอินเข้าสู่โปรแกรมนี้ได้", font=("Arial", 14), text_color="#5F6368").pack(pady=(0, 20))
        
        input_frame = ctk.CTkFrame(admin_card, fg_color="transparent")
        input_frame.pack(pady=(0, 20))
        
        ctk.CTkEntry(input_frame, placeholder_text="กรอก Email ของแอดมินใหม่...", width=300, height=40).pack(side="left", padx=10)
        ctk.CTkButton(input_frame, text="เพิ่มสิทธิ์ Admin", fg_color="#1A73E8", hover_color="#174EA6", height=40, font=("Arial", 13, "bold")).pack(side="left")

        ctk.CTkLabel(self.list_frame, text="รายชื่อผู้ดูแลระบบปัจจุบัน:", font=("Arial", 14, "bold"), text_color="#202124", anchor="w").pack(fill="x", padx=25, pady=10)
        
        mock_admin = ctk.CTkFrame(self.list_frame, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#DADCE0")
        mock_admin.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(mock_admin, text="📧 admin.master@mahidol.edu", font=("Arial", 14, "bold"), text_color="#3C4043").pack(side="left", padx=15, pady=15)
        ctk.CTkLabel(mock_admin, text="👑 Master Admin", font=("Arial", 12), text_color="#1E8E3E").pack(side="left", padx=10)