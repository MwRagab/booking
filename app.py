import streamlit as st
import pandas as pd
import os
import time
import urllib.parse
import base64
from io import BytesIO
from streamlit_gsheets import GSheetsConnection
from sqlalchemy import text

# 1. إعدادات الصفحة
st.set_page_config(page_title="سنتر الأوائل - حجز المواعيد", page_icon="📚", layout="centered")

# 2. إنشاء الاتصالات بقواعد البيانات (جوجل شيت و PostgreSQL)
gsheets_conn = st.connection("gsheets", type=GSheetsConnection)
db_conn = st.connection("postgresql", type="sql", autocommit=True)

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

LOGO_FILE = "logo.png"
logo_base64 = get_base64_image(LOGO_FILE)
SCHEDULE_IMAGE = "جدول اولى copy.jpg"
WHATSAPP_NUMBER = "201024851696"

st.markdown("""
<style>
* { direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.stTextInput>div>div>input { text-align: right; }
.stAlert { direction: rtl; text-align: right; }
.subject-card { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #f0f2f6; }
.subject-title { color: #1e3d59; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #ff6e40; padding-bottom: 5px; display: inline-block; }
.ticket-card { background: linear-gradient(135deg, #1e3d59 0%, #2b5876 100%); color: white; padding: 25px; border-radius: 15px; margin-top: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.2); text-align: center; border: 2px dashed #ff6e40; position: relative; }
.ticket-card h2 { color: #ff6e40; margin-bottom: 5px; margin-top: 15px; }
.ticket-card p { font-size: 18px; margin: 5px 0; }
.ticket-item { background: rgba(255,255,255,0.1); margin: 10px 0; padding: 10px; border-radius: 8px; font-weight: bold; font-size: 17px; }
.logo-circle { background-color: white; border-radius: 50%; padding: 0px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
.logo-circle img { width: 100%; height: 100%; object-fit: contain; display: block; transform: scale(1.5) translateY(-2px); }
.marketing-card { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); color: #e65100; padding: 25px; border-radius: 15px; margin-top: 25px; border: 1px solid #ffb74d; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.marketing-card h3 { color: #d84315; margin-bottom: 5px; font-weight: bold; text-align: center; font-size: 22px; }
.marketing-card p { text-align: center; color: #5d4037; font-weight: bold; margin-bottom: 15px; font-size: 16px; }
.marketing-item { background: white; margin: 8px 0; padding: 10px 15px; border-radius: 8px; font-size: 15px; border-right: 5px solid #ff9800; color: #333; font-weight: bold; }
.whatsapp-btn { display: inline-block; background-color: #25D366; color: white !important; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-size: 18px; font-weight: bold; margin-top: 20px; text-align: center; width: 100%; box-shadow: 0 4px 6px rgba(37,211,102,0.3); transition: 0.3s; }
.whatsapp-btn:hover { background-color: #1ebe56; transform: translateY(-2px); }
</style>
""", unsafe_allow_html=True)

MULTI_SLOT = {
    "محمود قاسم": [{"slot": "الجمعة 08:00 (في انتظار المنهج)", "max": 85}, {"slot": "السبت 04:00 (في انتظار المنهج)", "max": 199}],
    "عبدالمجيد": [{"slot": "الإثنين 05:00 (البداية 08/17)", "max": 60}, {"slot": "الأحد 03:00 (البداية 08/16)", "max": 143}],
    "أحمد ربوشة": [{"slot": "الجمعة 01:30 (في انتظار المنهج)", "max": 127}, {"slot": "الجمعة 03:30 (في انتظار المنهج)", "max": 127}, {"slot": "السبت 12:30 (في انتظار المنهج)", "max": 126}],
    "أسامة رفعت": [{"slot": "الثلاثاء 05:00 (البداية 08/18)", "max": 91}, {"slot": "الخميس 03:00 (البداية 08/20)", "max": 90}],
    "سامي سمير": [{"slot": "الأربعاء 03:00 (البداية 08/26)", "max": 117}, {"slot": "الأحد 05:00 (البداية 08/30)", "max": 116}]
}

