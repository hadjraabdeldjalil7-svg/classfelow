import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, datetime, smtplib, qrcode
from email.mime.text import MIMEText
from pyzbar.pyzbar import decode
import cv2

DB_FILE = "attendance.db"

# ------------------ إعداد قاعدة البيانات ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS managers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT, last_name TEXT, code TEXT UNIQUE, email TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS parents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT, last_name TEXT, email TEXT, phone TEXT, password TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT, last_name TEXT, parent_id INTEGER, student_code TEXT UNIQUE,
        FOREIGN KEY(parent_id) REFERENCES parents(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER, date TEXT, status TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )""")
    conn.commit()
    conn.close()

# ------------------ إرسال بريد ------------------
def send_email(to, subject, body):
    print(f"[إيميل] إلى: {to}\nالموضوع: {subject}\n{body}\n")
    # هنا ممكن تربط SMTP حقيقي

# ------------------ التطبيق ------------------
class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("تطبيق الحضور والغياب")
        self.root.geometry("500x300")

        frame = ttk.Frame(root, padding=20)
        frame.pack(expand=True, fill="both")

        ttk.Label(frame, text="تطبيق تسجيل الحضور", font=("Helvetica", 16)).pack(pady=10)

        ttk.Button(frame, text="المدير", command=self.manager_login).pack(pady=10)
        ttk.Button(frame, text="الأولياء", command=self.parent_register).pack(pady=10)
        ttk.Button(frame, text="الحارس", command=self.guard_login).pack(pady=10)

    # ------------- المدير -------------
    def manager_login(self):
        win = tk.Toplevel(self.root)
        win.title("دخول المدير")
        win.geometry("400x250")
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="الاسم").pack()
        fname = ttk.Entry(frame)
        fname.pack()

        ttk.Label(frame, text="اللقب").pack()
        lname = ttk.Entry(frame)
        lname.pack()

        ttk.Label(frame, text="الإيميل").pack()
        email = ttk.Entry(frame)
        email.pack()

        ttk.Label(frame, text="كود المدير (أرقام)").pack()
        code = ttk.Entry(frame)
        code.pack()

        def save_manager():
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO managers(first_name,last_name,code,email) VALUES(?,?,?,?)",
                          (fname.get(), lname.get(), code.get(), email.get()))
                conn.commit()
                messagebox.showinfo("تم", "تم تسجيل المدير.")
            except sqlite3.IntegrityError:
                messagebox.showerror("خطأ", "الكود مستخدم بالفعل.")
            conn.close()

        ttk.Button(frame, text="تسجيل", command=save_manager).pack(pady=10)

    # ------------- الأولياء -------------
    def parent_register(self):
        win = tk.Toplevel(self.root)
        win.title("تسجيل ولي")
        win.geometry("400x350")
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        labels = ["اسم الولي", "لقب الولي", "الإيميل", "الهاتف", "كلمة السر"]
        entries = {}
        for lab in labels:
            ttk.Label(frame, text=lab).pack()
            ent = ttk.Entry(frame, show="*" if lab == "كلمة السر" else None)
            ent.pack()
            entries[lab] = ent

        def next_step():
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO parents(first_name,last_name,email,phone,password) VALUES(?,?,?,?,?)",
                      (entries["اسم الولي"].get(), entries["لقب الولي"].get(),
                       entries["الإيميل"].get(), entries["الهاتف"].get(),
                       entries["كلمة السر"].get()))
            pid = c.lastrowid
            conn.commit()
            conn.close()
            self.add_student(pid)

        ttk.Button(frame, text="التالي", command=next_step).pack(pady=10)

    def add_student(self, parent_id):
        win = tk.Toplevel(self.root)
        win.title("إضافة تلميذ")
        win.geometry("400x250")
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="اسم التلميذ").pack()
        fname = ttk.Entry(frame)
        fname.pack()
        ttk.Label(frame, text="لقب التلميذ").pack()
        lname = ttk.Entry(frame)
        lname.pack()

        def save_student():
            student_code = f"S{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO students(first_name,last_name,parent_id,student_code) VALUES(?,?,?,?)",
                      (fname.get(), lname.get(), parent_id, student_code))
            conn.commit()
            conn.close()

            # إنشاء QR
            qr = qrcode.make(student_code)
            qr.save(f"{student_code}.png")
            messagebox.showinfo("تم", f"تم تسجيل التلميذ.\nالكود: {student_code}\nتم إنشاء باركود وحفظه كصورة.")

        ttk.Button(frame, text="حفظ التلميذ", command=save_student).pack(pady=10)

    # ------------- الحارس -------------
    def guard_login(self):
        win = tk.Toplevel(self.root)
        win.title("دخول الحارس")
        win.geometry("300x200")
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="أدخل كود المدير").pack()
        code = ttk.Entry(frame)
        code.pack()

        def validate():
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT * FROM managers WHERE code=?", (code.get(),))
            if c.fetchone():
                self.open_guard_panel(code.get())
                win.destroy()
            else:
                messagebox.showerror("خطأ", "كود المدير غير صحيح")
            conn.close()

        ttk.Button(frame, text="دخول", command=validate).pack(pady=10)

    def open_guard_panel(self, manager_code):
        win = tk.Toplevel(self.root)
        win.title("واجهة الحارس")
        win.geometry("400x200")
        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="مرحبا بالحارس", font=("Helvetica",14)).pack(pady=8)

        def scan_qr():
            cap = cv2.VideoCapture(0)
            student_code = None
            messagebox.showinfo("تنبيه", "وجه الباركود نحو الكاميرا لمسحه.")
            while True:
                ret, frame_cam = cap.read()
                if not ret:
                    break
                for barcode in decode(frame_cam):
                    student_code = barcode.data.decode("utf-8")
                    cap.release()
                    cv2.destroyAllWindows()
                    self.register_guard_attendance(student_code, manager_code)
                    return
                cv2.imshow("مسح الباركود (اضغط q للخروج)", frame_cam)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cap.release()
            cv2.destroyAllWindows()

        ttk.Button(frame, text="مسح باركود", command=scan_qr).pack(pady=20)

    def register_guard_attendance(self, student_code, manager_code):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, first_name, last_name, parent_id FROM students WHERE student_code=?", (student_code,))
        row = c.fetchone()
        if not row:
            messagebox.showerror("خطأ","لم يتم العثور على التلميذ بهذا الباركود.")
            conn.close()
            return
        sid, sf, sl, pid = row
        today = datetime.date.today().isoformat()
        c.execute("INSERT INTO attendance(student_id, date, status) VALUES(?,?,?)", (sid, today, "present"))
        conn.commit()

        # إشعار المدير
        c.execute("SELECT email FROM managers WHERE code=?", (manager_code,))
        mgr = c.fetchone()
        if mgr and mgr[0]:
            subj = f"حضور {sf} {sl}"
            body = f"الحارس سجّل حضور التلميذ {sf} {sl} بتاريخ {today}."
            send_email(mgr[0], subj, body)

        # إشعار الولي
        if pid:
            c.execute("SELECT email FROM parents WHERE id=?", (pid,))
            pem = c.fetchone()
            if pem and pem[0]:
                subj = f"ابنك {sf} {sl} حاضر اليوم"
                body = f"تم تسجيل حضور ابنك {sf} {sl} بتاريخ {today}."
                send_email(pem[0], subj, body)

        conn.close()
        messagebox.showinfo("تم", f"تم تسجيل حضور {sf} {sl} وإرسال إشعار.")

# ------------------ تشغيل ------------------
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()
