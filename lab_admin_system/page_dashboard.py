import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import platform

if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = ['Sukhumvit Set', 'Thonburi', 'sans-serif']
else:
    plt.rcParams['font.family'] = ['Tahoma', 'sans-serif']

plt.rcParams['text.color'] = '#3C4043'
plt.rcParams['axes.labelcolor'] = '#5F6368'
plt.rcParams['xtick.color'] = '#5F6368'
plt.rcParams['ytick.color'] = '#5F6368'
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 11

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
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.attributes("-topmost", True)
        
        frame = tk.Frame(self.tooltip_window, background="#202124", padx=12, pady=8)
        frame.pack()
        
        font_name = "Sukhumvit Set" if platform.system() == 'Darwin' else "Tahoma"
        label = tk.Label(frame, text=self.text, fg="#F8F9FA", bg="#202124", font=(font_name, 11), justify="left")
        label.pack()
        self.move_tooltip(event)

    def move_tooltip(self, event):
        if self.tooltip_window:
            x, y = event.x_root + 15, event.y_root + 15
            self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, spreadsheet):
        super().__init__(parent, fg_color="#F0F2F5") 
        
        self.spreadsheet = spreadsheet
        self.bookings_cache = []
        self.users_cache = [] 
        self.ratings_cache = [] # ✅ เพิ่ม Cache เก็บ Rating
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
            
            # โหลด Bookings
            sheet_book = self.spreadsheet.worksheet("Bookings")
            book_vals = sheet_book.get_all_values()
            self.bookings_cache = []
            if len(book_vals) > 1:
                b_headers = book_vals[0]
                for row in book_vals[1:]:
                    self.bookings_cache.append(dict(zip(b_headers, row)))
                    
            # โหลด Users
            sheet_user = self.spreadsheet.worksheet("Users")
            user_vals = sheet_user.get_all_values()
            self.users_cache = []
            if len(user_vals) > 1:
                u_headers = user_vals[0]
                for row in user_vals[1:]:
                    self.users_cache.append(dict(zip(u_headers, row)))
                    
            # ✅ โหลด Ratings
            try:
                sheet_rating = self.spreadsheet.worksheet("Ratings")
                rating_vals = sheet_rating.get_all_values()
                self.ratings_cache = []
                if len(rating_vals) > 1:
                    r_headers = rating_vals[0]
                    for row in rating_vals[1:]:
                        self.ratings_cache.append(dict(zip(r_headers, row)))
            except Exception:
                pass # กรณีไม่มี Sheet Ratings หรือเกิด Error 

        except Exception as e:
            print(f"Error loading dashboard data: {e}")

    def render_ui(self):
        for widget in self.winfo_children(): widget.destroy()

        self.load_data()

        nav_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=70, border_width=1, border_color="#E0E0E0")
        nav_frame.pack(fill="x")
        nav_frame.pack_propagate(False)
        
        ctk.CTkLabel(nav_frame, text="Analytics", font=("Arial", 22, "bold"), text_color="#202124").pack(side="left", padx=30)

        tab_bg = ctk.CTkFrame(nav_frame, fg_color="#F1F3F4", corner_radius=20, height=40)
        tab_bg.pack(side="left", padx=20, pady=15)
        tab_bg.pack_propagate(False)

        def switch_tab(tab_name):
            self.current_tab = tab_name
            btn_over.configure(fg_color="#FFFFFF" if tab_name == "Overview" else "transparent", text_color="#1A73E8" if tab_name == "Overview" else "#5F6368")
            btn_user.configure(fg_color="#FFFFFF" if tab_name == "Users" else "transparent", text_color="#1A73E8" if tab_name == "Users" else "#5F6368")
            btn_time.configure(fg_color="#FFFFFF" if tab_name == "Times" else "transparent", text_color="#1A73E8" if tab_name == "Times" else "#5F6368")
            btn_rate.configure(fg_color="#FFFFFF" if tab_name == "Ratings" else "transparent", text_color="#1A73E8" if tab_name == "Ratings" else "#5F6368")
            self.update_dashboard()

        btn_over = ctk.CTkButton(tab_bg, text="Overview", font=("Arial", 13, "bold"), fg_color="#FFFFFF", text_color="#1A73E8", hover_color="#FFFFFF", corner_radius=15, width=90, height=32, command=lambda: switch_tab("Overview"))
        btn_over.pack(side="left", padx=4)
        
        btn_user = ctk.CTkButton(tab_bg, text="Users", font=("Arial", 13, "bold"), fg_color="transparent", text_color="#5F6368", hover_color="#E8EAED", corner_radius=15, width=90, height=32, command=lambda: switch_tab("Users"))
        btn_user.pack(side="left", padx=4)

        btn_time = ctk.CTkButton(tab_bg, text="Times", font=("Arial", 13, "bold"), fg_color="transparent", text_color="#5F6368", hover_color="#E8EAED", corner_radius=15, width=90, height=32, command=lambda: switch_tab("Times"))
        btn_time.pack(side="left", padx=4)

        # ✅ เพิ่มแท็บความพึงพอใจ
        btn_rate = ctk.CTkButton(tab_bg, text="⭐ Ratings", font=("Arial", 13, "bold"), fg_color="transparent", text_color="#5F6368", hover_color="#E8EAED", corner_radius=15, width=90, height=32, command=lambda: switch_tab("Ratings"))
        btn_rate.pack(side="left", padx=4)

        filter_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        filter_frame.pack(side="right", padx=30)
        ctk.CTkLabel(filter_frame, text="Filter by:", font=("Arial", 12), text_color="#5F6368").pack(side="left", padx=10)
        self.filter_var = ctk.StringVar(value="All Time")
        filter_combo = ctk.CTkComboBox(filter_frame, variable=self.filter_var, 
                                       values=["All Time", "This Month", "Last 30 Days"], 
                                       width=150, height=32, fg_color="#F8F9FA", border_color="#DADCE0", 
                                       font=("Arial", 12), dropdown_font=("Arial", 12), command=lambda e: self.update_dashboard())
        filter_combo.pack(side="left")

        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.update_dashboard()

    def clear_canvases(self):
        for canvas in self.canvases: canvas.get_tk_widget().destroy()
        self.canvases.clear()
        for widget in self.content_frame.winfo_children(): widget.destroy()

    def update_dashboard(self):
        self.clear_canvases()
        filtered_data = []
        filtered_ratings = []
        filter_val = self.filter_var.get()
        today = datetime.now()

        # กรองข้อมูล Bookings
        for b in self.bookings_cache:
            date_str = b.get('Date', '')
            try:
                b_date = datetime.strptime(date_str, "%Y-%m-%d")
                if filter_val == "This Month" and (b_date.month != today.month or b_date.year != today.year): continue
                elif filter_val == "Last 30 Days" and (today - b_date).days > 30: continue
            except: pass 
            filtered_data.append(b)

        # กรองข้อมูล Ratings (อิงจาก Timestamp)
        for r in self.ratings_cache:
            ts_str = r.get('Timestamp', '')
            try:
                r_date = datetime.strptime(ts_str, "%m/%d/%Y %H:%M:%S")
                if filter_val == "This Month" and (r_date.month != today.month or r_date.year != today.year): continue
                elif filter_val == "Last 30 Days" and (today - r_date).days > 30: continue
            except: pass
            filtered_ratings.append(r)

        if not filtered_data and self.current_tab != "Ratings":
            ctk.CTkLabel(self.content_frame, text="📭 ไม่พบข้อมูลในช่วงเวลานี้", font=("Arial", 16), text_color="#A0A0A0").pack(pady=100)
            return

        if self.current_tab == "Overview": self.render_overview(filtered_data)
        elif self.current_tab == "Users": self.render_users(filtered_data)
        elif self.current_tab == "Times": self.render_times(filtered_data)
        elif self.current_tab == "Ratings": self.render_ratings(filtered_ratings)

    def embed_plot(self, fig, parent):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas)

    def create_premium_card(self, parent, height=None):
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#E4E7EB")
        if height: 
            card.configure(height=height)
            card.pack_propagate(False)
        return card

    def format_chart_spines(self, ax):
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#E4E7EB')
        ax.tick_params(axis='y', length=0) 
        ax.tick_params(axis='x', color='#E4E7EB')

    # ==================== TAB 1: ภาพรวม (Overview) ====================
    def render_overview(self, data):
        cards_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 20))

        total_bookings = len(data)
        unique_users = len(set([b.get('Name', '') for b in data if b.get('Name')]))
        unique_machines = len(set([b.get('Machine', '') for b in data if b.get('Machine')]))

        def create_stat_card(parent, title, value, icon, accent_color):
            card = self.create_premium_card(parent, height=120)
            card.pack(side="left", fill="x", expand=True, padx=8)
            
            top_frame = ctk.CTkFrame(card, fg_color="transparent")
            top_frame.pack(fill="x", padx=20, pady=(20, 5))
            
            icon_bg = ctk.CTkFrame(top_frame, fg_color=f"{accent_color}1A", corner_radius=8, width=32, height=32)
            icon_bg.pack(side="left")
            icon_bg.pack_propagate(False)
            ctk.CTkLabel(icon_bg, text=icon, font=("Arial", 16), text_color=accent_color).pack(expand=True)
            
            ctk.CTkLabel(top_frame, text=title, font=("Arial", 13, "bold"), text_color="#5F6368").pack(side="left", padx=10)
            ctk.CTkLabel(card, text=f"{value:,}", font=("Arial", 36, "bold"), text_color="#202124").pack(anchor="w", padx=20, pady=(0, 10))

        create_stat_card(cards_frame, "Total Bookings", total_bookings, "📅", "#1A73E8")
        create_stat_card(cards_frame, "Active Users", unique_users, "👥", "#10B981")
        create_stat_card(cards_frame, "Machines Used", unique_machines, "⚙️", "#F59E0B")

        chart_card = self.create_premium_card(self.content_frame, height=450)
        chart_card.pack(fill="x", padx=8)

        machine_counts = Counter([b.get('Machine', 'Unknown') for b in data if b.get('Machine')])
        top_machines = machine_counts.most_common(5)
        
        if top_machines:
            labels = [m[0] for m in top_machines]
            values = [m[1] for m in top_machines]
            
            fig, ax = plt.subplots(figsize=(8, 4.5), facecolor='#FFFFFF')
            bars = ax.barh(labels, values, color='#3B82F6', edgecolor='none', height=0.5, alpha=0.85)
            
            ax.set_title('Top Equipment Usage', pad=25, weight='bold', loc='left', fontsize=16)
            ax.invert_yaxis()
            self.format_chart_spines(ax)
            ax.grid(axis='x', linestyle='-', alpha=0.3, color='#E4E7EB')
            
            for bar in bars:
                width = bar.get_width()
                ax.text(width + (max(values)*0.01), bar.get_y() + bar.get_height()/2, f' {int(width)}', 
                        va='center', ha='left', fontsize=11, color='#1A73E8', weight='bold')
            
            fig.tight_layout()
            self.embed_plot(fig, chart_card)

    # ==================== TAB 2: พฤติกรรมผู้ใช้ (Users) ====================
    def render_users(self, data):
        row_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        row_frame.pack(fill="x")
        
        left_card = self.create_premium_card(row_frame)
        left_card.pack(side="left", fill="both", expand=True, padx=(8, 10))
        
        head_f = ctk.CTkFrame(left_card, fg_color="transparent")
        head_f.pack(fill="x", padx=25, pady=20)
        ctk.CTkLabel(head_f, text="Top Users Leaderboard", font=("Arial", 16, "bold"), text_color="#202124").pack(side="left")
        ctk.CTkLabel(head_f, text="Hover for details", font=("Arial", 11), text_color="#9CA3AF").pack(side="right")
        
        user_counts = Counter([b.get('Name', 'Unknown') for b in data if b.get('Name')])
        top_users = user_counts.most_common(5)
        
        for i, (name, count) in enumerate(top_users):
            medals = ["🥇", "🥈", "🥉", "4", "5"]
            bg_color = "#F8FAFC" if i % 2 == 0 else "#FFFFFF" 
            
            item_frame = ctk.CTkFrame(left_card, fg_color=bg_color, corner_radius=8, cursor="hand2", height=50)
            item_frame.pack(fill="x", padx=20, pady=4)
            item_frame.pack_propagate(False)
            
            rank_l = ctk.CTkLabel(item_frame, text=medals[i], font=("Arial", 16), width=30)
            rank_l.pack(side="left", padx=(10, 5))
            
            lbl_name = ctk.CTkLabel(item_frame, text=name, font=("Arial", 14, "bold"), text_color="#374151")
            lbl_name.pack(side="left", padx=5)
            
            lbl_count = ctk.CTkLabel(item_frame, text=f"{count} bookings", font=("Arial", 13, "bold"), text_color="#3B82F6")
            lbl_count.pack(side="right", padx=15)

            u_info = next((u for u in self.users_cache if u.get('Name') == name), None)
            if u_info: tt_text = f"ID: {u_info.get('UserID', '-')}\nYear: {u_info.get('Year', '-')}\nAdvisor: {u_info.get('Advisor', '-')}\nStatus: {u_info.get('Status', 'Active')}"
            else: tt_text = "No profile data available."
            
            ToolTip(item_frame, tt_text); ToolTip(lbl_name, tt_text); ToolTip(rank_l, tt_text); ToolTip(lbl_count, tt_text)

        right_card = self.create_premium_card(row_frame, height=400)
        right_card.pack(side="right", fill="both", expand=True, padx=(10, 8))
        
        year_counts = Counter([b.get('Year/Position', 'ไม่ได้ระบุ') for b in data if b.get('Year/Position')])
        
        if year_counts:
            total = sum(year_counts.values())
            processed_counts = {}
            others = 0
            for k, v in year_counts.items():
                if v / total < 0.04: others += v
                else: processed_counts[k] = v
            if others > 0: processed_counts['Others'] = others

            labels = list(processed_counts.keys())
            values = list(processed_counts.values())
            
            fig, ax = plt.subplots(figsize=(7, 4), facecolor='#FFFFFF')
            colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#14B8A6', '#F43F5E', '#94A3B8']
            
            wedges, texts, autotexts = ax.pie(values, autopct='%1.1f%%', startangle=90, colors=colors, 
                                              textprops=dict(color="w", weight="bold", fontsize=9),
                                              pctdistance=0.75, wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2))
            
            ax.legend(wedges, labels, title="User Role", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), frameon=False)
            ax.set_title('Booking Distribution by Role', pad=20, weight='bold', loc='left', fontsize=14)
            
            annot = ax.annotate("", xy=(0,0), xytext=(20, 20), textcoords="offset points",
                                bbox=dict(boxstyle="round4,pad=0.6", fc="#202124", ec="none", alpha=0.9),
                                arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-0.2", fc="#202124", ec="none"),
                                color="white", weight="bold")
            annot.set_visible(False)

            def hover(event):
                vis = annot.get_visible()
                if event.inaxes == ax:
                    for i, wedge in enumerate(wedges):
                        cont, _ = wedge.contains(event)
                        if cont:
                            annot.xy = (event.xdata, event.ydata)
                            annot.set_text(f"{labels[i]}\n{values[i]} Bookings")
                            annot.set_visible(True)
                            fig.canvas.draw_idle()
                            return
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

            fig.canvas.mpl_connect("motion_notify_event", hover)
            fig.tight_layout()
            self.embed_plot(fig, right_card)

    # ==================== TAB 3: ช่วงเวลายอดฮิต (Times) ====================
    def switch_time_mode(self, mode):
        self.time_stat_type = "slots" if "Time Slots" in mode else "timestamp"
        self.update_dashboard()

    def render_times(self, data):
        toggle_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        toggle_frame.pack(fill="x", pady=(0, 10), padx=8)
        
        seg_btn = ctk.CTkSegmentedButton(toggle_frame, values=["Usage Time Slots", "Booking Timestamps"], 
                                         command=self.switch_time_mode, font=("Arial", 13, "bold"), 
                                         selected_color="#3B82F6", selected_hover_color="#2563EB", unselected_color="#FFFFFF")
        seg_btn.pack(anchor="w", pady=5)
        seg_btn.set("Usage Time Slots" if self.time_stat_type == "slots" else "Booking Timestamps")

        chart_card = self.create_premium_card(self.content_frame, height=480)
        chart_card.pack(fill="x", padx=8, pady=5)
        
        if self.time_stat_type == "slots":
            counts = Counter([b.get('Time', 'Unknown') for b in data if b.get('Time') and '-' in b.get('Time', '')])
            title_text = 'Usage Time Slots Popularity'
            x_label = 'Time Slots'
        else:
            hours = []
            for b in data:
                ts = b.get('Timestamp', '')
                if ts and ':' in ts:
                    try:
                        time_part = ts.split(' ')[-1] 
                        h_str = time_part.split(':')[0]
                        if h_str.isdigit(): hours.append(f"{int(h_str):02d}:00")
                    except: pass
            counts = Counter(hours)
            title_text = 'When do users book? (Peak Activity)'
            x_label = 'Hour of Day'

        sorted_times = sorted(counts.items(), key=lambda x: x[0])
        
        if sorted_times:
            labels = [t[0] for t in sorted_times]
            values = [t[1] for t in sorted_times]
            
            fig, ax = plt.subplots(figsize=(10, 5), facecolor='#FFFFFF')
            
            max_val = max(values)
            colors = ['#F43F5E' if val == max_val else '#E2E8F0' for val in values]
            
            bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor='none')
            
            ax.set_title(title_text, pad=25, weight='bold', fontsize=16, loc='left')
            self.format_chart_spines(ax)
            ax.grid(axis='y', linestyle='-', alpha=0.3, color='#E4E7EB')
            plt.xticks(rotation=45, ha='right')
            
            for bar in bars:
                height = bar.get_height()
                color = '#F43F5E' if height == max_val else '#64748B'
                ax.text(bar.get_x() + bar.get_width()/2., height + (max_val*0.02), f'{int(height)}', 
                        ha='center', va='bottom', fontsize=11, color=color, weight='bold')
            
            fig.tight_layout()
            self.embed_plot(fig, chart_card)
        else:
            ctk.CTkLabel(chart_card, text="Insufficient data to generate chart", font=("Arial", 14), text_color="#A0A0A0").pack(expand=True)

    # ==================== TAB 4: ความพึงพอใจ (Ratings) ====================
    def render_ratings(self, ratings_data):
        if not ratings_data:
            ctk.CTkLabel(self.content_frame, text="📭 ยังไม่มีข้อมูลการให้คะแนนจากผู้ใช้", font=("Arial", 16), text_color="#A0A0A0").pack(pady=100)
            return

        scores = []
        for r in ratings_data:
            try: scores.append(int(r.get('Score', 0)))
            except: pass
            
        scores = [s for s in scores if 1 <= s <= 5] # กรองเฉพาะ 1-5 ดาว
        
        if not scores:
            ctk.CTkLabel(self.content_frame, text="📭 ข้อมูลคะแนนไม่ถูกต้อง", font=("Arial", 16), text_color="#A0A0A0").pack(pady=100)
            return

        total_ratings = len(scores)
        avg_score = sum(scores) / total_ratings

        cards_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 20))

        # สรุปคะแนนเฉลี่ย
        avg_card = self.create_premium_card(cards_frame, height=130)
        avg_card.pack(side="left", fill="both", expand=True, padx=8)
        ctk.CTkLabel(avg_card, text="Overall Satisfaction Score", font=("Arial", 14, "bold"), text_color="#5F6368").pack(anchor="w", padx=20, pady=(20, 5))
        
        score_frame = ctk.CTkFrame(avg_card, fg_color="transparent")
        score_frame.pack(anchor="w", padx=20)
        ctk.CTkLabel(score_frame, text=f"{avg_score:.1f}", font=("Arial", 42, "bold"), text_color="#202124").pack(side="left")
        ctk.CTkLabel(score_frame, text=" / 5.0", font=("Arial", 20, "bold"), text_color="#9CA3AF").pack(side="left", pady=(15,0))
        
        # แสดงดาวตามคะแนนเฉลี่ย
        stars = "⭐" * int(round(avg_score))
        ctk.CTkLabel(avg_card, text=stars, font=("Arial", 18), text_color="#F59E0B").pack(anchor="w", padx=20)

        # สรุปจำนวนคนให้คะแนน
        count_card = self.create_premium_card(cards_frame, height=130)
        count_card.pack(side="left", fill="both", expand=True, padx=8)
        ctk.CTkLabel(count_card, text="Total Ratings Received", font=("Arial", 14, "bold"), text_color="#5F6368").pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(count_card, text=f"{total_ratings:,}", font=("Arial", 42, "bold"), text_color="#3B82F6").pack(anchor="w", padx=20)
        ctk.CTkLabel(count_card, text="Feedbacks", font=("Arial", 14), text_color="#9CA3AF").pack(anchor="w", padx=20)

        # กราฟแท่งแสดงสัดส่วนคะแนน
        chart_card = self.create_premium_card(self.content_frame, height=400)
        chart_card.pack(fill="x", padx=8)

        score_counts = Counter(scores)
        # บังคับให้มี 5 ดาว ถึง 1 ดาว เสมอ แม้บางดาวจะไม่มีคนโหวต
        labels = ["5 Stars ⭐", "4 Stars ⭐", "3 Stars ⭐", "2 Stars ⭐", "1 Star ⭐"]
        values = [score_counts.get(5, 0), score_counts.get(4, 0), score_counts.get(3, 0), score_counts.get(2, 0), score_counts.get(1, 0)]
        
        fig, ax = plt.subplots(figsize=(8, 4), facecolor='#FFFFFF')
        
        # สีแยกตามระดับความพึงพอใจ
        colors = ['#10B981', '#34D399', '#FBBF24', '#F87171', '#EF4444']
        bars = ax.barh(labels, values, color=colors, edgecolor='none', height=0.5, alpha=0.9)
        
        ax.set_title('Score Distribution', pad=25, weight='bold', loc='left', fontsize=16)
        ax.invert_yaxis() # เอา 5 ดาวไว้บนสุด
        self.format_chart_spines(ax)
        ax.grid(axis='x', linestyle='-', alpha=0.3, color='#E4E7EB')
        
        for bar in bars:
            width = bar.get_width()
            if width > 0:
                ax.text(width + (max(values)*0.01), bar.get_y() + bar.get_height()/2, f' {int(width)}', 
                        va='center', ha='left', fontsize=11, color='#4B5563', weight='bold')
        
        fig.tight_layout()
        self.embed_plot(fig, chart_card)