SINGLE_SLOT = {
    "علاء عبدالستار": "السبت 11:00 (البداية 08/15)", "ممدوح جاد": "الإثنين 01:00 (البداية 08/17)",
    "محمد عمر": "الثلاثاء 01:00 (البداية 08/25)", "عماد إبراهيم": "الأربعاء 03:00 (البداية 08/19)",
    "علا زهران": "الأربعاء 01:00 (البداية 08/19)", "محمد عبدالقادر": "الجمعة 11:00 (البداية 08/21)",
    "علاء جمال": "الجمعة 06:00 (البداية 08/21)", "محمد أبوهولة": "الجمعة 06:00 (البداية 08/21)",
    "محمود رفاعي": "الإثنين 03:00 (البداية 08/17)", "أماني منصور": "الثلاثاء 03:00 (في انتظار المنهج)",
    "محمد شكري": "الثلاثاء 08:00 (البداية 08/18)", "محمود صلاح": "جاري تحديد الميعاد",
    "محمد علي": "الأربعاء 05:00 (البداية 08/19)"
}

ALL_COURSES = {
    "اللغة العربية": "علاء عبدالستار (السبت 11ص) | ممدوح جاد (الإثنين 1م) | محمد عمر (الثلاثاء 1م) | عماد إبراهيم (الأربعاء 3م)",
    "اللغة الإنجليزية": "سامي سمير (الأربعاء 3م أو الأحد 5م)",
    "البرمجة": "علا زهران (الأربعاء 1م) | محمد عبدالقادر (الجمعة 11ص)",
    "اللغة الفرنسية": "علاء جمال (الجمعة 6م)",
    "اللغة الألمانية": "محمد أبوهولة (الجمعة 6م) | محمود رفاعي (الإثنين 3م)",
    "الرياضيات": "محمود قاسم (الجمعة 8ص أو السبت 4م)",
    "العلوم المتكاملة": "أحمد ربوشة (الجمعة أو السبت) | أماني منصور (الثلاثاء 3م)",
    "التاريخ": "أسامة رفعت (الثلاثاء 5م أو الخميس 3م)",
    "الفلسفة": "عبدالمجيد (الأحد 3م أو الإثنين 5م)",
    "علوم شرعية": "محمد شكري (الثلاثاء 8ص)",
    "INTEGRATED SCIENCE": "محمود صلاح (جاري التحديد)",
    "MATH": "محمد علي (الأربعاء 5م)"
}

