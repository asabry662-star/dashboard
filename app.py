import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from pyairtable import Table

# ----------------------------------------------
# 1. إعدادات الصفحة والتصميم (CSS Customization)
# ----------------------------------------------

# الألوان للهوية البصرية (يمكنك تعديلها لاحقاً)
PRIMARY_COLOR = "#004d99"  
SUCCESS_COLOR = "#28a745"  
WARNING_COLOR = "#dc3545"  
ACCENT_COLOR = "#007bff"   

st.set_page_config(layout="wide", page_title="نظام متابعة أداء عقود التشغيل والصيانة")

# تطبيق CSS مخصص ليتوافق مع التصميم المطلوب
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="st-"] {{ font-family: 'Tajawal', sans-serif; }}
    .stApp {{ background-color: #f8f9fa; }}

    /* تصميم بطاقات KPI لتكون بارزة */
    div.st-emotion-cache-k7vsyb, div.st-emotion-cache-1r6r8u, div[data-testid*="stMetric"] {{ 
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border-left: 5px solid {ACCENT_COLOR}; 
        margin-bottom: 15px;
    }}
    
    .css-1f2wzrg {{ color: {PRIMARY_COLOR}; }} 
    [data-testid="stMetricValue"] {{ color: {ACCENT_COLOR}; font-size: 2.5em; }}
    .css-1b4z8g7, .css-1b4z8g7 div:first-child {{ color: {WARNING_COLOR} !important; }} 
    
    /* تصميم البطاقة المجمعة (لتقييم المقاول) */
    .combined-card {{
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border-left: 5px solid {PRIMARY_COLOR};
        margin-bottom: 15px;
        height: 100%;
    }}
    .combined-card h4 {{
        color: {PRIMARY_COLOR};
        border-bottom: 2px solid #eee;
        padding-bottom: 5px;
        margin-top: 0;
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
    # يجب استبدال هذا الجزء بقراءة مفاتيحك الفعلية
    # في بيئة Code Interpreter، يجب عليك توفير المفاتيح أو إزالتها لتجنب الخطأ
    # في بيئة Streamlit Cloud، يتم قراءة المفاتيح من ملف .streamlit/secrets.toml
    AIRTABLE_API_KEY = st.secrets["airtable"]["api_key"]
    AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
    AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
except KeyError:
    # يجب تعليق هذا السطر في بيئة Code Interpreter أو توفير مفاتيح وهمية
    # إذا كنت تستخدم Streamlit Cloud، تأكد من وجود مفاتيحك في secrets.toml
    st.error("خطأ: يرجى التأكد من إعداد مفاتيح Airtable (api_key, base_id, table_name) في Streamlit Secrets.")
    st.stop()


@st.cache_data(ttl=600) # تخزين مؤقت للبيانات لمدة 10 دقائق
def load_and_process_data():
    try:
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
    
    # ------------------ معالجة الأخطاء (KeyError Fix applied here) ------------------
    
    # الأعمدة المطلوبة لضمان عدم الانهيار في أي صفحة
    # تم إضافة 'Delayed_Financial_Value' هنا
    REQUIRED_COLS = [
        'Actual_Financial_Value', 'Target_Financial_Value', 'Total_Contract_Value',
        'Delayed_Financial_Value', # <--- **العمود الذي تم إضافته لحل مشكلة KeyError**
        'Actual_Completion_Rate', 'Target_Completion_Rate', 'Actual_Deviation_Rate', 
        'Contract_ID', 'Report_Date', 'Category', 'Contract_Duration', 'Elapsed_Time_Rate',
        'Contractor_Overall_Score', 'HSE_Score', 'Communication_Score', 'Target_Achievement_Score', 'Quality_Score'
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
                 df[col] = 0 
    
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

    # 6. تنظيف وتحويل القيم المالية والـ Scores (لن تحدث مشكلة KeyError هنا بعد الإصلاح)
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
    if not df['Report_Date'].empty and 'Contract_ID' in df.columns:
        latest_reports = df.loc[df.groupby('Contract_ID')['Report_Date'].idxmax()]
    else:
        latest_reports = df.copy() 

    return df, latest_reports

# استدعاء الدالة
df, latest_reports_df = load_and_process_data()

if df.empty:
    st.info("لا توجد بيانات للعرض. يرجى مراجعة إعدادات Airtable في ملف Secrets أو التحقق من صلاحيات المفتاح.")
    st.stop()


# ----------------------------------------------
# 3. واجهة الفلاتر (Interface Filters)
# ----------------------------------------------

def filter_sidebar(df):
    st.sidebar.header("خيارات الفلترة")

    # قائمة الفلاتر المطلوبة
    axis_options = df['Axis'].dropna().unique() if 'Axis' in df.columns else []
    supervisor_options = df['Supervisor_Engineer'].dropna().unique() if 'Supervisor_Engineer' in df.columns else []
    category_options = df['Category'].dropna().unique() if 'Category' in df.columns else []
    contract_options = df['Contract_ID'].dropna().unique() if 'Contract_ID' in df.columns else []
    
    selected_axis = st.sidebar.multiselect("المحور:", options=axis_options)
    selected_supervisor = st.sidebar.multiselect("المهندس المشرف:", options=supervisor_options)
    selected_category = st.sidebar.multiselect("التصنيف:", options=category_options)
    selected_contract = st.sidebar.multiselect("رقم العقد:", options=contract_options)
    
    status_options = ['متقدم', 'متأخر', 'مطابق', 'غير معلوم']
    selected_status = st.sidebar.multiselect("حالة المشروع:", options=status_options)
    
    # فلتر التاريخ
    if 'Report_Date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Report_Date']) and not df['Report_Date'].empty:
        min_date = df['Report_Date'].min().date()
        max_date = df['Report_Date'].max().date()
        date_range = st.sidebar.slider(
            "تاريخ التقرير:",
            min_value=min_date, max_value=max_date,
            value=(min_date, max_date), format="YYYY/MM/DD"
        )
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
    else:
        start_date = pd.Timestamp.min
        end_date = pd.Timestamp.max

    # تطبيق الفلاتر
    df_filtered = df.copy()
    if selected_axis: df_filtered = df_filtered[df_filtered['Axis'].isin(selected_axis)]
    if selected_supervisor: df_filtered = df_filtered[df_filtered['Supervisor_Engineer'].isin(selected_supervisor)]
    if selected_category: df_filtered = df_filtered[df_filtered['Category'].isin(selected_category)]
    if selected_contract: df_filtered = df_filtered[df_filtered['Contract_ID'].isin(selected_contract)]
    if selected_status: df_filtered = df_filtered[df_filtered['Project_Deviation_Status'].isin(selected_status)]
    
    df_filtered = df_filtered[(df_filtered['Report_Date'] >= start_date) & (df_filtered['Report_Date'] <= end_date)]
    
    return df_filtered

# ----------------------------------------------
# 4. بناء الصفحات والتنقل
# ----------------------------------------------

PAGES = {
    "1. ملخص تنفيذي (KPIs)": "executive_summary",
    "2. تحليل تفصيلي (المسار الزمني)": "detailed_analysis",
    "3. عرض كامل التفاصيل": "raw_data_view"
}

st.sidebar.title("تنقل بين الصفحات")
selection = st.sidebar.radio("اذهب إلى:", list(PAGES.keys()))
page = PAGES[selection]

# ----------------------------------------------------
# -------------------- صفحة الملخص التنفيذي --------------------
# ----------------------------------------------------

if page == "executive_summary":
    st.title("ملخص تنفيذي: المؤشرات الرئيسية")
    st.markdown("---")
    
    filtered_df = filter_sidebar(df)
    
    # تجميع البيانات الأخيرة بعد الفلترة
    filtered_latest_df = filtered_df.loc[filtered_df.groupby('Contract_ID')['Report_Date'].idxmax()]

    # 1. حساب المؤشرات المطلوبة
    total_projects = filtered_latest_df['Contract_ID'].nunique()
    
    avg_actual_completion = filtered_latest_df['Actual_Completion_Rate'].fillna(0).mean() * 100
    avg_target_completion = filtered_latest_df['Target_Completion_Rate'].fillna(0).mean() * 100
    total_target_value = filtered_latest_df['Target_Financial_Value'].fillna(0).sum() / 1000000
    total_actual_value = filtered_latest_df['Actual_Financial_Value'].fillna(0).sum() / 1000000
    avg_overall_score = filtered_latest_df['Contractor_Overall_Score'].fillna(0).mean()

    # 2. عرض المؤشرات في بطاقات مترابطة (4 صفوف رئيسية)
    
    # --- الصف الأول: بطاقة الوقت والمشاريع ---
    st.subheader("إجمالي الوضع العام والمشاريع")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("إجمالي عدد المشاريع (فريد)", f"{total_projects}")
    col2.metric("متوسط مدة العقد (أيام)", f"{filtered_latest_df['Contract_Duration'].fillna(0).mean():.0f}")
    col3.metric("متوسط المدة المنقضية %", f"{filtered_latest_df['Elapsed_Time_Rate'].fillna(0).mean() * 100:.1f}%")
    
    status_counts = filtered_latest_df['Project_Deviation_Status'].value_counts()
    late_count = status_counts.get('متأخر', 0)
    col4.metric("المشاريع المتأخرة", f"{late_count}", delta_color='inverse', delta=f"من أصل {total_projects}")

    st.markdown("---")
    
    # --- الصف الثاني: بطاقة نسب الإنجاز وحالة المشروع ---
    st.subheader("ملخص الإنجاز")
    col5, col6, col7 = st.columns(3)
    
    col5.metric("متوسط الإنجاز المخطط", f"{avg_target_completion:.1f}%")
    col6.metric("متوسط الإنجاز الفعلي", f"{avg_actual_completion:.1f}%", 
                delta=f"{avg_actual_completion - avg_target_completion:.1f}%")
    
    avg_dev = filtered_latest_df['Actual_Deviation_Rate'].fillna(0).mean() * 100
    col7.metric("متوسط الانحراف الكلي", f"{avg_dev:.1f}%", 
                delta_color='inverse', delta=f"{avg_dev:.1f}%")
    
    st.markdown("---")

    # --- الصف الثالث: بطاقة القيمة المالية ---
    st.subheader("ملخص القيمة المالية")
    col8, col9, col10 = st.columns(3)

    col8.metric("إجمالي القيمة المخططة (مليون)", f"{total_target_value:,.2f}M")
    col9.metric("إجمالي القيمة الفعلية (مليون)", f"{total_actual_value:,.2f}M")
    deviation_val = total_actual_value - total_target_value
    col10.metric("الانحراف المالي الكلي (مليون)", f"{deviation_val:,.2f}M", 
                delta=f"{deviation_val:,.2f}M", delta_color='inverse')

    st.markdown("---")

    # --- الصف الرابع: بطاقة تقييم المقاول المجمعة ---
    st.subheader("تقييم الأداء والمقاول")
    col11, col12 = st.columns([1, 2])
    
    with col11:
        st.metric("متوسط التقييم العام للمقاول", f"{avg_overall_score:.2f}")

    with col12:
        st.markdown('<div class="combined-card">', unsafe_allow_html=True)
        st.markdown('<h4>تفاصيل تقييم المقاول (المتوسط)</h4>', unsafe_allow_html=True)
        
        # عرض المؤشرات الفرعية داخل البطاقة المجمعة
        score_cols = ['HSE_Score', 'Communication_Score', 'Target_Achievement_Score', 'Quality_Score']
        avg_scores = filtered_df[score_cols].fillna(0).mean()
        
        # تصميم عرض القيم داخل البطاقة
        col_s1, col_s2 = st.columns(2)
        
        col_s1.markdown(f"**السلامة والصحة المهنية:** {avg_scores['HSE_Score']:.2f}")
        col_s1.markdown(f"**التواصل والاستجابة:** {avg_scores['Communication_Score']:.2f}")

        col_s2.markdown(f"**تحقيق المستهدفات:** {avg_scores['Target_Achievement_Score']:.2f}")
        col_s2.markdown(f"**الجودة:** {avg_scores['Quality_Score']:.2f}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")

# ----------------------------------------------------
# -------------------- صفحة التحليل التفصيلي (التخصصي) --------------------
# ----------------------------------------------------

elif page == "detailed_analysis":
    st.title("تحليل تفصيلي: تتبع الأداء التخصصي")
    st.markdown("---")
    
    filtered_df = filter_sidebar(df)
    
    # 1. تحديد التصنيف المختار من الفلاتر
    selected_categories = filtered_df['Category'].dropna().unique()
    
    # تحديد المؤشرات التي سيتم عرضها بناءً على التصنيف
    
    LIGHTING_METRICS = [
        'L_Rep_Col_Target', 'L_Rep_Col_Actual', 'L_Rep_Col_Monthly_Target', 'L_Rep_Col_Monthly_Actual',
        'L_Maint_Col_Target', 'L_Maint_Col_Actual', 'L_Maint_Col_Monthly_Target', 'L_Maint_Col_Monthly_Actual',
        'L_Fuse_Target', 'L_Fuse_Actual', 'L_Fuse_Monthly_Target', 'L_Fuse_Monthly_Actual',
        'L_Lantern_Target', 'L_Lantern_Actual', 'L_Lantern_Monthly_Target', 'L_Lantern_Monthly_Actual',
        'L_Arm_Target', 'L_Arm_Actual', 'L_Arm_Monthly_Target', 'L_Arm_Monthly_Actual',
        'L_Board_Target', 'L_Board_Actual', 'L_Board_Monthly_Target', 'L_Board_Monthly_Actual',
        'L_Cable_Target', 'L_Cable_Actual', 'L_Cable_Monthly_Target', 'L_Cable_Monthly_Actual'
    ]
    
    ROADS_METRICS = [
        'FR_Cum_Target', 'FR_Cum_Actual', 'FR_Monthly_Target', 'FR_Monthly_Actual',
        'Trans_Cum_Target', 'Trans_Cum_Actual', 'Trans_Monthly_Target', 'Trans_Monthly_Actual',
        'Pave_Cum_Target', 'Pave_Cum_Actual', 'Pave_Monthly_Target', 'Pave_Monthly_Actual',
        'Paint_Cum_Target', 'Paint_Cum_Actual', 'Paint_Monthly_Target', 'Paint_Monthly_Actual',
        'Traffic_Cum_Target', 'Traffic_Cum_Actual', 'Traffic_Monthly_Target', 'Traffic_Monthly_Actual',
        'Emergency_Cum_Target', 'Emergency_Cum_Actual', 'Emergency_Monthly_Target', 'Emergency_Monthly_Actual',
        'Wash_Cum_Target', 'Wash_Cum_Actual', 'Wash_Monthly_Target', 'Wash_Monthly_Actual',
        'Other_Cum_Target', 'Other_Cum_Actual', 'Other_Monthly_Target', 'Other_Monthly_Actual',
        # دورات الحفر (Holes) - لا يتم حساب المتوسط لها مباشرة في الـ KPI cards
    ]
    
    # 2. تطبيق المنطق الشرطي للعرض
    
    if len(selected_categories) == 0:
        st.warning("يرجى اختيار **تصنيف واحد (إنارة أو طرق)** من القائمة الجانبية لعرض المؤشرات التخصصية.")
        st.stop()
        
    if len(selected_categories) == 1:
        current_category = selected_categories[0]
        
        if current_category == 'انارة':
            st.info("عرض المؤشرات التراكمية والشهرية الخاصة بـ **الإنارة**.")
            # التأكد من أن المؤشر موجود في أعمدة الداتا فريم بعد الفلترة
            target_metrics = [m for m in LIGHTING_METRICS if m in filtered_df.columns]
            chart_title = "تتبع أداء أعمال الإنارة التراكمي (استبدال أعمدة)"
            actual_col = 'L_Rep_Col_Actual'
            target_col = 'L_Rep_Col_Target'
            
        elif current_category == 'طرق':
            st.info("عرض المؤشرات التراكمية والشهرية الخاصة بـ **الطرق**.")
            # التأكد من أن المؤشر موجود في أعمدة الداتا فريم بعد الفلترة
            target_metrics = [m for m in ROADS_METRICS if m in filtered_df.columns]
            chart_title = "تتبع أداء أعمال الطرق التراكمي (الفرقة الرئيسية)"
            actual_col = 'FR_Cum_Actual'
            target_col = 'FR_Cum_Target'

        else:
            st.warning("التصنيف المختار غير معروف لتطبيق المؤشرات التخصصية. (قد يكون 'غير محدد')")
            st.stop()
            
        # 3. عرض الرسوم البيانية التراكمية (المتوسط)
        
        # حساب المتوسط الشهري للتراكمي
        if 'Report_Date' in filtered_df.columns:
            # التأكد من أن الأعمدة المطلوبة موجودة في DataFrame قبل Groupby
            if actual_col in filtered_df.columns and target_col in filtered_df.columns:
                monthly_data = filtered_df.groupby(filtered_df['Report_Date'].dt.to_period('M'))[[
                    actual_col, target_col
                ]].mean().reset_index()
                
                monthly_data['Report_Date'] = monthly_data['Report_Date'].dt.to_timestamp()
                
                fig_cum = px.line(
                    monthly_data, x='Report_Date', y=[actual_col, target_col], 
                    title=chart_title,
                    labels={'value': 'النسبة التراكمية', 'Report_Date': 'التاريخ', 'variable': 'النوع'},
                    color_discrete_map={actual_col: SUCCESS_COLOR, target_col: ACCENT_COLOR}
                )
                st.plotly_chart(fig_cum, use_container_width=True)
            else:
                 st.warning("لا يمكن عرض المخطط الزمني: أعمدة المؤشر الرئيسي مفقودة.")
        else:
            st.warning("لا يمكن عرض المخطط الزمني بسبب عدم وجود عمود 'Report_Date'.")


        st.markdown("---")
        
        # 4. عرض جميع المؤشرات التخصصية في بطاقات
        st.subheader(f"جميع مؤشرات الأداء التخصصية لـ **{current_category}** (المتوسط)")
        
        cols = st.columns(4)
        col_index = 0
        
        # استخدام البيانات المفلترة للوصول إلى آخر تقرير لكل عقد
        latest_per_contract = filtered_df.loc[filtered_df.groupby('Contract_ID')['Report_Date'].idxmax()]
        
        for metric in target_metrics:
            # تم التأكد من وجود metric في القائمة target_metrics أعلاه
            
            avg_value = latest_per_contract[metric].fillna(0).mean()
            
            # استخدام المتغير العام REVERSE_COLUMN_MAP
            arabic_name = REVERSE_COLUMN_MAP.get(metric, metric)
            
            if 'Rate' in metric or 'Cum' in metric or 'Monthly' in metric:
                 display_value = f"{avg_value * 100:.2f}%"
            else:
                 display_value = f"{avg_value:,.2f}"
            
            cols[col_index % 4].metric(arabic_name, display_value)
            col_index += 1
                
    else:
        # الحالة الثالثة: تم اختيار أكثر من تصنيف
        st.warning("تم اختيار أكثر من تصنيف في الفلتر. يرجى اختيار **تصنيف واحد فقط** (إنارة أو طرق) لتفعيل التحليل التخصصي.")

# ----------------------------------------------------
# -------------------- صفحة عرض كامل التفاصيل --------------------
# ----------------------------------------------------

elif page == "raw_data_view":
    st.title("عرض كامل التفاصيل (البيانات الخام)")
    st.markdown("---")
    
    filtered_df = filter_sidebar(df)
    
    st.subheader("جدول بيانات التقارير المفصل")
    
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
