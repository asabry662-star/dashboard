import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from pyairtable import Table

# ----------------------------------------------
# 1. إعدادات الصفحة والتصميم (CSS Customization)
# ----------------------------------------------

# الألوان للهوية البصرية (تم تثبيتها لألوان Streamlit القياسية مع تباين جيد)
PRIMARY_COLOR = "#004d99"  # أزرق داكن (للعناوين والحدود)
SUCCESS_COLOR = "#28a745"  # أخضر (للأداء الإيجابي)
WARNING_COLOR = "#dc3545"  # أحمر (للأداء السلبي/المتأخر)
ACCENT_COLOR = "#007bff"   # أزرق فاتح (للقيم الرئيسية)
BACKGROUND_COLOR = "#f0f2f6" # خلفية فاتحة موحدة

st.set_page_config(layout="wide", page_title="نظام متابعة أداء عقود التشغيل والصيانة", initial_sidebar_state="expanded")

# تطبيق CSS مخصص ليتوافق مع التصميم المطلوب
# تم تحسين الأنماط لتطبيق تأثير بطاقات (Cards) أفضل واستخدام خط 'Tajawal'
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
    
    html, body, [class*="st-"] {{ 
        font-family: 'Tajawal', sans-serif; 
        direction: rtl; /* لضمان الدعم الكامل للغة العربية */
        text-align: right;
    }}
    .stApp {{ background-color: {BACKGROUND_COLOR}; }}
    
    /* إعدادات الشريط الجانبي */
    .st-emotion-cache-1cypcdb {{ /* Streamlit sidebar header */
        color: {PRIMARY_COLOR};
    }}
    
    /* تصميم بطاقات KPI بشكل بارز ومحدّث */
    div.st-emotion-cache-k7vsyb, div.st-emotion-cache-1r6r8u, div[data-testid*="stMetric"] {{ 
        background-color: #ffffff;
        border-radius: 12px; /* زوايا مستديرة أكثر */
        padding: 20px; /* مساحة داخلية أكبر */
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1); /* ظل أفضل */
        border-right: 5px solid {PRIMARY_COLOR}; /* شريط جانبي بلون رئيسي */
        margin-bottom: 20px;
        min-height: 100px; /* لضمان اتساق ارتفاع البطاقات */
    }}
    
    /* قيم المؤشرات الرئيسية */
    [data-testid="stMetricValue"] {{ 
        color: {ACCENT_COLOR}; 
        font-size: 2.2em; 
        font-weight: 700;
        text-align: right;
    }}
    
    /* تسمية المؤشرات */
    [data-testid="stMetricLabel"] {{ 
        color: #6c757d; 
        font-size: 1em; 
        font-weight: 400;
        text-align: right;
    }}
    
    /* الانحراف (Delta) */
    .css-1b4z8g7 div:first-child {{ 
        color: {WARNING_COLOR} !important; /* لون الانحراف السلبي */
    }} 
    .css-1f2wzrg div:first-child {{ 
        color: {SUCCESS_COLOR} !important; /* لون الانحراف الإيجابي */
    }}

    /* تصميم البطاقة المجمعة (لتقييم المقاول) */
    .combined-card {{
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        border-right: 5px solid {PRIMARY_COLOR};
        margin-bottom: 20px;
        height: 100%;
    }}
    .combined-card h4 {{
        color: {PRIMARY_COLOR};
        font-weight: 700;
        border-bottom: 2px solid #eee;
        padding-bottom: 10px;
        margin-top: 0;
        margin-bottom: 15px;
    }}
    
    /* تعديل تصميم أزرار الراديو (للتنقل) */
    .st-emotion-cache-1r4y5p7 {{
        padding: 10px 0;
        border-radius: 8px;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }}
    .st-emotion-cache-1r4y5p7 label {{
        padding: 8px 15px;
        font-weight: 700;
        color: {PRIMARY_COLOR};
    }}
    
    /* نمط التحذير (لرسالة "يرجى اختيار تصنيف") */
    div[data-testid="stAlert"] {{
        border-right: 10px solid #ffc107;
        border-left: none;
    }}
    
    /* عناوين الصفحات */
    h1 {{ 
        color: {PRIMARY_COLOR}; 
        font-weight: 900;
        text-align: right;
        border-bottom: 3px solid {ACCENT_COLOR};
        padding-bottom: 10px;
        margin-bottom: 20px;
    }}
    
    </style>
    """, unsafe_allow_html=True)

# ----------------------------------------------
# 2. تعريف خريطة الأعمدة (متغير عام)
# ----------------------------------------------

# القائمة الكاملة لإعادة التسمية - تم نقلها هنا لتكون متاحة عالمياً
COLUMN_MAP = {
    # الأعمدة الأساسية
    'عقد رقم': 'Contract_ID', 'تاريخ التقرير': 'Report_Date', 'المقاول': 'Contractor',
    'الإستشاري': 'Consultant', 'المهندس المشرف': 'Supervisor_Engineer', 'المشروع': 'Project_Name',
    'التصنيف (انارة - طرق )': 'Category', 'المحور': 'Axis', 
    'مدة العقد': 'Contract_Duration', 'عدد الايام المتبقية': 'Remaining_Days',
    'التقييم العام للمقاول': 'Contractor_Overall_Score',
    'تاريخ بداية المشروع': 'Start_Date', 'تاريخ نهاية المشروع': 'End_Date', 
    'حاله المشروع': 'Project_Overall_Status',
    
    # الأعمدة المالية والزمنية والنسب المئوية
    'نسبة الانجاز المستهدفه': 'Target_Completion_Rate',
    'نسبة الانجاز الفعلية': 'Actual_Completion_Rate', 'نسبة المدة المنقضية': 'Elapsed_Time_Rate',
    'نسبة الإنحراف الفعلية': 'Actual_Deviation_Rate', 
    'مؤشر أداء المقاول حسب الاوزان المستهدف': 'Target_Weighted_Index',
    'مؤشر أداء المقاول حسب الاوزان الفعلى': 'Actual_Weighted_Index', 
    'قيمة العقد (ريال)': 'Total_Contract_Value',
    'المنفذ فعلياً (نسبة الإنجاز)': 'Actual_Financial_Value', 
    'القيمة المخطط لها': 'Target_Financial_Value',
    'الإنحراف عن التكلفة (CV)': 'Delayed_Financial_Value',
    'مؤشر أداء البرناج الزمني': 'SPI',
    
    # مؤشرات التقييم الفرعية (Scores)
    'السلامة والصحة المهنية': 'HSE_Score', 'التواصل والاستجابة': 'Communication_Score',
    'تحقيق المستهدفات': 'Target_Achievement_Score', 'الجودة': 'Quality_Score',
    
    # مؤشرات الطرق (التراكمي / الشهري)
    'مؤشر أداء الفرقة الرئيسية التراكمي المستهدف': 'FR_Cum_Target', 'مؤشر أداء الفرقة الرئيسية التراكمي الفعلى': 'FR_Cum_Actual',
    'مؤشر أداء الفرقة الرئيسية الشهري المستهدف': 'FR_Monthly_Target', 'مؤشر أداء الفرقة الرئيسية الشهري الفعلى': 'FR_Monthly_Actual',
    
    'مؤشر أداء المعاملات التراكمي المستهدف': 'Trans_Cum_Target', 'مؤشر أداء المعاملات التراكمي الفعلى': 'Trans_Cum_Actual',
    'مؤشر أداء المعاملات الشهري المستهدف': 'Trans_Monthly_Target', 'مؤشر أداء المعاملات الشهري الفعلى': 'Trans_Monthly_Actual',
    
    'مؤشر أداء الأرصفة التراكمي المستهدف': 'Pave_Cum_Target', 'مؤشر أداء الأرصفة التراكمي الفعلى': 'Pave_Cum_Actual',
    'مؤشر أداء الأرصفة الشهري المستهدف': 'Pave_Monthly_Target', 'مؤشر أداء الأرصفة الشهري الفعلى': 'Pave_Monthly_Actual',
    
    'مؤشر أداء الدهانات التراكمي المستهدف': 'Paint_Cum_Target', 'مؤشر أداء الدهانات التراكمي الفعلى': 'Paint_Cum_Actual',
    'مؤشر أداء الدهانات الشهري المستهدف': 'Paint_Monthly_Target', 'مؤشر أداء الدهانات الشهري الفعلى': 'Paint_Monthly_Actual',
    
    'مؤشر أداء السلامة المرورية التراكمي المستهدف': 'Traffic_Cum_Target', 'مؤشر أداء السلامة المرورية التراكمي الفعلى': 'Traffic_Cum_Actual',
    'مؤشر أداء السلامة المرورية الشهري المستهدف': 'Traffic_Monthly_Target', 'مؤشر أداء السلامة المرورية الشهري الفعلى': 'Traffic_Monthly_Actual',
    
    'مؤشر أداء الطوارئ التراكمي المستهدف': 'Emergency_Cum_Target', 'مؤشر أداء الطوارئ التراكمي الفعلى': 'Emergency_Cum_Actual',
    'مؤشر أداء الطوارئ الشهري المستهدف': 'Emergency_Monthly_Target', 'مؤشر أداء الطوارئ الشهري الفعلى': 'Emergency_Monthly_Actual',
    
    'مؤشر غسيل الدهانات التراكمي المستهدف': 'Wash_Cum_Target', 'مؤشر غسيل الدهانات التراكمي الفعلى': 'Wash_Cum_Actual',
    'مؤشر غسيل الدهانات الشهري المستهدف': 'Wash_Monthly_Target', 'مؤشر غسيل الدهانات الشهري الفعلى': 'Wash_Monthly_Actual',
    
    'موشر اعمال أخرى تراكمي المستهدف': 'Other_Cum_Target', 'موشر اعمال أخرى تراكمي الفعلى': 'Other_Cum_Actual',
    'موشر اعمال أخرى الشهري المستهدف': 'Other_Monthly_Target', 'موشر اعمال أخرى الشهري الفعلى': 'Other_Monthly_Actual',

    # مؤشرات دورات الحفر (Holes)
    'نسبة دورة الحفر 01': 'Hole_Rate_01', 'نسبة خصم دورة الحفر 01': 'Hole_Discount_01',
    'نسبة دورة الحفر 02': 'Hole_Rate_02', 'نسبة خصم دورة الحفر 02': 'Hole_Discount_02',
    'نسبة دورة الحفر 03': 'Hole_Rate_03', 'نسبة خصم دورة الحفر 03': 'Hole_Discount_03',
    'نسبة دورة الحفر 04': 'Hole_Rate_04', 'نسبة خصم دورة الحفر 04': 'Hole_Discount_04',
    'نسبة دورة الحفر 05': 'Hole_Rate_05', 'نسبة خصم دورة الحفر 05': 'Hole_Discount_05',
    'نسبة دورة الحفر 06': 'Hole_Rate_06', 'نسبة خصم دورة الحفر 06': 'Hole_Discount_06',
    'نسبة دورة الحفر 07': 'Hole_Rate_07', 'نسبة خصم دورة الحفر 07': 'Hole_Discount_07',
    'نسبة دورة الحفر 08': 'Hole_Rate_08', 'نسبة خصم دورة الحفر 08': 'Hole_Discount_08',
    'نسبة دورة الحفر 09': 'Hole_Rate_09', 'نسبة خصم دورة الحفر 09': 'Hole_Discount_09',
    'نسبة دورة الحفر 10': 'Hole_Rate_10', 'نسبة خصم دورة الحفر 10': 'Hole_Discount_10',
    'نسبة دورة الحفر 11': 'Hole_Rate_11', 'نسبة خصم دورة الحفر 11': 'Hole_Discount_11',
    'نسبة دورة الحفر 12': 'Hole_Rate_12', 'نسبة خصم دورة الحفر 12': 'Hole_Discount_12',

    # مؤشرات الإنارة (التفصيلية)
    'استبدال وتوريد أعمدة الإنارة - تراكمي مستهدف': 'L_Rep_Col_Target', 
    'استبدال وتوريد أعمدة الإنارة - تراكمي فعلي': 'L_Rep_Col_Actual',
    'استبدال وتوريد أعمدة الإنارة - شهري مستهدف': 'L_Rep_Col_Monthly_Target', 
    'استبدال وتوريد أعمدة الإنارة - شهري فعلي': 'L_Rep_Col_Monthly_Actual',
    'صيانة أعمدة الإنارة - تراكمي مستهدف': 'L_Maint_Col_Target', 
    'صيانة أعمدة الإنارة - تراكمي فعلي': 'L_Maint_Col_Actual',
    'صيانة أعمدة الإنارة - شهري مستهدف': 'L_Maint_Col_Monthly_Target', 
    'صيانة أعمدة الإنارة - شهري فعلي': 'L_Maint_Col_Monthly_Actual',
    'صيانة وتوريد علب الفيوزات - تراكمي مستهدف': 'L_Fuse_Target', 
    'صيانة وتوريد علب الفيوزات - تراكمي فعلي': 'L_Fuse_Actual',
    'صيانة وتوريد علب الفيوزات - شهري مستهدف': 'L_Fuse_Monthly_Target', 
    'صيانة وتوريد علب الفيوزات - شهري فعلي': 'L_Fuse_Monthly_Actual',
    'صيانة وتوريد فوانيس الإنارة - تراكمي مستهدف': 'L_Lantern_Target', 
    'صيانة وتوريد فوانيس الإنارة - تراكمي فعلي': 'L_Lantern_Actual',
    'صيانة وتوريد فوانيس الإنارة - شهري مستهدف': 'L_Lantern_Monthly_Target', 
    'صيانة وتوريد فوانيس الإنارة - شهري فعلي': 'L_Lantern_Monthly_Actual',
    'صيانة وتوريد أذرع أعمدة الإنارة - تراكمي مستهدف': 'L_Arm_Target', 
    'صيانة وتوريد أذرع أعمدة الإنارة - تراكمي فعلي': 'L_Arm_Actual',
    'صيانة وتوريد أذرع أعمدة الإنارة - شهري مستهدف': 'L_Arm_Monthly_Target', 
    'صيانة وتوريد أذرع أعمدة الإنارة - شهري فعلي': 'L_Arm_Monthly_Actual',
    'صيانة لوحات توزيع الإنارة - تراكمي مستهدف': 'L_Board_Target', 
    'صيانة لوحات توزيع الإنارة - تراكمي فعلي': 'L_Board_Actual',
    'صيانة لوحات توزيع الإنارة - شهري مستهدف': 'L_Board_Monthly_Target', 
    'صيانة لوحات توزيع الإنارة - شهري فعلي': 'L_Board_Monthly_Actual',
    'توريد وتمديد كوابل أرضية - تراكمي مستهدف': 'L_Cable_Target', 
    'توريد وتمديد كوابل أرضية - تراكمي فعلي': 'L_Cable_Actual',
    'توريد وتمديد كوابل أرضية - شهري مستهدف': 'L_Cable_Monthly_Target', 
    'توريد وتمديد كوابل أرضية - شهري فعلي': 'L_Cable_Monthly_Actual',
} 
# إنشاء الخريطة العكسية لاستخدامها في العرض
REVERSE_COLUMN_MAP = {v: k for k, v in COLUMN_MAP.items()}


# قراءة مفاتيح Airtable من Streamlit Secrets
try:
    # سيتم تشغيل هذا الكود فقط في البيئة التي تحتوي على Secrets
    # في حال لم تكن متاحة، سيتم التعامل معها كـ DataFrame فارغة
    AIRTABLE_API_KEY = st.secrets["airtable"]["api_key"]
    AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
    AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
except KeyError:
    # وضع قيم وهمية لتمكين التشغيل إذا لم تتوفر مفاتيح Secrets
    AIRTABLE_API_KEY = "DUMMY_KEY"
    AIRTABLE_BASE_ID = "DUMMY_BASE"
    AIRTABLE_TABLE_NAME = "DUMMY_TABLE"
    st.error("خطأ: لم يتم العثور على مفاتيح Airtable (api_key, base_id, table_name) في Streamlit Secrets. سيتم عرض بيانات وهمية أو فارغة.")


@st.cache_data(ttl=600) # تخزين مؤقت للبيانات لمدة 10 دقائق
def load_and_process_data():
    try:
        if AIRTABLE_API_KEY == "DUMMY_KEY":
            # في بيئة التطوير/الاختبار حيث لا تتوفر Secrets، نرجع DataFrame فارغة لتجنب الانهيار
            return pd.DataFrame(), pd.DataFrame() 
            
        # 1. الاتصال بـ Airtable وجلب البيانات
        table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
        records = table.all()
        
        # 2. تحويل البيانات إلى DataFrame
        data = [record['fields'] for record in records]
        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"حدث خطأ أثناء جلب البيانات من Airtable. (هل المفاتيح والصلاحيات صحيحة؟): {e}")
        return pd.DataFrame(), pd.DataFrame() 

    # ------------------ بدء منطق المعالجة ------------------
    
    # خطوة التنظيف: تنظيف أسماء الأعمدة الموجودة في DataFrame
    df.columns = df.columns.str.replace(r'\s+', ' ', regex=False).str.strip()
    
    # 3. إعادة التسمية بشكل آمن (فقط للأعمدة الموجودة)
    rename_dict = {col_ar: col_en for col_ar, col_en in COLUMN_MAP.items() if col_ar in df.columns}
    df.rename(columns=rename_dict, inplace=True)
    
    # ------------------ معالجة الأخطاء ------------------
    
    # الأعمدة المطلوبة لضمان عدم الانهيار في أي صفحة
    REQUIRED_COLS = [
        'Actual_Financial_Value', 'Target_Financial_Value', 'Total_Contract_Value',
        'Delayed_Financial_Value', 
        'Actual_Completion_Rate', 'Target_Completion_Rate', 'Actual_Deviation_Rate', 
        'Contract_ID', 'Report_Date', 'Category', 'Contract_Duration', 'Elapsed_Time_Rate',
        'Contractor_Overall_Score', 'HSE_Score', 'Communication_Score', 'Target_Achievement_Score', 'Quality_Score',
        'Axis', 'Supervisor_Engineer', 'Contractor'
    ]
    
    # إضافة الأعمدة المفقودة بقيم صفرية أو افتراضية لمنع الـ KeyError
    for col in REQUIRED_COLS:
        if col not in df.columns:
            if 'Rate' in col or 'Value' in col or 'Score' in col or 'Duration' in col:
                 df[col] = 0.0
            elif col == 'Category':
                 df[col] = 'غير محدد'
            elif 'Date' in col:
                 df[col] = pd.NaT 
            else:
                 df[col] = 'غير معلوم' if col in ['Axis', 'Supervisor_Engineer', 'Contractor'] else 0
    
    # ملء القيم المفقودة في عمود التصنيف لعدم كسر الفلتر
    df['Category'].fillna('غير محدد', inplace=True)
        
    # 4. تحويل التواريخ
    date_cols = ['Report_Date', 'Start_Date', 'End_Date']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 5. تحويل النسب المئوية
    rate_cols_to_process = [
        col for col in df.columns 
        if ('Rate' in col or 'Target' in col or 'Actual' in col or 'Cum' in col or 'Monthly' in col) 
        and ('Score' not in col) and ('Hole_Discount' not in col) and ('_ID' not in col) and ('Value' not in col)
    ]
    for col in rate_cols_to_process:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) / 100

    # 6. تنظيف وتحويل القيم المالية والـ Scores
    financial_cols = ['Total_Contract_Value', 'Actual_Financial_Value', 'Target_Financial_Value', 'Delayed_Financial_Value']
    score_cols = ['HSE_Score', 'Communication_Score', 'Target_Achievement_Score', 'Quality_Score', 'Contractor_Overall_Score']
    
    for col in financial_cols + score_cols:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False).apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # ------------------ الحسابات المتقدمة ------------------
    def get_deviation_status(rate):
        if pd.isna(rate): return 'غير معلوم'
        if rate >= 0.05: return 'متقدم'
        elif rate <= -0.05: return 'متأخر'
        else: return 'مطابق'
    
    # حساب الحالة بناءً على الانحراف
    df['Project_Deviation_Status'] = df['Actual_Deviation_Rate'].apply(get_deviation_status)
        
    # استخلاص آخر تقرير لكل عقد
    latest_reports = pd.DataFrame() 
    if not df.empty and 'Report_Date' in df.columns and 'Contract_ID' in df.columns:
        latest_reports = df.loc[df.groupby('Contract_ID')['Report_Date'].idxmax()]
    else:
        latest_reports = df.copy() 

    # التأكد من عدم إرجاع قيم NaN بدلاً من DataFrame فارغة في حالة الفشل
    return df, latest_reports

# استدعاء الدالة
df, latest_reports_df = load_and_process_data()

if df.empty:
    st.info("لا توجد بيانات للعرض. يرجى التأكد من إعداد Airtable Secrets بشكل صحيح.")
    if AIRTABLE_API_KEY == "DUMMY_KEY":
        st.markdown("**ملاحظة:** يرجى التأكد من توفير مفاتيح Airtable في Streamlit Secrets للتحميل الفعلي للبيانات.")
    st.stop()


# ----------------------------------------------
# 3. واجهة الفلاتر (Interface Filters)
# ----------------------------------------------

# تم تعديل هذه الدالة لإرجاع قائمة التصنيفات التي اختارها المستخدم أيضاً
def filter_sidebar(df):
    st.sidebar.header("تصفية البيانات")

    # قائمة الفلاتر المطلوبة
    # استخدام خيار "الكل" كخيار افتراضي لتحسين UX
    axis_options = ['الكل'] + df['Axis'].dropna().unique().tolist() if 'Axis' in df.columns else []
    supervisor_options = ['الكل'] + df['Supervisor_Engineer'].dropna().unique().tolist() if 'Supervisor_Engineer' in df.columns else []
    # هنا لا نستخدم 'الكل' لفرض اختيار واحد أو لا شيء في صفحة التحليل التفصيلي
    category_options = df[df['Category'] != 'غير محدد']['Category'].dropna().unique().tolist() if 'Category' in df.columns else []
    contract_options = ['الكل'] + df['Contract_ID'].dropna().unique().tolist() if 'Contract_ID' in df.columns else []
    
    selected_axis = st.sidebar.multiselect("المحور:", options=axis_options, default='الكل')
    selected_supervisor = st.sidebar.multiselect("المهندس المشرف:", options=supervisor_options, default='الكل')
    # الاحتفاظ بقائمة التصنيفات التي اختارها المستخدم
    selected_category = st.sidebar.multiselect("التصنيف:", options=category_options) 
    selected_contract = st.sidebar.multiselect("رقم العقد:", options=contract_options, default='الكل')
    
    status_options = ['متقدم', 'متأخر', 'مطابق', 'غير معلوم']
    selected_status = st.sidebar.multiselect("حالة المشروع:", options=status_options)
    
    # فلتر التاريخ
    start_date = pd.Timestamp.min
    end_date = pd.Timestamp.max
    date_range = None
    if 'Report_Date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Report_Date']) and not df['Report_Date'].empty:
        min_date = df['Report_Date'].min().date() if not df['Report_Date'].min() is pd.NaT else pd.to_datetime('2020-01-01').date()
        max_date = df['Report_Date'].max().date() if not df['Report_Date'].max() is pd.NaT else pd.to_datetime('2025-12-31').date()
        
        if min_date <= max_date:
            date_range = st.sidebar.slider(
                "تاريخ التقرير:",
                min_value=min_date, max_value=max_date,
                value=(min_date, max_date), format="YYYY/MM/DD"
            )
            start_date = pd.to_datetime(date_range[0])
            end_date = pd.to_datetime(date_range[1])

    # تطبيق الفلاتر
    df_filtered = df.copy()
    
    # تطبيق الفلاتر (تجاهل 'الكل' في الفلترة)
    if selected_axis and 'الكل' not in selected_axis: df_filtered = df_filtered[df_filtered['Axis'].isin(selected_axis)]
    if selected_supervisor and 'الكل' not in selected_supervisor: df_filtered = df_filtered[df_filtered['Supervisor_Engineer'].isin(selected_supervisor)]
    if selected_category: df_filtered = df_filtered[df_filtered['Category'].isin(selected_category)]
    if selected_contract and 'الكل' not in selected_contract: df_filtered = df_filtered[df_filtered['Contract_ID'].isin(selected_contract)]
    if selected_status: df_filtered = df_filtered[df_filtered['Project_Deviation_Status'].isin(selected_status)]
    
    if date_range:
        df_filtered = df_filtered[(df_filtered['Report_Date'] >= start_date) & (df_filtered['Report_Date'] <= end_date)]
    
    # إرجاع كل من DataFrame المفلتر وقائمة التصنيفات المختارة
    return df_filtered, selected_category

# ----------------------------------------------
# 4. بناء الصفحات والتنقل
# ----------------------------------------------

PAGES = {
    "1. ملخص تنفيذي (KPIs)": "executive_summary",
    "2. تحليل تفصيلي (الأداء التخصصي)": "detailed_analysis",
    "3. عرض كامل التفاصيل": "raw_data_view"
}

st.sidebar.title("التنقل في لوحة التحكم")
selection = st.sidebar.radio("اختر الصفحة:", list(PAGES.keys()))
page = PAGES[selection]

# ----------------------------------------------------
# -------------------- صفحة الملخص التنفيذي --------------------
# ----------------------------------------------------

if page == "executive_summary":
    st.title("ملخص تنفيذي: المؤشرات الرئيسية")
    
    # هنا لا نحتاج قائمة التصنيفات، نستقبل DataFrame فقط
    filtered_df, _ = filter_sidebar(df)
    
    # تجميع البيانات الأخيرة بعد الفلترة
    if not filtered_df.empty and 'Report_Date' in filtered_df.columns:
        filtered_latest_df = filtered_df.loc[filtered_df.groupby('Contract_ID')['Report_Date'].idxmax()]
    else:
        st.warning("لا توجد بيانات مطابقة لمعايير الفلترة الحالية.")
        st.stop()

    # 1. حساب المؤشرات المطلوبة
    total_projects = filtered_latest_df['Contract_ID'].nunique()
    
    avg_actual_completion = filtered_latest_df['Actual_Completion_Rate'].fillna(0).mean() * 100
    avg_target_completion = filtered_latest_df['Target_Completion_Rate'].fillna(0).mean() * 100
    total_target_value = filtered_latest_df['Target_Financial_Value'].fillna(0).sum() / 1000000
    total_actual_value = filtered_latest_df['Actual_Financial_Value'].fillna(0).sum() / 1000000
    avg_overall_score = filtered_latest_df['Contractor_Overall_Score'].fillna(0).mean()

    # 2. عرض المؤشرات في بطاقات (KPI Cards)
    
    # --- الصف الأول: بطاقة الوقت والمشاريع ---
    st.subheader("إجمالي الوضع العام والمشاريع", anchor=False)
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("إجمالي عدد المشاريع", f"{total_projects}")
    col2.metric("متوسط المدة المنقضية", f"{filtered_latest_df['Elapsed_Time_Rate'].fillna(0).mean() * 100:.1f}%")
    col3.metric("متوسط مدة العقد (أيام)", f"{filtered_latest_df['Contract_Duration'].fillna(0).mean():.0f}")
    
    status_counts = filtered_latest_df['Project_Deviation_Status'].value_counts()
    late_count = status_counts.get('متأخر', 0)
    col4.metric("المشاريع المتأخرة", f"{late_count}", delta_color='inverse', delta=f"من أصل {total_projects}")

    st.divider()
    
    # --- الصف الثاني: بطاقة نسب الإنجاز وحالة المشروع ---
    st.subheader("ملخص الإنجاز والمسار الزمني", anchor=False)
    col5, col6, col7 = st.columns(3)
    
    col5.metric("متوسط الإنجاز المخطط", f"{avg_target_completion:.1f}%")
    col6.metric("متوسط الإنجاز الفعلي", f"{avg_actual_completion:.1f}%", 
                delta=f"{avg_actual_completion - avg_target_completion:.1f}%")
    
    avg_dev = filtered_latest_df['Actual_Deviation_Rate'].fillna(0).mean() * 100
    col7.metric("متوسط الانحراف الكلي", f"{avg_dev:.1f}%", 
                delta_color='inverse', delta=f"{avg_dev:.1f}%")
    
    st.divider()

    # --- الصف الثالث: بطاقة القيمة المالية ---
    st.subheader("ملخص القيمة المالية (مليون ريال)", anchor=False)
    col8, col9, col10 = st.columns(3)

    col8.metric("إجمالي القيمة المخططة", f"{total_target_value:,.2f}M")
    col9.metric("إجمالي القيمة الفعلية", f"{total_actual_value:,.2f}M")
    deviation_val = total_actual_value - total_target_value
    col10.metric("الانحراف المالي الكلي", f"{deviation_val:,.2f}M", 
                delta=f"{deviation_val:,.2f}M", delta_color='inverse')

    st.divider()

    # --- الصف الرابع: بطاقة تقييم المقاول المجمعة مع مخطط بياني ---
    st.subheader("تقييم الأداء والمقاول", anchor=False)
    col11, col12 = st.columns([1, 2])
    
    # حساب متوسط درجات المقاول
    score_cols = ['HSE_Score', 'Communication_Score', 'Target_Achievement_Score', 'Quality_Score']
    avg_scores = filtered_df[score_cols].fillna(0).mean().reset_index()
    avg_scores.columns = ['Metric', 'Score']
    
    # دالة لتحديد اسم المؤشر العربي
    def get_arabic_metric_name(metric):
        metric_map = {
            'HSE_Score': 'السلامة والصحة المهنية',
            'Communication_Score': 'التواصل والاستجابة',
            'Target_Achievement_Score': 'تحقيق المستهدفات',
            'Quality_Score': 'الجودة'
        }
        return metric_map.get(metric, metric)

    avg_scores['Metric_AR'] = avg_scores['Metric'].apply(get_arabic_metric_name)

    with col11:
        st.metric("متوسط التقييم العام للمقاول", f"{avg_overall_score:.2f}")
        
        # إضافة مخطط بياني (Bar Chart) صغير لتقييم المقاول الفرعي
        fig_scores = px.bar(
            avg_scores, 
            x='Score', y='Metric_AR', 
            orientation='h',
            title='متوسط درجات التقييم الفرعية',
            color_discrete_sequence=[PRIMARY_COLOR],
            text='Score'
        )
        # تخصيص المخطط ليناسب المساحة
        fig_scores.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_scores.update_layout(
            xaxis_title=None, yaxis_title=None, 
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor='white',
            yaxis={'autorange': "reversed"},
            font=dict(family='Tajawal', size=12) # تطبيق الخط العربي
        )
        st.plotly_chart(fig_scores, use_container_width=True)


    with col12:
        # عرض المخطط الزمني للإنجاز الفعلي مقابل المخطط
        st.subheader("تتبع أداء الإنجاز الزمني", anchor=False)
        
        # تجميع البيانات شهرياً (المتوسط)
        if 'Report_Date' in filtered_df.columns:
            monthly_data = filtered_df.groupby(filtered_df['Report_Date'].dt.to_period('M'))[[
                'Actual_Completion_Rate', 'Target_Completion_Rate'
            ]].mean().reset_index()
            
            monthly_data['Report_Date'] = monthly_data['Report_Date'].dt.to_timestamp()
            monthly_data['Actual_Completion_Rate'] = monthly_data['Actual_Completion_Rate'] * 100
            monthly_data['Target_Completion_Rate'] = monthly_data['Target_Completion_Rate'] * 100
            
            fig_completion = px.line(
                monthly_data, x='Report_Date', y=['Actual_Completion_Rate', 'Target_Completion_Rate'], 
                title='الإنجاز الفعلي مقابل المخطط (شهري)',
                labels={
                    'value': 'النسبة المئوية', 
                    'Report_Date': 'تاريخ التقرير', 
                    'variable': 'النوع',
                    'Actual_Completion_Rate': 'الفعلي',
                    'Target_Completion_Rate': 'المخطط'
                },
                color_discrete_map={
                    'Actual_Completion_Rate': SUCCESS_COLOR, 
                    'Target_Completion_Rate': ACCENT_COLOR
                }
            )
            
            fig_completion.update_layout(
                legend_title_text='مؤشر الإنجاز',
                font=dict(family='Tajawal', size=12)
            )
            
            st.plotly_chart(fig_completion, use_container_width=True)
    
    st.divider()

# ----------------------------------------------------
# -------------------- صفحة التحليل التفصيلي (التخصصي) --------------------
# ----------------------------------------------------

elif page == "detailed_analysis":
    st.title("تحليل تفصيلي: تتبع الأداء التخصصي")
    
    # استقبال كل من DataFrame المفلتر وقائمة التصنيفات المختارة
    filtered_df, selected_category_list = filter_sidebar(df)
    
    # 1. تحديد التصنيف المختار الصالح (من قائمة اختيار المستخدم)
    valid_selected_categories = [cat for cat in selected_category_list if cat in ['انارة', 'طرق']]
    
    # 2. تطبيق المنطق الشرطي للعرض
    if len(valid_selected_categories) == 0:
        if filtered_df.empty:
            st.warning("لا توجد بيانات للعقود في الإطار الزمني أو الفلاتر المحددة. يرجى تعديل خيارات الفلترة.")
        else:
            st.warning("**يرجى اختيار تصنيف واحد (إنارة أو طرق)** من القائمة الجانبية لعرض المؤشرات التخصصية.")
        st.stop()
        
    elif len(valid_selected_categories) > 1:
        st.warning("تم اختيار أكثر من تصنيف صالح. يرجى اختيار **تصنيف واحد فقط** لتفعيل التحليل التخصصي.")
        st.stop()

    current_category = valid_selected_categories[0]
        
    # تحقق إضافي إذا كانت البيانات فارغة بعد تطبيق كل الفلاتر
    if filtered_df.empty:
        st.warning(f"لا توجد بيانات للعقود المصنفة كـ **{current_category}** ضمن الفلاتر المطبقة (التاريخ، المحور، المهندس المشرف، الخ.). يرجى تعديل هذه الفلاتر.")
        st.stop()

    st.info(f"عرض مؤشرات الأداء التخصصية لـ **{current_category}**")
    st.divider()

    # تحديد المؤشرات التي سيتم عرضها بناءً على التصنيف (تم اختصار القائمة لأغراض العرض)
    LIGHTING_METRICS = [
        ('استبدال أعمدة (تراكمي)', 'L_Rep_Col_Actual', 'L_Rep_Col_Target'),
        ('صيانة أعمدة (شهري)', 'L_Maint_Col_Monthly_Actual', 'L_Maint_Col_Monthly_Target'),
        ('فوانيس الإنارة (تراكمي)', 'L_Lantern_Actual', 'L_Lantern_Target'),
        ('لوحات التوزيع (شهري)', 'L_Board_Monthly_Actual', 'L_Board_Monthly_Target'),
    ]
    
    ROADS_METRICS = [
        ('الفرقة الرئيسية (تراكمي)', 'FR_Cum_Actual', 'FR_Cum_Target'),
        ('المعاملات (شهري)', 'Trans_Monthly_Actual', 'Trans_Monthly_Target'),
        ('الأرصفة (تراكمي)', 'Pave_Cum_Actual', 'Pave_Cum_Target'),
        ('السلامة المرورية (شهري)', 'Traffic_Monthly_Actual', 'Traffic_Monthly_Target'),
    ]

    target_metrics_display = LIGHTING_METRICS if current_category == 'انارة' else ROADS_METRICS
    
    # 3. عرض الرسوم البيانية التراكمية الرئيسية
    main_metric_name, actual_col, target_col = target_metrics_display[0]
    
    st.subheader(f"تتبع الأداء التراكمي: {main_metric_name}", anchor=False)
    
    if 'Report_Date' in filtered_df.columns and actual_col in filtered_df.columns:
        # حساب المتوسط الشهري للتراكمي
        monthly_data = filtered_df.groupby(filtered_df['Report_Date'].dt.to_period('M'))[[
            actual_col, target_col
        ]].mean().reset_index()
            
        monthly_data['Report_Date'] = monthly_data['Report_Date'].dt.to_timestamp()
        
        # تحويل النسب لعرضها بـ 100%
        monthly_data[actual_col] = monthly_data[actual_col] * 100
        monthly_data[target_col] = monthly_data[target_col] * 100
            
        fig_cum = px.line(
            monthly_data, x='Report_Date', y=[actual_col, target_col], 
            title=f"أداء {main_metric_name} المخطط مقابل الفعلي",
            labels={
                'value': 'النسبة المئوية', 
                'Report_Date': 'التاريخ', 
                'variable': 'النوع',
                actual_col: 'الفعلي',
                target_col: 'المستهدف'
            },
            color_discrete_map={actual_col: SUCCESS_COLOR, target_col: ACCENT_COLOR}
        )
        fig_cum.update_layout(font=dict(family='Tajawal', size=12))
        st.plotly_chart(fig_cum, use_container_width=True)
    else:
        st.warning(f"بيانات الأداء التراكمي لـ {main_metric_name} غير متوفرة بشكل كافٍ أو مفقودة في الأعمدة.")
    

    st.divider()
        
    # 4. عرض جميع المؤشرات التخصصية في بطاقات
    st.subheader(f"ملخص جميع مؤشرات {current_category} (المتوسط التراكمي/الشهري)", anchor=False)
        
    cols = st.columns(4)
    col_index = 0
        
    # استخدام البيانات المفلترة للوصول إلى آخر تقرير لكل عقد (للحسابات التراكمية والنهائية)
    latest_per_contract = filtered_df.loc[filtered_df.groupby('Contract_ID')['Report_Date'].idxmax()]
        
    # دمج جميع الأعمدة المطلوبة في قائمة واحدة للحسابات
    all_metrics_to_calculate = [col for _, col, _ in target_metrics_display] + [col for _, _, col in target_metrics_display]
    
    for metric_ar_name, actual_metric, target_metric in target_metrics_display:
        
        # حساب متوسط القيمتين (الفعلي والمستهدف)
        avg_actual_value = latest_per_contract[actual_metric].fillna(0).mean() * 100
        avg_target_value = latest_per_contract[target_metric].fillna(0).mean() * 100
        
        # حساب الانحراف
        deviation = avg_actual_value - avg_target_value
            
        cols[col_index % 4].metric(
            metric_ar_name, 
            f"{avg_actual_value:.2f}%",
            delta=f"{deviation:.2f}%",
            delta_color='normal' if deviation >= 0 else 'inverse'
        )
        col_index += 1

# ----------------------------------------------------
# -------------------- صفحة عرض كامل التفاصيل --------------------
# ----------------------------------------------------

elif page == "raw_data_view":
    st.title("عرض كامل التفاصيل (البيانات الخام)")
    
    # هنا لا نحتاج قائمة التصنيفات، نستقبل DataFrame فقط
    filtered_df, _ = filter_sidebar(df)
    
    st.subheader("جدول بيانات التقارير المفصل", anchor=False)
    
    if filtered_df.empty:
         st.warning("لا توجد بيانات مطابقة لمعايير الفلترة الحالية.")
         st.stop()
    
    # قائمة الأعمدة المراد عرضها في الجدول (تم تحسينها لتكون موجزة ومهمة)
    display_cols_brief = [
        'Contract_ID', 'Report_Date', 'Contractor', 'Supervisor_Engineer', 'Project_Name', 
        'Actual_Completion_Rate', 'Target_Completion_Rate', 'Actual_Deviation_Rate', 'Project_Deviation_Status',
        'Contractor_Overall_Score', 'HSE_Score', 'Quality_Score',
    ]
    
    existing_cols_brief = [col for col in display_cols_brief if col in filtered_df.columns]

    st.dataframe(
        filtered_df[existing_cols_brief],
        column_config={
            "Contract_ID": "رقم العقد", "Report_Date": "تاريخ التقرير", "Contractor": "المقاول",
            "Supervisor_Engineer": "المهندس المشرف", "Project_Name": "المشروع",
            "Actual_Completion_Rate": st.column_config.ProgressColumn(
                "الإنجاز الفعلي", format="%.1f%%", min_value=0, max_value=1
            ),
             "Target_Completion_Rate": st.column_config.ProgressColumn(
                "الإنجاز المخطط", format="%.1f%%", min_value=0, max_value=1
            ),
            "Actual_Deviation_Rate": st.column_config.NumberColumn("معدل الانحراف", format="%.2f"),
            "Project_Deviation_Status": "حالة المشروع",
            "Contractor_Overall_Score": st.column_config.NumberColumn("تقييم المقاول العام", format="%.2f"),
            "HSE_Score": "درجة السلامة",
            "Quality_Score": "درجة الجودة",
        },
        hide_index=True,
        use_container_width=True
    )
