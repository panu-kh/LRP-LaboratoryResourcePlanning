import customtkinter as ctk
from datetime import datetime, timedelta
import calendar
from tkinter import messagebox

class CalendarPage(ctk.CTkFrame):
    def __init__(self, parent, spreadsheet):
        super().__init__(parent, fg_color="#F8F9FA")
        
        self.spreadsheet = spreadsheet
        self.current_view_date = datetime.now()
        self.time_slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
        self.current_overlay = None
        self.users_dict = {} 
        
        self.render_ui()

    def change_date(self, days):
        self.current_view_date += timedelta(days=days)
        self.refresh_page()

    def refresh_page(self):
        self.close_overlay()
        for widget in self.winfo_children():
            widget.destroy()
        self.render_ui()

    def get_column_index(self, time_str):
        hour = time_str[:2]
        for i, slot in enumerate(self.time_slots):
            if hour == slot[:2]:
                return i + 1
        return None

    def merge_continuous_bookings(self, bookings_list):
        if not bookings_list: return []
        bookings_list.sort(key=lambda x: x['StartCol'])
        merged = []
        
        current_block = bookings_list[0].copy()
        current_block['MergedRows'] = [current_block['RowNum']]

        for next_booking in bookings_list[1:]:
            if (current_block['Name'] == next_booking['Name'] and 
                current_block['Machine'] == next_booking['Machine'] and 
                current_block['EndCol'] == next_booking['StartCol']):
                
                current_block['EndCol'] = next_booking['EndCol']
                current_block['Span'] = current_block['EndCol'] - current_block['StartCol']
                start_t = current_block['TimeRange'].split('-')[0]
                end_t = next_booking['TimeRange'].split('-')[1]
                current_block['TimeRange'] = f"{start_t}-{end_t}"
                current_block['MergedRows'].append(next_booking['RowNum'])
            else:
                merged.append(current_block)
                current_block = next_booking.copy()
                current_block['MergedRows'] = [current_block['RowNum']]
                
        merged.append(current_block)
        return merged

    def close_overlay(self):
        if self.current_overlay:
            self.current_overlay.destroy()
            self.current_overlay = None

    def calculate_smart_position(self, widget, box_width, box_height):
        self.update_idletasks() 
        x = widget.winfo_rootx() - self.winfo_rootx()
        y = widget.winfo_rooty() - self.winfo_rooty()
        
        page_width = self.winfo_width()
        page_height = self.winfo_height()
        
        place_x = x + widget.winfo_width() + 10
        place_y = y
        
        if place_x + box_width > page_width:
            place_x = x - box_width - 10
            
        if place_y + box_height > page_height:
            place_y = page_height - box_height - 10
                
        return max(10, place_x), max(10, place_y)

    # ==================== ปฏิทิน Custom (แก้บั๊ก Text Clipping) ====================
    def show_calendar_dropdown(self):
        self.close_overlay()
        
        # ปรับขนาดกล่องให้สมส่วน
        box_width, box_height = 360, 420 
        
        self.current_overlay = ctk.CTkFrame(self, width=box_width, height=box_height, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#DADCE0")
        self.current_overlay.place(relx=1.0, rely=0.0, x=-5, y=55, anchor="ne")
        self.current_overlay.lift()
        self.current_overlay.pack_propagate(False)

        self.cal_year = self.current_view_date.year
        self.cal_month = self.current_view_date.month

        self.render_custom_calendar()

    def render_custom_calendar(self):
        for widget in self.current_overlay.winfo_children():
            widget.destroy()

        header_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        month_name = calendar.month_name[self.cal_month]
        ctk.CTkLabel(header_frame, text=f"{month_name} {self.cal_year}", font=("Arial", 16, "bold"), text_color="#202124").pack(side="left", padx=5)

        ctk.CTkButton(header_frame, text="✖", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", command=self.close_overlay).pack(side="right")

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=(0, 10))

        def prev_month():
            if self.cal_month == 1: self.cal_month = 12; self.cal_year -= 1
            else: self.cal_month -= 1
            self.render_custom_calendar()

        def next_month():
            if self.cal_month == 12: self.cal_month = 1; self.cal_year += 1
            else: self.cal_month += 1
            self.render_custom_calendar()

        ctk.CTkButton(btn_frame, text="<", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", corner_radius=15, command=prev_month).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text=">", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", corner_radius=15, command=next_month).pack(side="left", padx=2)

        cal_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent")
        cal_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # จุดเด็ดขาด: บังคับคอลัมน์ให้มีความกว้างขั้นต่ำ (minsize) ป้องกันโดนบีบจนพัง
        for i in range(7):
            cal_frame.grid_columnconfigure(i, weight=1, minsize=42)

        calendar.setfirstweekday(calendar.SUNDAY)

        days = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
        for i, day in enumerate(days):
            lbl = ctk.CTkLabel(cal_frame, text=day, font=("Arial", 12, "bold"), text_color="#5F6368")
            lbl.grid(row=0, column=i, pady=(0, 10))

        cal_matrix = calendar.monthcalendar(self.cal_year, self.cal_month)
        now = datetime.now()

        def select_date(d):
            self.current_view_date = datetime(self.cal_year, self.cal_month, d)
            self.refresh_page()

        for row, week in enumerate(cal_matrix):
            for col, day in enumerate(week):
                if day != 0:
                    is_today = (day == now.day and self.cal_month == now.month and self.cal_year == now.year)
                    is_selected = (day == self.current_view_date.day and self.cal_month == self.current_view_date.month and self.cal_year == self.current_view_date.year)

                    if is_selected: bg_color, txt_color, hover = "#1A73E8", "#FFFFFF", "#174EA6"
                    elif is_today: bg_color, txt_color, hover = "#E8F0FE", "#1A73E8", "#D2E3FC"
                    else: bg_color, txt_color, hover = "transparent", "#202124", "#F1F3F4"

                    # จุดเปลี่ยนสำคัญ: ใช้ปุ่มแบบ สี่เหลี่ยมขอบมน (corner_radius=8) จะไม่ตัดตัวอักษรแน่นอน
                    btn = ctk.CTkButton(cal_frame, text=str(day), width=36, height=36, corner_radius=8,
                                        font=("Arial", 13), fg_color=bg_color, text_color=txt_color, hover_color=hover,
                                        command=lambda d=day: select_date(d))
                    btn.grid(row=row+1, column=col, padx=2, pady=4)

    # ==================== กล่องดูข้อมูล และ แก้ไข ====================
    def show_booking_details_box(self, booking, clicked_widget):
        self.close_overlay()
        box_width, box_height = 340, 360 
        x, y = self.calculate_smart_position(clicked_widget, box_width, box_height)
        
        self.current_overlay = ctk.CTkFrame(self, width=box_width, height=box_height, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
        self.current_overlay.place(x=x, y=y)
        self.current_overlay.lift()
        self.current_overlay.pack_propagate(False)
        
        head_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent", corner_radius=0)
        head_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(head_frame, text="รายละเอียดการจอง", font=("Arial", 16, "bold"), text_color="#202124").pack(side="left", padx=15, pady=8)
        ctk.CTkButton(head_frame, text="✖", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", command=self.close_overlay).pack(side="right", padx=5)

        ctk.CTkLabel(self.current_overlay, text=f"🛠 {booking['Machine']}", font=("Arial", 16, "bold"), text_color="#1A73E8").pack(anchor="w", padx=20, pady=(0, 5))
        ctk.CTkLabel(self.current_overlay, text=f"👤 {booking['Name']}", font=("Arial", 14, "bold"), text_color="#202124").pack(anchor="w", padx=20, pady=0)
        
        role_display = booking['Year_Position'] if booking['Year_Position'] else 'ไม่ได้ระบุในระบบ'
        advisor_display = booking['Advisor'] if booking['Advisor'] else 'ไม่ได้ระบุในระบบ'
        
        ctk.CTkLabel(self.current_overlay, text=f"🎓 ชั้นปี/ตำแหน่ง: {role_display}", font=("Arial", 13), text_color="#5F6368").pack(anchor="w", padx=20, pady=0)
        ctk.CTkLabel(self.current_overlay, text=f"👨‍🏫 ที่ปรึกษา: {advisor_display}", font=("Arial", 13), text_color="#5F6368").pack(anchor="w", padx=20, pady=0)
        ctk.CTkLabel(self.current_overlay, text=f"⏱ เวลา: {booking['TimeRange']}", font=("Arial", 13), text_color="#5F6368").pack(anchor="w", padx=20, pady=(0, 10))

        edit_frame = ctk.CTkFrame(self.current_overlay, fg_color="#F8F9FA", corner_radius=8, border_width=1, border_color="#DADCE0")
        edit_frame.pack(fill="x", padx=15, pady=5, ipady=5)
        
        ctk.CTkLabel(edit_frame, text="แก้ไขเวลา:", font=("Arial", 12), text_color="#5F6368").grid(row=0, column=0, padx=10, pady=5)
        start_combo = ctk.CTkComboBox(edit_frame, values=self.time_slots, width=80, fg_color="#FFFFFF", border_color="#DADCE0")
        start_combo.set(booking['TimeRange'].split('-')[0])
        start_combo.grid(row=0, column=1)
        
        ctk.CTkLabel(edit_frame, text="-").grid(row=0, column=2, padx=2)
        end_combo = ctk.CTkComboBox(edit_frame, values=[f"{int(s[:2])+1:02d}:00" for s in self.time_slots], width=80, fg_color="#FFFFFF", border_color="#DADCE0")
        end_combo.set(booking['TimeRange'].split('-')[1])
        end_combo.grid(row=0, column=3)

        def save_edit():
            new_time = f"{start_combo.get()}-{end_combo.get()}"
            if start_combo.get() >= end_combo.get():
                messagebox.showerror("ข้อผิดพลาด", "เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุด")
                return
            try:
                sheet = self.spreadsheet.worksheet("Bookings")
                date_str = self.current_view_date.strftime("%Y-%m-%d")
                
                now = datetime.now()
                timestamp = f"{now.month}/{now.day}/{now.year} {now.strftime('%H:%M:%S')}"
                
                for r in sorted(booking['MergedRows'], reverse=True): sheet.delete_rows(r)
                
                new_row = [timestamp, booking['UserID'], booking['Machine'], date_str, new_time, booking['Name'], booking['Advisor'], booking['Year_Position']]
                sheet.append_row(new_row)
                self.refresh_page()
            except Exception as e: messagebox.showerror("Error", f"แก้ไขไม่สำเร็จ: {e}")

        def delete_booking():
            if messagebox.askyesno("ยืนยัน", "ต้องการยกเลิกการจองนี้ใช่หรือไม่?"):
                try:
                    sheet = self.spreadsheet.worksheet("Bookings")
                    for r in sorted(booking['MergedRows'], reverse=True): sheet.delete_rows(r)
                    self.refresh_page()
                except Exception as e: messagebox.showerror("Error", f"ลบไม่สำเร็จ: {e}")

        btn_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(btn_frame, text="บันทึก", fg_color="#1A73E8", hover_color="#174EA6", width=140, corner_radius=6, command=save_edit).pack(side="left")
        ctk.CTkButton(btn_frame, text="ลบ", fg_color="#D93025", hover_color="#A50E0E", width=80, corner_radius=6, command=delete_booking).pack(side="right")

    # ==================== กล่องสร้างการจองใหม่ ====================
    def show_new_booking_box(self, machine, clicked_time, clicked_widget):
        self.close_overlay()
        box_width, box_height = 320, 420 
        x, y = self.calculate_smart_position(clicked_widget, box_width, box_height)
        
        self.current_overlay = ctk.CTkFrame(self, width=box_width, height=box_height, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
        self.current_overlay.place(x=x, y=y)
        self.current_overlay.lift()
        self.current_overlay.pack_propagate(False)

        head_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent", corner_radius=0)
        head_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(head_frame, text="จองคิวใหม่ (Admin)", font=("Arial", 16, "bold"), text_color="#202124").pack(side="left", padx=15, pady=8)
        ctk.CTkButton(head_frame, text="✖", width=30, height=30, fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", command=self.close_overlay).pack(side="right", padx=5)

        ctk.CTkLabel(self.current_overlay, text=machine, font=("Arial", 16, "bold"), text_color="#1A73E8").pack(anchor="w", padx=20, pady=0)

        time_frame = ctk.CTkFrame(self.current_overlay, fg_color="transparent")
        time_frame.pack(fill="x", padx=15, pady=5)
        start_combo = ctk.CTkComboBox(time_frame, values=self.time_slots, width=90, fg_color="#FFFFFF", border_color="#DADCE0")
        start_combo.set(clicked_time)
        start_combo.pack(side="left", padx=5)
        ctk.CTkLabel(time_frame, text="-").pack(side="left")
        end_times = [f"{int(s[:2])+1:02d}:00" for s in self.time_slots]
        end_combo = ctk.CTkComboBox(time_frame, values=end_times, width=90, fg_color="#FFFFFF", border_color="#DADCE0")
        try: end_combo.set(end_times[self.time_slots.index(clicked_time)])
        except: pass
        end_combo.pack(side="left", padx=5)

        name_entry = ctk.CTkEntry(self.current_overlay, placeholder_text="ชื่อ-นามสกุล", height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        name_entry.pack(fill="x", padx=20, pady=5)
        
        year_entry = ctk.CTkEntry(self.current_overlay, placeholder_text="ชั้นปี/ตำแหน่ง (เช่น ป.โท มหิดล)", height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        year_entry.pack(fill="x", padx=20, pady=5)
        
        advisor_entry = ctk.CTkEntry(self.current_overlay, placeholder_text="ชื่ออาจารย์ที่ปรึกษา", height=35, fg_color="#F8F9FA", border_color="#DADCE0")
        advisor_entry.pack(fill="x", padx=20, pady=5)

        def save_new():
            name = name_entry.get().strip()
            year_pos = year_entry.get().strip()
            advisor = advisor_entry.get().strip()
            start_t = start_combo.get()
            end_t = end_combo.get()
            
            if not name: messagebox.showwarning("แจ้งเตือน", "กรุณาระบุชื่อผู้จอง"); return
            if start_t >= end_t: messagebox.showwarning("แจ้งเตือน", "เวลาเริ่มต้องน้อยกว่าสิ้นสุด"); return

            try:
                sheet = self.spreadsheet.worksheet("Bookings")
                date_str = self.current_view_date.strftime("%Y-%m-%d")
                
                now = datetime.now()
                timestamp = f"{now.month}/{now.day}/{now.year} {now.strftime('%H:%M:%S')}"
                
                new_row = [timestamp, "MANUAL_ADMIN", machine, date_str, f"{start_t}-{end_t}", name, advisor, year_pos]
                sheet.append_row(new_row)
                self.refresh_page()
            except Exception as e: messagebox.showerror("Error", f"ไม่สามารถบันทึกได้: {e}")

        ctk.CTkButton(self.current_overlay, text="ยืนยันการจอง", fg_color="#1E8E3E", hover_color="#137333", height=40, corner_radius=6, command=save_new).pack(fill="x", padx=20, pady=10)

    # ==================== วาดหน้าจอหลัก (ตาราง) ====================
    def render_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header_frame, text="ตารางการจองประจำวัน", font=("Arial", 26, "bold"), text_color="#202124").pack(side="left")
        
        date_control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        date_control_frame.pack(side="right")
        
        ctk.CTkButton(date_control_frame, text="<", command=lambda: self.change_date(-1), width=40, fg_color="#FFFFFF", border_width=1, border_color="#DADCE0", text_color="#5F6368", hover_color="#F1F3F4").pack(side="left", padx=5)
        
        current_date_str = self.current_view_date.strftime("%Y-%m-%d")
        day_name = self.current_view_date.strftime("%A")
        
        self.date_btn = ctk.CTkButton(date_control_frame, text=f"{current_date_str} ({day_name}) ▾", 
                                 font=("Arial", 14, "bold"), fg_color="#FFFFFF", border_width=1, border_color="#DADCE0", text_color="#1A73E8", 
                                 hover_color="#F8F9FA", command=self.show_calendar_dropdown)
        self.date_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(date_control_frame, text=">", command=lambda: self.change_date(1), width=40, fg_color="#FFFFFF", border_width=1, border_color="#DADCE0", text_color="#5F6368", hover_color="#F1F3F4").pack(side="left", padx=5)

        try:
            if self.spreadsheet:
                bookings_sheet = self.spreadsheet.worksheet("Bookings")
                all_values = bookings_sheet.get_all_values()
                bookings_data = []
                if len(all_values) > 1:
                    headers = all_values[0]
                    for i, row in enumerate(all_values[1:], start=2):
                        row_dict = dict(zip(headers, row))
                        row_dict['_row_num'] = i
                        bookings_data.append(row_dict)

                machines_sheet = self.spreadsheet.worksheet("Machines")
                unique_machines = list(dict.fromkeys(machines_sheet.col_values(1)[1:]))
            else:
                bookings_data, unique_machines = [], []
            
            num_time_slots = len(self.time_slots)
            data_for_date = {}

            for row in bookings_data:
                date = str(row.get('Date', '')).strip()
                if date == current_date_str:
                    machine = str(row.get('Machine', '')).strip()
                    time_range = str(row.get('Time', '')).strip()
                    name = str(row.get('Name', '')).strip()
                    advisor = str(row.get('Advisor', '')).strip()
                    year_pos = str(row.get('Year/Position', '')).strip()
                    user_id = str(row.get('UserID', '')).strip()
                    
                    if not machine or not time_range or '-' not in time_range: continue
                    
                    time_parts = time_range.split('-')
                    start_col = self.get_column_index(time_parts[0].strip())
                    end_col = self.get_column_index(time_parts[1].strip())
                    
                    if end_col is None and time_parts[1].strip() >= "16:00": end_col = num_time_slots + 1
                    elif end_col is None:
                        for i, slot in enumerate(self.time_slots):
                            if time_parts[1].strip()[:2] < slot[:2]:
                                end_col = i + 1
                                break
                        if end_col is None: end_col = num_time_slots + 1

                    if start_col and end_col and end_col > start_col:
                        if machine not in data_for_date: data_for_date[machine] = []
                        data_for_date[machine].append({
                            'StartCol': start_col, 'EndCol': end_col, 'Span': end_col - start_col, 
                            'Name': name, 'Machine': machine, 'TimeRange': time_range, 'RowNum': row.get('_row_num'),
                            'Advisor': advisor, 'Year_Position': year_pos, 'UserID': user_id
                        })

            scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
            scroll_frame.pack(fill="both", expand=True)

            scroll_frame.grid_columnconfigure(0, weight=0, minsize=160)
            for col in range(1, num_time_slots + 1):
                scroll_frame.grid_columnconfigure(col, weight=1, uniform="timeslot")

            ctk.CTkLabel(scroll_frame, text="ชื่อเครื่องมือ", font=("Arial", 14, "bold"), text_color="#5F6368", anchor="w").grid(row=0, column=0, padx=15, pady=15, sticky="ew")
            for col, slot in enumerate(self.time_slots):
                ctk.CTkLabel(scroll_frame, text=slot, font=("Arial", 14, "bold"), text_color="#5F6368").grid(row=0, column=col+1, padx=3, pady=15, sticky="ew")

            if unique_machines:
                for row_idx, machine_name in enumerate(unique_machines):
                    current_row = row_idx + 1
                    
                    ctk.CTkLabel(scroll_frame, text=f"🛠 {machine_name}", font=("Arial", 13, "bold"), text_color="#202124", anchor="w").grid(row=current_row, column=0, padx=20, pady=5, sticky="ew")
                    
                    for col_idx in range(num_time_slots):
                        slot_time = self.time_slots[col_idx]
                        empty_cell = ctk.CTkFrame(scroll_frame, fg_color="#FFFFFF", height=60, corner_radius=4, border_width=1, border_color="#F1F3F4", cursor="hand2")
                        empty_cell.grid(row=current_row, column=col_idx+1, padx=2, pady=5, sticky="nsew")
                        empty_cell.bind("<Button-1>", lambda e, m=machine_name, t=slot_time, w=empty_cell: self.show_new_booking_box(m, t, w))
                    
                    if machine_name in data_for_date:
                        merged_bookings = self.merge_continuous_bookings(data_for_date[machine_name])
                        
                        for booking in merged_bookings:
                            cell = ctk.CTkFrame(scroll_frame, fg_color="#E8F0FE", height=60, corner_radius=6, cursor="hand2")
                            cell.grid(row=current_row, column=booking['StartCol'], columnspan=booking['Span'], padx=2, pady=5, sticky="nsew")
                            
                            lbl_text = f"🛠 {booking['Machine']}\n👤 {booking['Name']}"
                            lbl = ctk.CTkLabel(cell, text=lbl_text, font=("Arial", 12, "bold"), text_color="#1967D2", justify="center", cursor="hand2")
                            lbl.pack(expand=True, fill="both", padx=2, pady=2)
                            
                            cell.bind("<Button-1>", lambda e, b=booking, w=cell: self.show_booking_details_box(b, w))
                            lbl.bind("<Button-1>", lambda e, b=booking, w=cell: self.show_booking_details_box(b, w))

        except Exception as e:
            ctk.CTkLabel(self, text=f"⚠️ โหลดข้อมูลตารางไม่สำเร็จ:\n{e}", text_color="#D93025").pack(pady=50)