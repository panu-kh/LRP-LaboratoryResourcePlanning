import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import platform

# ==================== ตั้งค่า Font ====================
if platform.system() == 'Darwin': # สำหรับ macOS
    plt.rcParams['font.family'] = ['Sukhumvit Set', 'Thonburi', 'sans-serif']
else: # สำหรับ Windows
    plt.rcParams['font.family'] = ['Tahoma', 'sans-serif']
    
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# ==================== Class สำหรับสร้างกล่องข้อความลอย (Tooltip) ====================
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.move_tooltip)

    def show_tooltip(self, event):
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # ลบขอบหน้าต่าง
        self.tooltip_window.attributes("-topmost", True) # ให้อยู่หน้าสุด
        
        frame = tk.Frame(self.tooltip_window, background="#202124", padx=10, pady=8)
        frame.pack()
        
        font_name = "Sukhumvit Set" if platform.system() == 'Darwin' else "Tahoma"
        label = tk.Label(frame, text=self.text, fg="#FFFFFF", bg="#202124", 
                         font=(font_name, 11), justify="left")
        label.pack()
        self.move_tooltip(event)

    def move_tooltip(self, event):
        if self.tooltip_window:
            # ให้กล่องลอยตามเมาส์ (เยื้องไปด้านขวาล่างนิดหน่อย)
            x = event.x_root + 15
            y = event.y_root + 15
            self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# ==================== หน้าหลัก Dashboard ====================
