import customtkinter as ctk
from tkinter import messagebox, filedialog
import requests
from PIL import Image
from io import BytesIO
import csv
from datetime import datetime
import os 

class MachinesPage(ctk.CTkFrame):
    def __init__(self, parent, spreadsheet):
        super().__init__(parent, fg_color="#F8F9FA")
        
        self.spreadsheet = spreadsheet
        self.current_overlay = None
        # โครงสร้าง Schema ล่าสุด: Name, Floor, Slots, Color, Image, Status, WarnDays, WarnTime, WarnMsg, WarnCol
        self.headers = ["Name", "Floor", "Slots", "Color", "Image", "Status", "WarnDays", "WarnTime", "WarnMsg", "WarnCol"]
        self.time_slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
        
        self.IMAGE_API_KEY = os.getenv("IMGBB_API_KEY") 
        self.IMAGE_API_URL = "https://api.imgbb.com/1/upload"
        self.image_cache = {}

        self.render_ui()

    def refresh_page(self):
        self.close_overlay()
        for widget in self.winfo_children():
            widget.destroy()
        self.render_ui()

    def close_overlay(self):
        if self.current_overlay:
            self.current_overlay.destroy()
            self.current_overlay = None

    def get_image_from_url(self, url, size=(80, 80)):
        if not url or not url.startswith("http"): return None
        if url in self.image_cache: return self.image_cache[url]
        try:
            response = requests.get(url, timeout=3)
            img = Image.open(BytesIO(response.content))
            ctk_img = ctk.CTkImage(light_image=img, size=size)
            self.image_cache[url] = ctk_img
            return ctk_img
        except Exception:
            return None

    def show_block_time_form(self, machine_data):
        self.close_overlay()
        machine_name = machine_data.get('Name', 'Unknown')
        
        self.current_overlay = ctk.CTkFrame(self, width=600, height=680, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
        self.current_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.current_overlay.pack_propagate(False)

        head_frame = ctk.CTkFrame(self.current_overlay, fg_color="#FCE8E6", corner_radius=0)
        head_frame.pack(fill="x")
        ctk.CTkLabel(head_frame, text=f"🚫 จัดการบล็อกเวลา: {machine_name}", font=("Arial", 16, "bold"), text_color="#C5221F").pack(side="left", padx=20, pady=12)
        ctk.CTkButton(head_frame, text="✖", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#FAD2CF", command=self.close_overlay).pack(side="right", padx=10)

        form_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=10)
        
        row1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="วันที่ปิดจอง (YYYY-MM-DD):", font=("Arial", 12, "bold"), text_color="#5F6368", width=160, anchor="w").pack(side="left")
        date_entry = ctk.CTkEntry(row1, height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        date_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ctk.CTkLabel(form_frame, text="ติ๊กเลือกช่วงเวลาที่ต้องการบล็อก (รวมเป็น 1 รายการ):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w", pady=(10, 5))
        
        cb_frame = ctk.CTkFrame(form_frame, fg_color="#F8F9FA", corner_radius=8, border_width=1, border_color="#DADCE0")
        cb_frame.pack(fill="x", pady=5)
        
        m_slots = machine_data.get('Slots', '').strip()
        if m_slots: intervals = [s.strip() for s in m_slots.split(',') if s.strip()]
        else: intervals = ["09:00-10:00", "10:00-11:00", "11:00-12:00", "13:00-14:00", "14:00-15:00", "15:00-16:00"]

        self.checkbox_vars = {}
        for i, interval in enumerate(intervals):
            var = ctk.StringVar(value="")
            self.checkbox_vars[interval] = var
            cb = ctk.CTkCheckBox(cb_frame, text=interval, variable=var, onvalue=interval, offvalue="",
                                 font=("Arial", 13), fg_color="#D93025", hover_color="#A50E0E")
            cb.grid(row=i//3, column=i%3, padx=20, pady=10, sticky="w") 

        row3 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row3.pack(fill="x", pady=(10, 5))
        ctk.CTkLabel(row3, text="เหตุผล (Message):", font=("Arial", 12, "bold"), text_color="#5F6368", width=120, anchor="w").pack(side="left")
        msg_entry = ctk.CTkEntry(row3, height=35, fg_color="#F8F9FA", border_color="#DADCE0", placeholder_text="เช่น มีเรียน / Class")
        msg_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))

        def save_blocked_slots():
            b_date = date_entry.get().strip()
            b_msg = msg_entry.get().strip()
            selected_slots = [var.get() for var in self.checkbox_vars.values() if var.get() != ""]
            
            if not b_date: messagebox.showwarning("แจ้งเตือน", "กรุณาระบุวันที่"); return
            if not selected_slots: messagebox.showwarning("แจ้งเตือน", "กรุณาติ๊กเลือกเวลาอย่างน้อย 1 ช่วง"); return
            if not b_msg: b_msg = "ปิดระบบ/แอดมินบล็อก"

            try:
                sheet = self.spreadsheet.worksheet("BlockedSlots")
                joined_slots = ", ".join(selected_slots)
                sheet.append_row([machine_name, b_date, joined_slots, b_msg, "Active"])
                messagebox.showinfo("สำเร็จ", "บันทึกข้อมูลการบล็อกเวลาเรียบร้อยแล้ว!")
                self.show_block_time_form(machine_data) 
            except Exception as e:
                messagebox.showerror("Error", f"บันทึกไม่สำเร็จ: {e}")

        ctk.CTkButton(form_frame, text="💾 บันทึกการบล็อกเวลา", fg_color="#D93025", hover_color="#A50E0E", height=40, font=("Arial", 13, "bold"), command=save_blocked_slots).pack(anchor="e", pady=(15, 0))

        ctk.CTkFrame(self.current_overlay, height=2, fg_color="#E8EAED").pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(self.current_overlay, text="รายการบล็อกเวลาปัจจุบัน", font=("Arial", 14, "bold"), text_color="#202124").pack(anchor="w", padx=20, pady=(0, 5))
        
        list_frame = ctk.CTkScrollableFrame(self.current_overlay, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        try:
            sheet = self.spreadsheet.worksheet("BlockedSlots")
            all_values = sheet.get_all_values()
            
            if len(all_values) > 1:
                headers = all_values[0]
                has_data = False
                for i, row in enumerate(all_values[1:], start=2):
                    row_dict = dict(zip(headers, row))
                    if row_dict.get('Machine') == machine_name:
                        has_data = True
                        card = ctk.CTkFrame(list_frame, fg_color="#FCE8E6", corner_radius=8)
                        card.pack(fill="x", pady=4)
                        
                        info_lbl = f"📅 {row_dict.get('Date', '')}\n⏱ {row_dict.get('TimeSlots', '')}\n📝 {row_dict.get('Message', '')}"
                        ctk.CTkLabel(card, text=info_lbl, font=("Arial", 12), text_color="#C5221F", justify="left", wraplength=350).pack(side="left", padx=15, pady=10)
                        
                        def delete_block(row_num=i):
                            if messagebox.askyesno("ยืนยัน", "ต้องการปลดบล็อกช่วงเวลานี้ (ทั้งหมด) ใช่หรือไม่?"):
                                try:
                                    self.spreadsheet.worksheet("BlockedSlots").delete_rows(row_num)
                                    self.show_block_time_form(machine_data)
                                except Exception as e: messagebox.showerror("Error", f"ลบไม่สำเร็จ: {e}")

                        ctk.CTkButton(card, text="ปลดบล็อก", width=70, fg_color="#FFFFFF", text_color="#D93025", hover_color="#FAD2CF", command=delete_block).pack(side="right", padx=15)
                
                if not has_data: ctk.CTkLabel(list_frame, text="ไม่มีรายการบล็อกเวลาสำหรับเครื่องมือนี้", text_color="#A0A0A0").pack(pady=30)
            else: ctk.CTkLabel(list_frame, text="ไม่มีรายการบล็อกเวลาสำหรับเครื่องมือนี้", text_color="#A0A0A0").pack(pady=30)
        except Exception as e: ctk.CTkLabel(list_frame, text=f"⚠️ โหลดข้อมูลไม่สำเร็จ\n{e}", text_color="#D93025").pack(pady=30)

    def show_machine_log(self, machine_name):
        self.close_overlay()
        self.current_overlay = ctk.CTkFrame(self, width=600, height=600, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
        self.current_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.current_overlay.pack_propagate(False)

        head_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent", corner_radius=0)
        head_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(head_frame, text=f"📜 ประวัติการใช้งาน: {machine_name}", font=("Arial", 16, "bold"), text_color="#202124").pack(side="left", padx=20, pady=10)
        ctk.CTkButton(head_frame, text="✖", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", command=self.close_overlay).pack(side="right", padx=10)

        log_frame = ctk.CTkScrollableFrame(self.current_overlay, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        loading_lbl = ctk.CTkLabel(log_frame, text="⏳ กำลังโหลดประวัติการจอง...", font=("Arial", 14), text_color="#A0A0A0")
        loading_lbl.pack(pady=50)
        self.update() 

        try:
            bookings_sheet = self.spreadsheet.worksheet("Bookings")
            all_values = bookings_sheet.get_all_values()
            loading_lbl.destroy() 

            if len(all_values) <= 1:
                ctk.CTkLabel(log_frame, text="ยังไม่มีประวัติการจองใดๆ ในระบบ", font=("Arial", 14), text_color="#A0A0A0").pack(pady=50)
                return
            
            headers = all_values[0]
            logs = []
            for row in all_values[1:]:
                row_dict = dict(zip(headers, row))
                if row_dict.get('Machine') == machine_name: logs.append(row_dict)
            
            if not logs:
                ctk.CTkLabel(log_frame, text="ไม่มีประวัติการจองสำหรับเครื่องมือนี้", font=("Arial", 14), text_color="#A0A0A0").pack(pady=50)
                return

            logs.sort(key=lambda x: (x.get('Date', ''), x.get('Time', '')), reverse=True)

            def export_csv():
                filepath = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"Log_{machine_name}.csv", title="บันทึกไฟล์ประวัติการใช้งาน", filetypes=[("CSV Files", "*.csv")])
                if not filepath: return
                try:
                    with open(filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(["ทำรายการเมื่อ (Timestamp)", "วันที่จอง (Date)", "เวลาที่จอง (Time)", "ชื่อผู้จอง (Name)", "ชั้นปี/ตำแหน่ง", "อาจารย์ที่ปรึกษา"])
                        for log_item in logs:
                            writer.writerow([log_item.get('Timestamp', ''), log_item.get('Date', ''), log_item.get('Time', ''), log_item.get('Name', ''), log_item.get('Year/Position', ''), log_item.get('Advisor', '')])
                    messagebox.showinfo("สำเร็จ", "ส่งออกไฟล์ CSV เรียบร้อยแล้ว!")
                except Exception as err: messagebox.showerror("Error", f"ไม่สามารถสร้างไฟล์ได้: {err}")

            ctk.CTkButton(head_frame, text="📥 Export CSV", font=("Arial", 12, "bold"), fg_color="#1E8E3E", hover_color="#137333", height=30, command=export_csv).pack(side="right", padx=10)

            for log in logs:
                card = ctk.CTkFrame(log_frame, fg_color="#F8F9FA", corner_radius=8, border_width=1, border_color="#E8EAED")
                card.pack(fill="x", pady=5)
                
                timestamp_str = log.get('Timestamp', '-')
                date_str = log.get('Date', '-')
                time_str = log.get('Time', '-')
                name_str = log.get('Name', 'ไม่ระบุชื่อ')
                role_str = log.get('Year/Position', '')
                advisor_str = log.get('Advisor', '')
                
                top_frame = ctk.CTkFrame(card, fg_color="transparent")
                top_frame.pack(fill="x", padx=15, pady=(10, 2))
                ctk.CTkLabel(top_frame, text=f"📅 จองใช้วันที่: {date_str}  ⏱ เวลา: {time_str}", font=("Arial", 13, "bold"), text_color="#1A73E8").pack(side="left")
                ctk.CTkLabel(top_frame, text=f"ทำรายการเมื่อ: {timestamp_str}", font=("Arial", 11), text_color="#A0A0A0").pack(side="right")
                
                bot_frame = ctk.CTkFrame(card, fg_color="transparent")
                bot_frame.pack(fill="x", padx=15, pady=(0, 10))
                
                user_info = f"👤 {name_str}"
                if role_str: user_info += f"  🎓 {role_str}"
                if advisor_str: user_info += f"  👨‍🏫 อ.ที่ปรึกษา: {advisor_str}"
                ctk.CTkLabel(bot_frame, text=user_info, font=("Arial", 13), text_color="#5F6368").pack(side="left")

        except Exception as e:
            if loading_lbl.winfo_exists(): loading_lbl.destroy()
            ctk.CTkLabel(log_frame, text=f"⚠️ ดึงข้อมูลไม่สำเร็จ:\n{e}", text_color="#D93025").pack(pady=50)

    # ==================== กล่องแก้ไขเครื่องมือ (อัปเดตฟิลด์แจ้งเตือน) ====================
    def show_machine_form(self, machine_data=None, row_num=None):
        self.close_overlay()
        # เปลี่ยนใช้ Frame ภายนอกขนาดคงที่ และภายในเป็น ScrollableFrame
        self.current_overlay = ctk.CTkFrame(self, width=550, height=700, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
        self.current_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.current_overlay.pack_propagate(False)

        is_edit = machine_data is not None
        title_text = "แก้ไขข้อมูลเครื่องมือ" if is_edit else "เพิ่มเครื่องมือใหม่"

        head_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent", corner_radius=0)
        head_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(head_frame, text=title_text, font=("Arial", 18, "bold"), text_color="#202124").pack(side="left", padx=20, pady=10)
        ctk.CTkButton(head_frame, text="✖", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", command=self.close_overlay).pack(side="right", padx=10)

        # ใช้งาน CTkScrollableFrame เพื่อรองรับกล่องข้อมูลที่ยาวขึ้น
        form_frame = ctk.CTkScrollableFrame(self.current_overlay, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # -- ข้อมูลพื้นฐาน --
        ctk.CTkLabel(form_frame, text="ชื่อเครื่องมือ (Name):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w", padx=10)
        name_entry = ctk.CTkEntry(form_frame, height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        name_entry.pack(fill="x", padx=10, pady=(0, 10))
        if is_edit: name_entry.insert(0, machine_data.get('Name', ''))

        ctk.CTkLabel(form_frame, text="สถานที่/ชั้น (Floor):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w", padx=10)
        floor_entry = ctk.CTkEntry(form_frame, height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        floor_entry.pack(fill="x", padx=10, pady=(0, 10))
        if is_edit: floor_entry.insert(0, machine_data.get('Floor', ''))

        ctk.CTkLabel(form_frame, text="รูปแบบเวลาจอง (Slots) คั่นด้วย (,):", font=("Arial", 12, "bold"), text_color="#1A73E8").pack(anchor="w", padx=10)
        slots_entry = ctk.CTkEntry(form_frame, height=35, fg_color="#F8F9FA", border_color="#1A73E8", placeholder_text="เช่น 09:00-12:00, 13:00-16:00")
        slots_entry.pack(fill="x", padx=10, pady=(0, 10))
        if is_edit: 
            m_slots_val = machine_data.get('Slots', '')
            if not m_slots_val: m_slots_val = "09:00-10:00, 10:00-11:00, 11:00-12:00, 13:00-14:00, 14:00-15:00, 15:00-16:00"
            slots_entry.insert(0, m_slots_val)
        else: 
            slots_entry.insert(0, "09:00-10:00, 10:00-11:00, 11:00-12:00, 13:00-14:00, 14:00-15:00, 15:00-16:00")

        ctk.CTkLabel(form_frame, text="สถานะ (Status):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w", padx=10)
        status_combo = ctk.CTkComboBox(form_frame, values=["Active", "Maintenance", "Closed"], height=35, fg_color="#FFFFFF", border_color="#DADCE0")
        status_combo.pack(fill="x", padx=10, pady=(0, 15))
        if is_edit: status_combo.set(machine_data.get('Status', 'Active'))
        else: status_combo.set("Active")

        # -- โซนตั้งค่าการแจ้งเตือน (Warn Settings) --
        warn_zone = ctk.CTkFrame(form_frame, fg_color="#FFF8E1", corner_radius=8, border_width=1, border_color="#FDE68A")
        warn_zone.pack(fill="x", padx=10, pady=(0, 15), ipady=10)
        
        ctk.CTkLabel(warn_zone, text="⚠️ ตั้งค่าการแจ้งเตือนเฉพาะวัน/เวลา (Warning Settings)", font=("Arial", 13, "bold"), text_color="#D97706").pack(anchor="w", padx=15, pady=(10, 5))
        
        # 1. เลือกวัน (WarnDays) 0=Sun, 1=Mon ... 6=Sat
        ctk.CTkLabel(warn_zone, text="แสดงคำเตือนในวัน:", font=("Arial", 12), text_color="#5F6368").pack(anchor="w", padx=15)
        days_frame = ctk.CTkFrame(warn_zone, fg_color="transparent")
        days_frame.pack(fill="x", padx=15, pady=5)
        
        day_names = [("อา", "0"), ("จ", "1"), ("อ", "2"), ("พ", "3"), ("พฤ", "4"), ("ศ", "5"), ("ส", "6")]
        self.warn_day_vars = {}
        
        existing_days = []
        if is_edit and machine_data.get('WarnDays'):
            existing_days = [d.strip() for d in str(machine_data.get('WarnDays')).split(',')]

        for d_name, d_val in day_names:
            var = ctk.StringVar(value=d_val if d_val in existing_days else "")
            self.warn_day_vars[d_val] = var
            cb = ctk.CTkCheckBox(days_frame, text=d_name, variable=var, onvalue=d_val, offvalue="",
                                 width=45, checkbox_width=18, checkbox_height=18, text_color="#5F6368", fg_color="#F59E0B")
            cb.pack(side="left", padx=5)

        # 2. เลือกเวลา (WarnTime)
        time_row = ctk.CTkFrame(warn_zone, fg_color="transparent")
        time_row.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(time_row, text="ในรอบเวลา (WarnTime):", font=("Arial", 12), text_color="#5F6368").pack(side="left")
        warn_time_combo = ctk.CTkComboBox(time_row, values=["ทุกรอบเวลา (All)", *self.time_slots, "09:00-12:00", "13:00-16:00"], width=150, fg_color="#FFFFFF", border_color="#DADCE0")
        warn_time_combo.pack(side="left", padx=10)
        
        if is_edit and machine_data.get('WarnTime'):
            warn_time_combo.set(machine_data.get('WarnTime'))
        else:
            warn_time_combo.set("ทุกรอบเวลา (All)")

        # 3. สีข้อความ (WarnCol)
        ctk.CTkLabel(time_row, text="สีแจ้งเตือน:", font=("Arial", 12), text_color="#5F6368").pack(side="left", padx=(10, 0))
        color_choices = {"สีแดง (Red)": "#FF5555", "สีส้ม (Orange)": "#F59E0B", "สีน้ำเงิน (Blue)": "#1A73E8"}
        warn_col_combo = ctk.CTkComboBox(time_row, values=list(color_choices.keys()), width=120, fg_color="#FFFFFF", border_color="#DADCE0")
        warn_col_combo.pack(side="left", padx=10)
        
        if is_edit and machine_data.get('WarnCol'):
            saved_col = machine_data.get('WarnCol')
            found = False
            for k, v in color_choices.items():
                if v == saved_col:
                    warn_col_combo.set(k)
                    found = True
                    break
            if not found: warn_col_combo.set("สีแดง (Red)")
        else:
            warn_col_combo.set("สีแดง (Red)")

        # 4. ข้อความแจ้งเตือน (WarnMsg)
        ctk.CTkLabel(warn_zone, text="ข้อความแจ้งเตือน (WarnMsg):", font=("Arial", 12), text_color="#5F6368").pack(anchor="w", padx=15)
        warn_entry = ctk.CTkEntry(warn_zone, height=35, fg_color="#FFFFFF", border_color="#DADCE0", placeholder_text="เช่น งดใช้เครื่องมือช่วงบ่าย")
        warn_entry.pack(fill="x", padx=15, pady=(0, 5))
        if is_edit: warn_entry.insert(0, machine_data.get('WarnMsg', ''))

        # -- รูปภาพ --
        ctk.CTkLabel(form_frame, text="ลิงก์รูปภาพ (Image URL):", font=("Arial", 12, "bold"), text_color="#5F6368").pack(anchor="w", padx=10)
        img_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        img_frame.pack(fill="x", padx=10, pady=(0, 15))
        img_entry = ctk.CTkEntry(img_frame, height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        img_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        if is_edit: img_entry.insert(0, machine_data.get('Image', ''))

        def auto_upload_image():
            filepath = filedialog.askopenfilename(title="เลือกรูปเครื่องมือ", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
            if not filepath: return
            if not self.IMAGE_API_KEY or self.IMAGE_API_KEY == "your_imgbb_api_key_here":
                messagebox.showerror("Error", "ไม่พบ API Key สำหรับอัปโหลดรูปภาพ (โปรดตั้งค่าในไฟล์ .env ก่อน)")
                return
                
            btn_upload.configure(text="⏳ กำลังอัปโหลด...", state="disabled")
            self.update() 
            try:
                with open(filepath, "rb") as file:
                    payload = {"key": self.IMAGE_API_KEY}
                    files = {"image": file}
                    response = requests.post(self.IMAGE_API_URL, data=payload, files=files)
                    if response.status_code == 200:
                        direct_url = response.json()['data']['url'] 
                        img_entry.delete(0, 'end')
                        img_entry.insert(0, direct_url)
                        messagebox.showinfo("สำเร็จ", "อัปโหลดรูปลงเซิร์ฟเวอร์เรียบร้อยแล้ว!")
                    else: messagebox.showerror("Error", f"อัปโหลดไม่สำเร็จ: {response.text}")
            except Exception as e: messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {e}")
            finally: btn_upload.configure(text="📂 เลือกไฟล์...", state="normal")

        btn_upload = ctk.CTkButton(img_frame, text="📂 เลือกไฟล์...", width=100, height=35, fg_color="#F1F3F4", text_color="#1A73E8", hover_color="#E8EAED", command=auto_upload_image)
        btn_upload.pack(side="right")

        def save_machine():
            m_name = name_entry.get().strip()
            m_slots = slots_entry.get().strip()
            
            if not m_name: messagebox.showwarning("แจ้งเตือน", "กรุณาระบุชื่อเครื่องมือ"); return
            if not m_slots: messagebox.showwarning("แจ้งเตือน", "กรุณาระบุช่วงเวลาการจอง (Slots)"); return
            
            # แปลงค่า Setting เป็น String
            sel_days = [var.get() for var in self.warn_day_vars.values() if var.get() != ""]
            warn_days_str = ",".join(sel_days)
            
            warn_time_str = warn_time_combo.get()
            if warn_time_str == "ทุกรอบเวลา (All)": warn_time_str = ""
            
            warn_col_hex = color_choices.get(warn_col_combo.get(), "#FF5555")

            try:
                sheet = self.spreadsheet.worksheet("Machines")
                headers = sheet.row_values(1)

                if is_edit:
                    row_data = sheet.row_values(row_num)
                    while len(row_data) < len(headers): row_data.append("")
                    
                    if 'Name' in headers: row_data[headers.index('Name')] = m_name
                    if 'Floor' in headers: row_data[headers.index('Floor')] = floor_entry.get().strip()
                    if 'Slots' in headers: row_data[headers.index('Slots')] = m_slots 
                    if 'Status' in headers: row_data[headers.index('Status')] = status_combo.get()
                    if 'WarnMsg' in headers: row_data[headers.index('WarnMsg')] = warn_entry.get().strip()
                    if 'Image' in headers: row_data[headers.index('Image')] = img_entry.get().strip()
                    
                    # ✅ บันทึกค่าแจ้งเตือน
                    if 'WarnDays' in headers: row_data[headers.index('WarnDays')] = warn_days_str
                    if 'WarnTime' in headers: row_data[headers.index('WarnTime')] = warn_time_str
                    if 'WarnCol' in headers: row_data[headers.index('WarnCol')] = warn_col_hex
                    
                    for col_idx, val in enumerate(row_data, start=1): 
                        sheet.update_cell(row_num, col_idx, val)
                else:
                    new_row = [""] * len(headers)
                    if 'Name' in headers: new_row[headers.index('Name')] = m_name
                    if 'Floor' in headers: new_row[headers.index('Floor')] = floor_entry.get().strip()
                    if 'Slots' in headers: new_row[headers.index('Slots')] = m_slots
                    if 'Status' in headers: new_row[headers.index('Status')] = status_combo.get()
                    if 'WarnMsg' in headers: new_row[headers.index('WarnMsg')] = warn_entry.get().strip()
                    if 'Image' in headers: new_row[headers.index('Image')] = img_entry.get().strip()
                    if 'Color' in headers: new_row[headers.index('Color')] = "#3B82F6"
                    
                    # ✅ บันทึกค่าแจ้งเตือน
                    if 'WarnDays' in headers: new_row[headers.index('WarnDays')] = warn_days_str
                    if 'WarnTime' in headers: new_row[headers.index('WarnTime')] = warn_time_str
                    if 'WarnCol' in headers: new_row[headers.index('WarnCol')] = warn_col_hex
                    
                    sheet.append_row(new_row)
                    
                self.refresh_page()
            except Exception as e: messagebox.showerror("Error", f"บันทึกข้อมูลไม่สำเร็จ: {e}")

        # วางปุ่มบันทึกไว้ด้านนอก ScrollableFrame ให้กดง่ายๆ
        ctk.CTkButton(self.current_overlay, text="💾 บันทึกข้อมูลเครื่องมือ", fg_color="#1A73E8", hover_color="#174EA6", height=45, corner_radius=6, font=("Arial", 14, "bold"), command=save_machine).pack(fill="x", padx=20, pady=(10, 20))

    def toggle_machine_status(self, current_status, row_num):
        new_status = "Maintenance" if current_status.lower() == "active" else "Active"
        if messagebox.askyesno("ยืนยัน", f"คุณต้องการเปลี่ยนสถานะเป็น '{new_status}' ใช่หรือไม่?"):
            try:
                sheet = self.spreadsheet.worksheet("Machines")
                sheet.update_cell(row_num, 6, new_status) 
                self.refresh_page()
            except Exception as e: messagebox.showerror("Error", f"เปลี่ยนสถานะไม่สำเร็จ: {e}")

    def delete_machine(self, machine_name, row_num):
        if messagebox.askyesno("ยืนยัน", f"ลบเครื่องมือ '{machine_name}' อย่างถาวรใช่หรือไม่?"):
            try:
                self.spreadsheet.worksheet("Machines").delete_rows(row_num)
                self.refresh_page()
            except Exception as e: messagebox.showerror("Error", f"ลบข้อมูลไม่สำเร็จ: {e}")

    def render_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header_frame, text="จัดการเครื่องมือ (Machines)", font=("Arial", 26, "bold"), text_color="#202124").pack(side="left")
        
        btn_add = ctk.CTkButton(header_frame, text="+ เพิ่มเครื่องมือใหม่", font=("Arial", 14, "bold"), 
                                fg_color="#1E8E3E", hover_color="#137333", height=40, corner_radius=6,
                                command=lambda: self.show_machine_form())
        btn_add.pack(side="right", padx=5)

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True)

        try:
            if self.spreadsheet:
                machines_sheet = self.spreadsheet.worksheet("Machines")
                all_values = machines_sheet.get_all_values()
                machines_data = []
                
                if len(all_values) > 1:
                    headers = all_values[0]
                    for i, row in enumerate(all_values[1:], start=2):
                        row_dict = {headers[j]: (row[j] if j < len(row) else "") for j in range(len(headers))}
                        row_dict['_row_num'] = i
                        machines_data.append(row_dict)
            else:
                machines_data = []

            if not machines_data:
                ctk.CTkLabel(scroll_frame, text="ยังไม่มีข้อมูลเครื่องมือในระบบ", font=("Arial", 16), text_color="#A0A0A0").pack(pady=100)
                return

            for machine in machines_data:
                m_name = machine.get('Name', 'Unknown')
                m_floor = machine.get('Floor', '-')
                m_slots = machine.get('Slots', '') 
                m_status = machine.get('Status', 'Active')
                m_warn = machine.get('WarnMsg', '')
                m_img_url = machine.get('Image', '')
                r_num = machine.get('_row_num')

                card = ctk.CTkFrame(scroll_frame, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#DADCE0")
                card.pack(fill="x", pady=6, padx=5)

                card.grid_columnconfigure(0, weight=1) 
                card.grid_columnconfigure(1, weight=0) 

                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
                
                pic_frame = ctk.CTkFrame(info_frame, width=80, height=80, fg_color="#F1F3F4", corner_radius=8)
                pic_frame.pack(side="left", padx=(0, 15))
                pic_frame.pack_propagate(False)
                
                ctk_img = self.get_image_from_url(m_img_url, size=(80, 80))
                if ctk_img: ctk.CTkLabel(pic_frame, image=ctk_img, text="").pack(expand=True, fill="both")
                else: ctk.CTkLabel(pic_frame, text="📸\nNo Image", font=("Arial", 10), text_color="#A0A0A0").pack(expand=True)
                
                text_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
                text_frame.pack(side="left", fill="both", expand=True)

                ctk.CTkLabel(text_frame, text=f"🛠 {m_name}", font=("Arial", 18, "bold"), text_color="#1A73E8", anchor="w").pack(fill="x", pady=(5,0))
                
                display_slots = m_slots if len(m_slots) <= 50 else m_slots[:47] + "..."
                sub_info = f"📍 สถานที่: {m_floor}   |   ⏱ รอบเวลา: {display_slots}"
                if m_warn: sub_info += f"\n⚠️ คำเตือน: {m_warn}" # ✅ โชว์ว่ามีคำเตือน
                ctk.CTkLabel(text_frame, text=sub_info, font=("Arial", 13), text_color="#5F6368", anchor="w", justify="left").pack(fill="x", pady=(2, 0))

                action_frame = ctk.CTkFrame(card, fg_color="transparent")
                action_frame.grid(row=0, column=1, sticky="e", padx=20, pady=15)

                is_active = m_status.lower() == "active"
                badge_color = "#E6F4EA" if is_active else "#FCE8E6"
                text_color = "#137333" if is_active else "#C5221F"
                status_text = "🟢 พร้อมใช้งาน" if is_active else "🔴 ปิดซ่อมบำรุง"
                
                badge = ctk.CTkFrame(action_frame, fg_color=badge_color, corner_radius=15, height=32, width=120)
                badge.pack(side="left", padx=10)
                badge.pack_propagate(False)
                ctk.CTkLabel(badge, text=status_text, font=("Arial", 12, "bold"), text_color=text_color).pack(expand=True, fill="both")

                toggle_btn_text = "ปิดเครื่องมือ" if is_active else "เปิดใช้งาน"
                ctk.CTkButton(action_frame, text=toggle_btn_text, font=("Arial", 12, "bold"), width=80, height=32,
                              fg_color="#F1F3F4", text_color=("#D93025" if is_active else "#1E8E3E"), hover_color="#E8EAED",
                              command=lambda s=m_status, r=r_num: self.toggle_machine_status(s, r)).pack(side="left", padx=3)

                ctk.CTkButton(action_frame, text="🚫 บล็อกเวลา", width=80, height=32, fg_color="#FCE8E6", text_color="#C5221F", border_width=1, border_color="#FAD2CF", hover_color="#F8D8D8",
                              command=lambda m=machine: self.show_block_time_form(m)).pack(side="left", padx=3)

                ctk.CTkButton(action_frame, text="📜 ประวัติ", width=70, height=32, fg_color="#F3E8FF", text_color="#7E22CE", border_width=1, border_color="#D8B4FE", hover_color="#E9D5FF",
                              command=lambda n=m_name: self.show_machine_log(n)).pack(side="left", padx=3)

                ctk.CTkButton(action_frame, text="✏️ แก้ไข", width=60, height=32, fg_color="#F8F9FA", text_color="#1A73E8", border_width=1, border_color="#DADCE0", hover_color="#E8F0FE",
                              command=lambda m=machine, r=r_num: self.show_machine_form(m, r)).pack(side="left", padx=3)
                
                ctk.CTkButton(action_frame, text="🗑️", width=35, height=32, fg_color="#F8F9FA", text_color="#D93025", border_width=1, border_color="#DADCE0", hover_color="#FCE8E6",
                              command=lambda n=m_name, r=r_num: self.delete_machine(n, r)).pack(side="left", padx=3)

        except Exception as e:
            ctk.CTkLabel(scroll_frame, text=f"⚠️ โหลดข้อมูลไม่สำเร็จ\n{e}", text_color="#D93025").pack(pady=50)