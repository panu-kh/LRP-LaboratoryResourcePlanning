import customtkinter as ctk
import gspread
import os
from PIL import Image
from dotenv import load_dotenv # ✅ นำเข้าไลบรารีอ่านไฟล์ .env

# โหลดค่าจากไฟล์ .env เข้าสู่ระบบ
load_dotenv()

# นำเข้าหน้าต่างๆ จากไฟล์ย่อยที่เราแยกไว้
from page_calendar import CalendarPage
from page_machines import MachinesPage
from page_users import UsersPage  
from page_dashboard import DashboardPage  

def connect_sheets():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        secret_file = os.path.join(current_dir, 'client_secret.json')
        auth_file = os.path.join(current_dir, 'authorized_user.json')

        if not os.path.exists(secret_file):
            return None, f"❌ ไม่พบไฟล์ที่:\n{secret_file}"
            
        gc = gspread.oauth(
            credentials_filename=secret_file,
            authorized_user_filename=auth_file
        )
        
        # ✅ ดึงรหัส Sheet จากไฟล์ .env แทนการฝังโค้ด
        SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
        if not SHEET_ID:
            return None, "❌ ไม่พบ GOOGLE_SHEET_ID ในไฟล์ .env"
            
        ss = gc.open_by_key(SHEET_ID)
        return ss, "✅ ยืนยันตัวตนสำเร็จ"
    except Exception as e:
        return None, f"❌ ข้อผิดพลาด: {e}"

class AdminERP(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Lab Management Mini ERP")
        self.geometry("1200x750")
        ctk.set_appearance_mode("light")
        self.configure(fg_color="#F0F2F5")

        self.spreadsheet = None 
        self.logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Support Logo.png')
        
        self.show_login_screen()

    def show_login_screen(self):
        self.login_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, width=450, height=380)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.login_frame.pack_propagate(False)

        if os.path.exists(self.logo_path):
            img = Image.open(self.logo_path)
            login_logo = ctk.CTkImage(light_image=img, size=(320, 85))
            ctk.CTkLabel(self.login_frame, image=login_logo, text="").pack(pady=(40, 10))
            ctk.CTkLabel(self.login_frame, text="LAB ADMIN ERP", font=("Arial", 18, "bold"), text_color="#1A73E8").pack(pady=(0, 5))
        else:
            ctk.CTkLabel(self.login_frame, text="LAB ADMIN ERP", font=("Arial", 32, "bold"), text_color="#1A73E8").pack(pady=(50, 10))

        ctk.CTkLabel(self.login_frame, text="ระบบจัดการข้อมูลการจองเครื่องมือวิทยาศาสตร์", font=("Arial", 14), text_color="#5F6368").pack(pady=(0, 25))

        self.login_btn = ctk.CTkButton(self.login_frame, text="🔒 Sign in with Google", font=("Arial", 16, "bold"), 
                                       fg_color="#1A73E8", hover_color="#174EA6", height=50, command=self.process_login)
        self.login_btn.pack(pady=10, padx=50, fill="x")

        self.status_label = ctk.CTkLabel(self.login_frame, text="", font=("Arial", 12))
        self.status_label.pack(pady=15)

    def process_login(self):
        self.status_label.configure(text="⏳ กรุณายืนยันตัวตนในหน้าต่างเบราว์เซอร์...", text_color="#F59E0B")
        self.login_btn.configure(state="disabled", fg_color="#A0A0A0")
        self.update()

        ss, message = connect_sheets()

        if ss:
            self.spreadsheet = ss
            self.login_frame.destroy()
            self.build_main_dashboard()
        else:
            self.status_label.configure(text=message, text_color="#D93025")
            self.login_btn.configure(state="normal", fg_color="#1A73E8")

    def build_main_dashboard(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#FFFFFF", border_width=1, border_color="#DADCE0")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        if os.path.exists(self.logo_path):
            img = Image.open(self.logo_path)
            sidebar_logo = ctk.CTkImage(light_image=img, size=(140, 35))
            ctk.CTkLabel(self.sidebar_frame, image=sidebar_logo, text="").pack(pady=(30, 0))
            ctk.CTkLabel(self.sidebar_frame, text="LAB ADMIN", font=ctk.CTkFont(size=16, weight="bold"), text_color="#1A73E8").pack(pady=(5, 25))
        else:
            ctk.CTkLabel(self.sidebar_frame, text="LAB ADMIN", font=ctk.CTkFont(size=24, weight="bold"), text_color="#1A73E8").pack(pady=40)

        self.create_menu_button("📅 ตารางการจอง", lambda: self.show_page(CalendarPage))
        self.create_menu_button("🛠 จัดการเครื่องมือ", lambda: self.show_page(MachinesPage)) 
        self.create_menu_button("👤 จัดการผู้ใช้", lambda: self.show_page(UsersPage)) 
        self.create_menu_button("📊 Dashboard", lambda: self.show_page(DashboardPage))

        ctk.CTkLabel(self.sidebar_frame, text="").pack(expand=True)

        btn_refresh = ctk.CTkButton(self.sidebar_frame, text="🔄 รีเฟรชข้อมูล", command=self.refresh_current_page,
                                    fg_color="#E8F0FE", text_color="#1967D2", hover_color="#D2E3FC", 
                                    anchor="center", height=45, font=("Arial", 15, "bold"))
        btn_refresh.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(self.sidebar_frame, text="Mini ERP v1.0", font=("Arial", 10), text_color="#A0A0A0").pack(side="bottom", pady=20)

        self.main_view = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view.grid(row=0, column=1, padx=25, pady=25, sticky="nsew")

        self.current_action = lambda: self.show_page(CalendarPage)
        self.current_action()

    def create_menu_button(self, text, command):
        btn = ctk.CTkButton(self.sidebar_frame, text=text, command=command, 
                            fg_color="transparent", text_color="#3C4043", hover_color="#F1F3F4", anchor="w", height=45, font=("Arial", 16))
        btn.pack(fill="x", padx=15, pady=8)

    def show_page(self, PageClass):
        self.current_action = lambda: self.show_page(PageClass)
        for widget in self.main_view.winfo_children():
            widget.destroy()
        page_instance = PageClass(self.main_view, self.spreadsheet)
        page_instance.pack(fill="both", expand=True)

    def placeholder_page(self):
        self.current_action = self.placeholder_page
        for widget in self.main_view.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.main_view, text="[ กำลังพัฒนาหน้านี้... ]", font=("Arial", 16), text_color="#A0A0A0").pack(pady=150)

    def refresh_current_page(self):
        if hasattr(self, 'current_action'):
            self.current_action()

if __name__ == "__main__":
    app = AdminERP()
    app.mainloop()