class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, spreadsheet):
        super().__init__(parent, fg_color="#F8F9FA")
        
        self.spreadsheet = spreadsheet
        self.bookings_cache = []
        self.users_cache = [] # เพิ่ม Cache สำหรับเก็บประวัติผู้ใช้
        self.current_tab = "Overview"
        self.time_stat_type = "slots" 
        self.canvases = [] 
        
        self.render_ui()

    def refresh_page(self):
        self.load_data()
        self.update_dashboard()

    def load_data(self):
        try:
            if not self.spreadsheet: return
            
            # ดึงข้อมูลการจอง (สำหรับกราฟ)
            sheet_book = self.spreadsheet.worksheet("Bookings")
            book_vals = sheet_book.get_all_values()
            self.bookings_cache = []
            if len(book_vals) > 1:
                b_headers = book_vals[0]
                for row in book_vals[1:]:
                    self.bookings_cache.append(dict(zip(b_headers, row)))
                    
            # ดึงข้อมูลผู้ใช้ (สำหรับ Hover ดูโปรไฟล์)
            sheet_user = self.spreadsheet.worksheet("Users")
            user_vals = sheet_user.get_all_values()
            self.users_cache = []
            if len(user_vals) > 1:
                u_headers = user_vals[0]
                for row in user_vals[1:]:
                    self.users_cache.append(dict(zip(u_headers, row)))
                    
        except Exception as e:
            print(f"Error loading dashboard data: {e}")

    def render_ui(self):
        for widget in self.winfo_children(): widget.destroy()

        ctk.CTkLabel(self, text="⏳ กำลังโหลดข้อมูลสถิติ...", font=("Arial", 16), text_color="#A0A0A0").pack(pady=100)
        self.update()
        self.load_data()
        for widget in self.winfo_children(): widget.destroy()

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header_frame, text="📊 Dashboard สถิติการใช้งาน", font=("Arial", 26, "bold"), text_color="#202124").pack(side="left")

        tab_frame = ctk.CTkFrame(header_frame, fg_color="#E8EAED", corner_radius=8)
        tab_frame.pack(side="left", padx=20)
        
        def switch_tab(tab_name):
            self.current_tab = tab_name
            btn_over.configure(fg_color="#FFFFFF" if tab_name == "Overview" else "transparent", text_color="#1A73E8" if tab_name == "Overview" else "#5F6368")
            btn_user.configure(fg_color="#FFFFFF" if tab_name == "Users" else "transparent", text_color="#1A73E8" if tab_name == "Users" else "#5F6368")
            btn_time.configure(fg_color="#FFFFFF" if tab_name == "Times" else "transparent", text_color="#1A73E8" if tab_name == "Times" else "#5F6368")
            self.update_dashboard()

        btn_over = ctk.CTkButton(tab_frame, text="📈 ภาพรวม (Overview)", font=("Arial", 14, "bold"), fg_color="#FFFFFF", text_color="#1A73E8", hover_color="#F1F3F4", corner_radius=6, command=lambda: switch_tab("Overview"))
        btn_over.pack(side="left", padx=2, pady=2)
        
        btn_user = ctk.CTkButton(tab_frame, text="👥 พฤติกรรมผู้ใช้", font=("Arial", 14, "bold"), fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", corner_radius=6, command=lambda: switch_tab("Users"))
        btn_user.pack(side="left", padx=2, pady=2)

        btn_time = ctk.CTkButton(tab_frame, text="⏱️ ช่วงเวลายอดฮิต", font=("Arial", 14, "bold"), fg_color="transparent", text_color="#5F6368", hover_color="#F1F3F4", corner_radius=6, command=lambda: switch_tab("Times"))
        btn_time.pack(side="left", padx=2, pady=2)

        filter_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#DADCE0", height=60)
        filter_frame.pack(fill="x", pady=(0, 15))
        filter_frame.pack_propagate(False)

        ctk.CTkLabel(filter_frame, text="📅 กรองข้อมูลตามเวลา:", font=("Arial", 14, "bold"), text_color="#5F6368").pack(side="left", padx=(20, 10))
        
        self.filter_var = ctk.StringVar(value="ทั้งหมด (All Time)")
        filter_combo = ctk.CTkComboBox(filter_frame, variable=self.filter_var, 
                                       values=["ทั้งหมด (All Time)", "เดือนนี้ (This Month)", "30 วันที่ผ่านมา (Last 30 Days)"], 
                                       width=200, fg_color="#F8F9FA", border_color="#DADCE0", command=lambda e: self.update_dashboard())
        filter_combo.pack(side="left", pady=10)

        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.content_frame.pack(fill="both", expand=True)

        self.update_dashboard()

    def clear_canvases(self):
        for canvas in self.canvases:
            canvas.get_tk_widget().destroy()
        self.canvases.clear()
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def update_dashboard(self):
        self.clear_canvases()
        
        filtered_data = []
        filter_val = self.filter_var.get()
        today = datetime.now()

        for b in self.bookings_cache:
            date_str = b.get('Date', '')
            try:
                b_date = datetime.strptime(date_str, "%Y-%m-%d")
                if filter_val == "เดือนนี้ (This Month)":
                    if b_date.month != today.month or b_date.year != today.year: continue
                elif filter_val == "30 วันที่ผ่านมา (Last 30 Days)":
                    if (today - b_date).days > 30: continue
            except:
                pass 
            filtered_data.append(b)

        if not filtered_data:
            ctk.CTkLabel(self.content_frame, text="📭 ไม่พบข้อมูลการจองในช่วงเวลานี้", font=("Arial", 16), text_color="#A0A0A0").pack(pady=50)
            return

        if self.current_tab == "Overview":
            self.render_overview(filtered_data)
        elif self.current_tab == "Users":
            self.render_users(filtered_data)
        elif self.current_tab == "Times":
            self.render_times(filtered_data)

    def embed_plot(self, fig, parent):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvases.append(canvas)

    # ==================== TAB 1: ภาพรวม (Overview) ====================
    def render_overview(self, data):
        cards_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 20))

        total_bookings = len(data)
        unique_users = len(set([b.get('Name', '') for b in data if b.get('Name')]))
        unique_machines = len(set([b.get('Machine', '') for b in data if b.get('Machine')]))

        def create_stat_card(parent, title, value, color):
            card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0", height=100)
            card.pack(side="left", fill="x", expand=True, padx=5)
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=title, font=("Arial", 14, "bold"), text_color="#5F6368").pack(anchor="w", padx=20, pady=(15, 0))
            ctk.CTkLabel(card, text=str(value), font=("Arial", 32, "bold"), text_color=color).pack(anchor="w", padx=20)

        create_stat_card(cards_frame, "📝 จำนวนการจองทั้งหมด", total_bookings, "#1A73E8")
        create_stat_card(cards_frame, "👥 ผู้ใช้งานในระบบ", unique_users, "#1E8E3E")
        create_stat_card(cards_frame, "🛠 เครื่องมือที่ถูกใช้งาน", unique_machines, "#D93025")

        chart_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0", height=400)
        chart_frame.pack(fill="x", pady=5)
        chart_frame.pack_propagate(False)

        machine_counts = Counter([b.get('Machine', 'Unknown') for b in data if b.get('Machine')])
        top_machines = machine_counts.most_common(5)
        
        if top_machines:
            labels = [m[0] for m in top_machines]
            values = [m[1] for m in top_machines]
            
            fig, ax = plt.subplots(figsize=(8, 4), facecolor='#FFFFFF')
            bars = ax.barh(labels, values, color='#4A90E2', edgecolor='none', height=0.6)
            ax.set_title('🏆 Top 5 เครื่องมือที่ถูกใช้งานมากที่สุด', pad=20, weight='bold')
            ax.set_xlabel('จำนวนครั้งที่จอง', color='#5F6368')
            ax.invert_yaxis()
            
            for bar in bars:
                ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, f'{int(bar.get_width())}', 
                        va='center', ha='left', fontsize=10, color='#333333', weight='bold')
            
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color('#DADCE0')
            ax.spines['left'].set_color('#DADCE0')
            fig.tight_layout()
            
            self.embed_plot(fig, chart_frame)

    # ==================== TAB 2: พฤติกรรมผู้ใช้ (User Insights & Interactive) ====================
    def render_users(self, data):
        row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=5)
        
        # ---------------- ส่วน Top 5 Users (มี Tooltip) ----------------
        left_frame = ctk.CTkFrame(row_frame, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(left_frame, text="👑 Top 5 ผู้ใช้งานที่จองเยอะที่สุด", font=("Arial", 16, "bold"), text_color="#1A73E8").pack(pady=15)
        
        user_counts = Counter([b.get('Name', 'Unknown') for b in data if b.get('Name')])
        top_users = user_counts.most_common(5)
        
        for i, (name, count) in enumerate(top_users):
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            item_frame = ctk.CTkFrame(left_frame, fg_color="#F8F9FA", corner_radius=8, cursor="hand2") # เปลี่ยน cursor เป็นรูปมือ
            item_frame.pack(fill="x", padx=20, pady=5)
            
            lbl_name = ctk.CTkLabel(item_frame, text=f"{medals[i]}  {name}", font=("Arial", 14, "bold"), text_color="#3C4043", cursor="hand2")
            lbl_name.pack(side="left", padx=15, pady=10)
            lbl_count = ctk.CTkLabel(item_frame, text=f"{count} ครั้ง", font=("Arial", 14, "bold"), text_color="#D93025", cursor="hand2")
            lbl_count.pack(side="right", padx=15, pady=10)

            # ค้นหาข้อมูลผู้ใช้นี้จาก Users Cache
            u_info = next((u for u in self.users_cache if u.get('Name') == name), None)
            if u_info:
                # ประกอบร่างข้อความ Tooltip
                tt_text = f"🆔 รหัส: {u_info.get('UserID', '-')}\n🎓 ชั้นปี: {u_info.get('Year', '-')}\n👨‍🏫 อ.ที่ปรึกษา: {u_info.get('Advisor', '-')}\nสถานะ: {u_info.get('Status', 'Active')}"
            else:
                tt_text = "⚠️ ไม่พบข้อมูลโปรไฟล์\nในฐานข้อมูลผู้ใช้"
            
            # ผูก Tooltip เข้ากับกล่องและข้อความ
            ToolTip(item_frame, tt_text)
            ToolTip(lbl_name, tt_text)
            ToolTip(lbl_count, tt_text)

        # ---------------- ส่วน Interactive Pie Chart ----------------
        right_frame = ctk.CTkFrame(row_frame, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0", height=400)
        right_frame.pack(side="right", fill="both", expand=True)
        right_frame.pack_propagate(False)
        
        year_counts = Counter([b.get('Year/Position', 'ไม่ได้ระบุ') for b in data if b.get('Year/Position')])
        
        if year_counts:
            total = sum(year_counts.values())
            processed_counts = {}
            others = 0
            for k, v in year_counts.items():
                if v / total < 0.03: others += v
                else: processed_counts[k] = v
            if others > 0: processed_counts['อื่นๆ (Others)'] = others

            labels = list(processed_counts.keys())
            values = list(processed_counts.values())
            
            fig, ax = plt.subplots(figsize=(7, 4), facecolor='#FFFFFF')
            colors = ['#1A73E8', '#34A853', '#FBBC05', '#EA4335', '#8E24AA', '#F29900', '#00ACC1', '#FF4081', '#9E9E9E']
            
            wedges, texts, autotexts = ax.pie(values, autopct='%1.1f%%', startangle=90, colors=colors, 
                                              textprops=dict(color="w", weight="bold", fontsize=10),
                                              pctdistance=0.75, wedgeprops=dict(width=0.4, edgecolor='w'))
            
            ax.legend(wedges, labels, title="ระดับ/ตำแหน่ง", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), frameon=False)
            ax.set_title('สัดส่วนการจองแบ่งตามชั้นปี/ตำแหน่ง\n(เอาเมาส์ชี้ที่กราฟเพื่อดูรายละเอียด)', pad=20, weight='bold', fontsize=12)
            
            # --- สร้างระบบ Hover สำหรับ Matplotlib ---
            # สร้างกล่องข้อความเปล่าๆ ซ่อนไว้ก่อน
            annot = ax.annotate("", xy=(0,0), xytext=(20, 20), textcoords="offset points",
                                bbox=dict(boxstyle="round4,pad=0.5", fc="white", ec="#DADCE0", alpha=0.95),
                                arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-0.2", fc="gray"))
            annot.set_visible(False)

            def hover(event):
                vis = annot.get_visible()
                if event.inaxes == ax:
                    for i, wedge in enumerate(wedges):
                        # เช็คว่าเมาส์ชี้โดนชิ้นส่วนไหน
                        cont, ind = wedge.contains(event)
                        if cont:
                            annot.xy = (event.xdata, event.ydata)
                            percent = (values[i] / total) * 100
                            # ใส่ข้อความบอกรายละเอียดครบถ้วน
                            annot.set_text(f"{labels[i]}\n{values[i]} ครั้ง ({percent:.1f}%)")
                            annot.set_visible(True)
                            fig.canvas.draw_idle()
                            return
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

            # ผูก Event เมาส์ขยับ เข้ากับฟังก์ชัน
            fig.canvas.mpl_connect("motion_notify_event", hover)
            
            fig.tight_layout()
            self.embed_plot(fig, right_frame)

    # ==================== TAB 3: ช่วงเวลายอดฮิต ====================
    def switch_time_mode(self, mode):
        self.time_stat_type = "slots" if "ช่วงเวลาที่ถูกจอง" in mode else "timestamp"
        self.update_dashboard()

    def render_times(self, data):
        toggle_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        toggle_frame.pack(fill="x", pady=(0, 10))
        
        seg_btn = ctk.CTkSegmentedButton(toggle_frame, values=["ช่วงเวลาที่ถูกจอง (Time Slots)", "เวลาที่ทำรายการ (Booking Timestamp)"], 
                                         command=self.switch_time_mode, font=("Arial", 13, "bold"), selected_color="#1A73E8", selected_hover_color="#174EA6")
        seg_btn.pack(pady=5)
        seg_btn.set("ช่วงเวลาที่ถูกจอง (Time Slots)" if self.time_stat_type == "slots" else "เวลาที่ทำรายการ (Booking Timestamp)")

        chart_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#DADCE0", height=450)
        chart_frame.pack(fill="x", pady=5)
        chart_frame.pack_propagate(False)
        
        if self.time_stat_type == "slots":
            counts = Counter([b.get('Time', 'Unknown') for b in data if b.get('Time') and '-' in b.get('Time', '')])
            title_text = '🔥 ช่วงเวลา (Time Slots) ที่ถูกใช้เครื่องมือมากที่สุด'
            x_label = 'ช่วงเวลา'
        else:
            hours = []
            for b in data:
                ts = b.get('Timestamp', '')
                if ts and ':' in ts:
                    try:
                        time_part = ts.split(' ')[-1] 
                        h_str = time_part.split(':')[0]
                        if h_str.isdigit():
                            hours.append(f"{int(h_str):02d}:00")
                    except: pass
            counts = Counter(hours)
            title_text = '⏳ ช่วงเวลาที่ผู้ใช้ "กดทำรายการจอง" มากที่สุด (Peak Booking Hours)'
            x_label = 'เวลาที่กดทำรายการ'

        sorted_times = sorted(counts.items(), key=lambda x: x[0])
        
        if sorted_times:
            labels = [t[0] for t in sorted_times]
            values = [t[1] for t in sorted_times]
            
            fig, ax = plt.subplots(figsize=(10, 5), facecolor='#FFFFFF')
            
            max_val = max(values)
            colors = ['#EA4335' if val == max_val else '#4A90E2' for val in values]
            
            bars = ax.bar(labels, values, color=colors, width=0.6, edgecolor='none', alpha=0.9)
            
            ax.set_title(title_text, pad=20, weight='bold', fontsize=14)
            ax.set_ylabel('จำนวนครั้ง', color='#5F6368')
            ax.set_xlabel(x_label, color='#5F6368')
            
            plt.xticks(rotation=45, ha='right')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1, f'{int(height)}', 
                        ha='center', va='bottom', fontsize=11, color='#333333', weight='bold')
            
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#DADCE0')
            ax.spines['bottom'].set_color('#DADCE0')
            ax.grid(axis='y', linestyle='--', alpha=0.4) 
            fig.tight_layout()
            
            self.embed_plot(fig, chart_frame)
        else:
            ctk.CTkLabel(chart_frame, text="ไม่พบข้อมูลเพียงพอสำหรับสร้างกราฟ", font=("Arial", 14), text_color="#A0A0A0").pack(expand=True)