# 3. دوال البيانات المُعدلة
@st.cache_data(ttl=60)
def load_main_data():
    df = gsheets_conn.read(worksheet="MainData")
    if not df.empty:
        df['كود الطالب'] = df['كود الطالب'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df['رقم التليفون'] = df['رقم التليفون'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    return df

def load_bookings():
    try:
        # قراءة الحجوزات لايف من قاعدة بيانات البوستجريس بدون كاش
        df = db_conn.query("SELECT * FROM bookings", ttl=0)
        df['كود الطالب'] = df['كود الطالب'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df['المدرس'] = df['المدرس'].astype(str).str.strip()
        return df
    except Exception as e:
        return pd.DataFrame(columns=["كود الطالب", "رقم التليفون", "اسم الطالب", "المادة", "المدرس", "الميعاد"])

def save_booking(new_data):
    # إدخال البيانات بسرعة وأمان لمنع التداخل بين الطلبة
    query = text('INSERT INTO bookings ("كود الطالب", "رقم التليفون", "اسم الطالب", "المادة", "المدرس", "الميعاد") VALUES (:code, :phone, :name, :subject, :teacher, :slot)')
    with db_conn.session as s:
        s.execute(query, {
            "code": new_data["كود الطالب"],
            "phone": new_data["رقم التليفون"],
            "name": new_data["اسم الطالب"],
            "subject": new_data["المادة"],
            "teacher": new_data["المدرس"],
            "slot": new_data["الميعاد"]
        })
        s.commit()
    st.cache_data.clear()

def convert_df_to_excel_sheets(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        grouped = df.groupby(['المدرس', 'الميعاد'])
        for (teacher, slot), group_df in grouped:
            clean_sheet_name = f"{teacher} - {slot[:15]}".replace(":", "-").replace("/", "-")
            group_df.to_excel(writer, sheet_name=clean_sheet_name[:31], index=False)
    return output.getvalue()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 4. لوحة الإدارة
with st.sidebar:
    if logo_base64:
        st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;">
<div class="logo-circle" style="width: 100px; height: 100px;">
<img src="data:image/png;base64,{logo_base64}" style="max-width: 100%; max-height: 100%;" /></div></div>""", unsafe_allow_html=True)
        
    st.markdown("### ⚙️ إدارة السنتر")
    admin_password = st.text_input("كلمة المرور", type="password")
    
    if admin_password == "1234":
        bookings_df = load_bookings()
        st.success("تسجيل الدخول ناجح")
        st.metric(label="إجمالي الحجوزات حتى الآن", value=len(bookings_df))
        
        st.markdown("---")
        st.markdown("### 📊 إحصائيات الأماكن المتبقية")
        
        stats_list = []
        for teacher, slots in MULTI_SLOT.items():
            for slot_info in slots:
                booked = len(bookings_df[(bookings_df['المدرس'] == teacher) & (bookings_df['الميعاد'] == slot_info['slot'])])
                rem = slot_info['max'] - booked
                stats_list.append({
                    "المدرس": teacher,
                    "الميعاد": slot_info['slot'].split("(")[0].strip(),
                    "الحد الأقصى": slot_info['max'],
                    "تم حجز": booked,
                    "متبقي": rem
                })
        
        if stats_list:
            stats_df = pd.DataFrame(stats_list)
            def highlight_zero(val):
                color = 'red' if val <= 5 else 'green'
                return f'color: {color}; font-weight: bold;'
            st.dataframe(stats_df.style.map(highlight_zero, subset=['متبقي']), use_container_width=True)

        st.markdown("---")
        if not bookings_df.empty:
            excel_data = convert_df_to_excel_sheets(bookings_df)
            st.download_button("📥 تحميل كشوفات المدرسين (Excel)", data=excel_data, file_name='مواعيد_المدرسين.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    elif admin_password != "":
        st.error("كلمة المرور خاطئة!")

# 5. واجهة الموقع
if logo_base64:
    st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;">
<div class="logo-circle" style="width: 130px; height: 130px;">
<img src="data:image/png;base64,{logo_base64}" style="max-width: 100%; max-height: 100%;" /></div></div>""", unsafe_allow_html=True)
    
st.markdown("<h1 style='text-align: center;'>🎓 سنتر الأوائل التعليمي</h1>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    st.markdown("##### برجاء إدخال بياناتك لعرض المواد واختيار المواعيد:")
    with st.form("login_form"):
        student_code = st.text_input("كود الطالب (بدون مسافات)").strip()
        phone_number = st.text_input("رقم تليفون ولي الأمر").strip()
        submit_btn = st.form_submit_button("دخول 🚀")
        
        if submit_btn:
            main_df = load_main_data()
            student_data = main_df[(main_df['كود الطالب'] == student_code) & (main_df['رقم التليفون'].str.lstrip('0') == phone_number.lstrip('0'))]
            
            if student_data.empty:
                st.error("❌ البيانات غير صحيحة، تأكد من الكود ورقم التليفون.")
            else:
                st.session_state.logged_in = True
                st.session_state.student_code = student_code
                st.session_state.student_phone = phone_number
                st.session_state.student_name = student_data.iloc[0]['اسم الطالب']
                st.session_state.student_data_rows = student_data
                st.rerun()
else:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"أهلاً بك يا {st.session_state.student_name} 👋")
    with col2:
        if st.button("تسجيل خروج 🚪"):
            st.session_state.logged_in = False
            st.rerun()
            
    tab1, tab2 = st.tabs(["📅 حجز مواعيدي", "🗓️ جدول السنتر الكامل"])
    
    with tab2:
        if os.path.exists(SCHEDULE_IMAGE):
            st.image(SCHEDULE_IMAGE, use_container_width=True)
        else:
            st.info("صورة الجدول غير متوفرة حالياً.")
            
    with tab1:
        bookings_df = load_bookings()
        student_data = st.session_state.student_data_rows
        
        total_subjects = len(student_data)
        booked_subjects_count = 0
        booked_details = []
        
        for index, row in student_data.iterrows():
            teacher = str(row['المدرس']).strip()
            subject = str(row['المادة']).strip()
            
            st.markdown(f"<div class='subject-card'>", unsafe_allow_html=True)
            st.markdown(f"<h3 class='subject-title'>{subject} | الأستاذ: {teacher}</h3>", unsafe_allow_html=True)
            
            already_booked = bookings_df[(bookings_df['كود الطالب'] == st.session_state.student_code) & (bookings_df['المدرس'] == teacher)]
            
            if not already_booked.empty:
                booked_slot = already_booked.iloc[0]['الميعاد']
                st.info(f"✅ تم تأكيد الميعاد: **{booked_slot}**")
                booked_subjects_count += 1
                booked_details.append(f"• {subject} ({teacher}): {booked_slot}")
            else:
                if teacher in SINGLE_SLOT:
                    st.write(f"📌 **الميعاد المخصص لك:** {SINGLE_SLOT[teacher]}")
                    if st.button(f"تأكيد ميعاد {subject} ✔️", key=f"btn_{teacher}"):
                        save_booking({"كود الطالب": st.session_state.student_code, "رقم التليفون": st.session_state.student_phone, "اسم الطالب": st.session_state.student_name, "المادة": subject, "المدرس": teacher, "الميعاد": SINGLE_SLOT[teacher]})
                        st.success(f"🎉 تم تأكيد حجز مادة {subject} بنجاح!")
                        time.sleep(1.5)
                        st.rerun()
                elif teacher in MULTI_SLOT:
                    available_slots = []
                    for slot_info in MULTI_SLOT[teacher]:
                        current_count = len(bookings_df[(bookings_df['المدرس'] == teacher) & (bookings_df['الميعاد'] == slot_info['slot'])])
                        if current_count < slot_info['max']:
                            available_slots.append(slot_info['slot'])
                    
                    if available_slots:
                        selected_slot = st.radio("اختر الميعاد المناسب لك:", available_slots, key=f"rad_{teacher}")
                        if st.button(f"تأكيد اختيار ميعاد {subject} ✔️", key=f"btn_{teacher}"):
                            save_booking({"كود الطالب": st.session_state.student_code, "رقم التليفون": st.session_state.student_phone, "اسم الطالب": st.session_state.student_name, "المادة": subject, "المدرس": teacher, "الميعاد": selected_slot})
                            st.success(f"🎉 تم تأكيد حجز مادة {subject} بنجاح!")
                            time.sleep(1.5)
                            st.rerun()
                    else:
                        st.error("عفواً، جميع المواعيد مكتملة العدد لهذا المدرس.")
                else:
                    st.warning(f"المدرس {teacher} غير مسجل في المواعيد حالياً.")
            st.markdown("</div>", unsafe_allow_html=True)

        if booked_subjects_count == total_subjects and total_subjects > 0:
            st.markdown("---")
            
            st.markdown("### 🎟️ جدولك الشخصي (احتفظ بصورة الشاشة)")
            
            logo_html_for_ticket = ""
            if logo_base64:
                logo_html_for_ticket = f"""<div style="text-align: center; margin-bottom: 10px;">
<div class="logo-circle" style="width: 80px; height: 80px; display: inline-flex;">
<img src="data:image/png;base64,{logo_base64}" style="max-width: 100%; max-height: 100%;" /></div></div>"""
                
            ticket_html = f"""<div class='ticket-card'>
{logo_html_for_ticket}
<h2>سنتر الأوائل التعليمي</h2>
<p>الطالب: <strong>{st.session_state.student_name}</strong></p>
<p>الكود: <strong>{st.session_state.student_code}</strong></p>
<hr style="border-top: 1px dashed white; margin: 15px 0;">
"""
            for detail in booked_details:
                ticket_html += f"<div class='ticket-item'>{detail}</div>"
            ticket_html += "</div>"
            st.markdown(ticket_html, unsafe_allow_html=True)
            
            student_subjects = [str(s).strip() for s in student_data['المادة'].unique()]
            missing_subjects = {k: v for k, v in ALL_COURSES.items() if k not in student_subjects}
            
            if missing_subjects:
                marketing_html = """<div class='marketing-card'>
<h3>🌟 بطل الأوائل مبيسيبش مادة للصدفة!</h3>
<p>مكانك دايماً في المقدمة، كمل جدولك دلوقتي واضمن تفوقك في باقي المواد:</p>
"""
                for subj, times in missing_subjects.items():
                    marketing_html += f"<div class='marketing-item'>📌 {subj}: {times}</div>"
                marketing_html += "</div>"
                st.markdown(marketing_html, unsafe_allow_html=True)

            whatsapp_msg = f"أهلاً، أنا الطالب {st.session_state.student_name}، كود: {st.session_state.student_code}.\nتم تأكيد حجزي في سنتر الأوائل بنجاح."
            encoded_msg = urllib.parse.quote(whatsapp_msg)
            whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded_msg}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank" class="whatsapp-btn">💬 إرسال تأكيد للإدارة عبر واتساب</a>', unsafe_allow_html=True)
