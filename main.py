import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup

# --- إعداد قاعدة البيانات في الهاتف ---
def init_db():
    conn = sqlite3.connect('aqsat_phone.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            total_amount REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            amount_paid REAL,
            payment_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

class AqsatPhoneApp(App):
    def build(self):
        init_db()
        self.selected_customer_id = None
        
        # الحاوية الرئيسية للتطبيق (عمودية لتناسب شاشة الهاتف)
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # عنوان التطبيق العلوي
        title = Label(text="نظام الأقساط الذكي للمحلات", font_size='20sp', size_hint_y=None, height=50, color=(1,1,1,1))
        self.main_layout.add_widget(title)
        
        # حقول الإدخال لإضافة زبون جديد
        input_layout = GridLayout(cols=2, spacing=5, size_hint_y=None, height=120)
        
        self.ent_name = TextInput(hint_text="اسم الزبون الجديد", halign='right', multiline=False)
        self.ent_phone = TextInput(hint_text="رقم الهاتف", halign='right', multiline=False)
        self.ent_total = TextInput(hint_text="المبلغ الكلي", halign='right', multiline=False)
        
        input_layout.add_widget(self.ent_name)
        input_layout.add_widget(self.ent_phone)
        input_layout.add_widget(self.ent_total)
        
        btn_add = Button(text="➕ إضافة زبون", background_color=(0.15, 0.68, 0.37, 1), font_size='16sp')
        btn_add.bind(on_press=self.add_customer)
        input_layout.add_widget(btn_add)
        
        self.main_layout.add_widget(input_layout)
        
        # قسم عرض قائمة الزبائن (Scrollable ليتنقل بالإصبع)
        self.main_layout.add_widget(Label(text="قائمة الزبائن (اضغط على الاسم لفتح صفحته):", size_hint_y=None, height=30, halign='right'))
        
        self.scroll_view = ScrollView()
        self.customer_list_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.customer_list_layout.bind(minimum_height=self.customer_list_layout.setter('height'))
        self.scroll_view.add_widget(self.customer_list_layout)
        
        self.main_layout.add_widget(self.scroll_view)
        
        self.load_customers()
        return self.main_layout

    def load_customers(self):
        self.customer_list_layout.clear_widgets()
        conn = sqlite3.connect('aqsat_phone.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers")
        rows = cursor.fetchall()
        
        for row in rows:
            c_id, name, phone, total = row
            cursor.execute("SELECT SUM(amount_paid) FROM payments WHERE customer_id=?", (c_id,))
            paid = cursor.fetchone()[0] or 0.0
            remaining = total - paid
            
            # نص يظهر معلومات الزبون كأنه كارت مالي
            btn_text = f"الاسم: {name} | المتبقي: {remaining} | الكلي: {total}"
            btn = Button(text=btn_text, size_hint_y=None, height=60, background_color=(0.17, 0.24, 0.31, 1))
            # ربط الضغط بفتح الصفحة الخاصة بالزبون
            btn.bind(on_press=lambda instance, x=c_id, n=name, r=remaining: self.open_customer_profile(x, n, r))
            self.customer_list_layout.add_widget(btn)
            
        conn.close()

    def add_customer(self, instance):
        name = self.ent_name.text.strip()
        phone = self.ent_phone.text.strip()
        total = self.ent_total.text.strip()
        
        if not name or not total:
            return
        
        try:
            total_val = float(total)
        except ValueError:
            return
            
        conn = sqlite3.connect('aqsat_phone.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO customers (name, phone, total_amount) VALUES (?, ?, ?)", (name, phone, total_val))
        conn.commit()
        conn.close()
        
        self.ent_name.text = ""
        self.ent_phone.text = ""
        self.ent_total.text = ""
        self.load_customers()

    # --- نافذة الصفحة الخاصة بالزبون (Popup مخصص للهاتف) ---
    def open_customer_profile(self, customer_id, name, remaining):
        self.selected_customer_id = customer_id
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=f"الزبون: {name}\nالمتبقي بذمته: {remaining}", halign='center', font_size='16sp'))
        
        # حقل إدخال دفعة جديدة
        self.ent_pay = TextInput(hint_text="أدخل مبلغ الدفعة الحالية هنا", halign='center', multiline=False, size_hint_y=None, height=50)
        content.add_widget(self.ent_pay)
        
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        btn_save = Button(text="💵 حفظ الدفعة", background_color=(0.16, 0.5, 0.73, 1))
        btn_save.bind(on_press=lambda instance: self.add_payment(customer_id, popup))
        
        btn_layout.add_widget(btn_save)
        content.add_widget(btn_layout)
        
        # عرض سجل الدفعات السابقة داخل صفحة الزبون
        content.add_widget(Label(text="سجل الدفعات السابقة لهذا الشخص:", size_hint_y=None, height=25))
        pay_scroll = ScrollView()
        pay_grid = GridLayout(cols=1, spacing=3, size_hint_y=None)
        pay_grid.bind(minimum_height=pay_grid.setter('height'))
        
        conn = sqlite3.connect('aqsat_phone.db')
        cursor = conn.cursor()
        cursor.execute("SELECT amount_paid, payment_date FROM payments WHERE customer_id=?", (customer_id,))
        p_rows = cursor.fetchall()
        
        for idx, p_row in enumerate(p_rows, start=1):
            amt, dt = p_row
            pay_grid.add_widget(Label(text=f"دفعة {idx}: {amt} في {dt}", size_hint_y=None, height=30, font_size='12sp'))
        conn.close()
        
        pay_scroll.add_widget(pay_grid)
        content.add_widget(pay_scroll)
        
        popup = Popup(title="الصفحة الخاصة بالزبون والأقساط", content=content, size_hint=(0.9, 0.9))
        popup.open()

    def add_payment(self, customer_id, popup):
        pay_amt = self.ent_pay.text.strip()
        if not pay_amt:
            return
            
        try:
            pay_val = float(pay_amt)
        except ValueError:
            return
            
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        conn = sqlite3.connect('aqsat_phone.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO payments (customer_id, amount_paid, payment_date) VALUES (?, ?, ?)", 
                       (customer_id, pay_val, current_date))
        conn.commit()
        conn.close()
        
        popup.dismiss()
        self.load_customers()

if __name__ == '__main__':
    AqsatPhoneApp().run()