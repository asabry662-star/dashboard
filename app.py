import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ----------------------------------------------
# 1. إعدادات الصفحة والتصميم (CSS Customization)
# ----------------------------------------------

# الألوان التي تم استخلاصها من الهوية البصرية الشائعة
PRIMARY_COLOR = "#004d99"  # أزرق داكن/أساسي
SUCCESS_COLOR = "#28a745"  # أخضر للتقدم
WARNING_COLOR = "#dc3545"  # أحمر للتأخير
ACCENT_COLOR = "#007bff"   # أزرق فاتح للأرقام

st.set_page_config(layout="wide", page_title="نظام متابعة أداء عقود التشغيل والصيانة")

# تطبيق CSS مخصص ليتوافق مع التصميم المطلوب (التركيز على بطاقات KPI)
st.markdown(f"""
    <style>
    /* تغيير الخط الافتراضي */
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    html, body, [class*="st-"] {{
        font-family: 'Tajawal', sans-serif;
    }}

    /* خلفية الصفحة */
    .stApp {{
        background-color: #f8f9fa; 
    }}

    /* تصميم بطاقات KPI لتكون بارزة */
    div.st-emotion-cache-k7vsyb, div.st-emotion-cache-1r6r8u {{ /* targeting container elements for metric */
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border-left: 5px solid {ACCENT_COLOR}; /* شريط لوني جانبي */
        margin-bottom: 10px;
    }}
    
    /* لون عنوان الـ Header */
    .css-1f2wzrg {{ /* targeting main header title */
        color: {PRIMARY_COLOR};
    }}
    
    /* لون أرقام الـ KPI */
    [data-testid="stMetricValue"] {{
        color: {ACCENT_COLOR};
        font-size: 2.5em;
    }}
    
    /* لون التنبيه والانحراف */
    .css-1b4z8g7, .css-1b4z8g7 div:first-child {{ /* targeting Delta text for red color */
        color: {WARNING_COLOR} !important;
    }}
    
    </style>
    """, unsafe_allow_html=True)


# اسم الملف المرفق
FILE_PATH = "مؤشرات الاداء-Grid view (18).csv"

# ----------------------------------------------
# 2. تحميل ومعالجة البيانات (نفس المنطق القوي السابق)
# ----------------------------------------------

# (ملاحظة: هذه الدالة لم تتغير عن الكود السابق لأنها كانت صحيحة وتلبي متطلبات الحساب)
@st.cache_data
def load_and_process_data(path):
    try:
        df = pd.read_csv(path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding='cp1256')
        
    df.rename(columns={
        'عقد رقم': 'Contract_ID', 'تاريخ التقرير': 'Report_Date', 'المقاول': 'Contractor', 
        'المهندس المشرف ': 'Supervisor_Engineer', 'المشروع': 'Project_Name', 
        'التصنيف (انارة - طرق )': 'Category', 'المحور': 'Axis',
        'نسبة الانجاز المستهدفه': 'Target_Completion_Rate', 'نسبة الانجاز الفعلية': 'Actual_Completion_Rate', 
        'نسبة المدة المنقضية': 'Elapsed_Time_Rate', 'نسبة الإنحراف الفعلية': 'Actual_Deviation_Rate', 
        'قيمة العقد (ريال)': 'Total_Contract_Value',
        'مؤشر أداء المقاول  حسب الاوزان  المستهدف': 'Target_Weighted_Index',
        'مؤشر أداء المقاول  حسب الاوزان  الفعلى': 'Actual_Weighted_Index', 
        'القيمة': 'Actual_Financial_Value', 
        'القيمة المستهدفة': 'Target_Financial_Value', 'القيمة المتأخرة': 'Delayed_Financial_Value' 
    }, inplace=True)
    
    df['Report_Date'] = pd.to_datetime(df['Report_Date'], errors='coerce')
    rate_cols = ['Target_Completion_Rate', 'Actual_Completion_Rate', 'Elapsed_Time_Rate', 'Actual_Deviation_Rate', 'Target_Weighted_Index', 'Actual_Weighted_Index']
    for col in rate_cols:
         if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce') / 100

    financial_cols = ['Total_Contract_Value', 'Actual_Financial_Value', 'Target_Financial_Value', 'Delayed_Financial_Value']
    for col in financial_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '', regex=False).apply(pd.to_numeric, errors='coerce')
    
    def get_deviation_status(rate):
        if rate >= 0.05: return 'متقدم'
        elif rate <= -0.05: return 'متأخر'
        else: return 'مطابق'
    
    df['Project_Status'] = df['Actual_Deviation_Rate'].apply(get_deviation_status)
    latest_reports = df.loc[df.groupby('Contract_ID')['Report_Date'].idxmax()]
    
    return df, latest_reports

df, latest_reports_df = load_and_process_data(FILE_PATH)

# ----------------------------------------------
# 3. واجهة الفلاتر (Interface Filters)
# ----------------------------------------------

def filter_sidebar(df):
    st.sidebar.header("خيارات الفلترة")

    # قائمة الفلاتر المطلوبة
    selected_axis = st.sidebar.multiselect("المحور:", options=df['Axis'].unique())
    selected_supervisor = st.sidebar.multiselect("المهندس المشرف:", options=df['Supervisor_Engineer'].unique())
    selected_category = st.sidebar.multiselect("التصنيف:", options=df['Category'].unique())
    selected_contract = st.sidebar.multiselect("رقم العقد:", options=df['Contract_ID'].unique())
    status_options = ['متقدم', 'متأخر', 'مطابق']
    selected_status = st.sidebar.multiselect("حالة المشروع:", options=status_options)
    
    # فلتر التاريخ
    if not df['Report_Date'].empty and pd.api.types.is_datetime64_any_dtype(df['Report_Date']):
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
        start_date = df['Report_Date'].min()
        end_date = df['Report_Date'].max()

    # تطبيق الفلاتر
    df_filtered = df.copy()
    if selected_axis: df_filtered = df_filtered[df_filtered['Axis'].isin(selected_axis)]
    if selected_supervisor: df_filtered = df_filtered[df_filtered['Supervisor_Engineer'].isin(selected_supervisor)]
    if selected_category: df_filtered = df_filtered[df_filtered['Category'].isin(selected_category)]
    if selected_contract: df_filtered = df_filtered[df_filtered['Contract_ID'].isin(selected_contract)]
    if selected_status: df_filtered = df_filtered[df_filtered['Project_Status'].isin(selected_status)]
    
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
    
    # استخدام أحدث تقرير لكل عقد للحسابات الفريدة
    filtered_latest_df = filtered_df.loc[filtered_df.groupby('Contract_ID')['Report_Date'].idxmax()]
    
    # 1. حساب المؤشرات المطلوبة
    total_projects = filtered_latest_df['Contract_ID'].nunique()
    avg_actual_completion = filtered_latest_df['Actual_Completion_Rate'].mean() * 100
    avg_target_completion = filtered_latest_df['Target_Completion_Rate'].mean() * 100
    avg_deviation_rate = filtered_latest_df['Actual_Deviation_Rate'].mean() * 100
    
    # 2. بطاقات المؤشرات (6 بطاقات في صفين)
    
    st.subheader("مؤشرات الأداء الأساسية (الوضع الحالي)")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("إجمالي عدد المشاريع (فريد)", f"{total_projects}")
    col2.metric("متوسط نسبة الإنجاز الفعلي", f"{avg_actual_completion:.1f}%", delta=f"{avg_actual_completion - avg_target_completion:.1f}%")
    col3.metric("متوسط الانحراف الكلي", f"{avg_deviation_rate:.1f}%", delta_color='inverse', delta=f"{avg_deviation_rate:.1f}%")
    
    col4, col5, col6 = st.columns(3)
    
    status_counts = filtered_latest_df['Project_Status'].value_counts()
    late_count = status_counts.get('متأخر', 0)
    on_time_count = status_counts.get('مطابق', 0)
    ahead_count = status_counts.get('متقدم', 0)

    col4.metric("المشاريع المتأخرة", f"{late_count}", delta_color='inverse', delta=f"من أصل {total_projects}")
    col5.metric("المشاريع المطابقة", f"{on_time_count}")
    col6.metric("المشاريع المتقدمة", f"{ahead_count}")
    
    st.markdown("---")

    # 3. مقارنة الإنجاز (المخطط والفعلي) لجميع المشاريع (Chart)
    st.subheader("مقارنة نسبة الإنجاز المخطط والفعلي لكل مشروع")
    
    # تجميع البيانات للرسم البياني العمودي
    chart_data = filtered_latest_df[['Project_Name', 'Actual_Completion_Rate', 'Target_Completion_Rate']].melt(
        id_vars='Project_Name', var_name='Type', value_name='Rate'
    )
    chart_data['Rate'] = chart_data['Rate'] * 100
    
    fig_bar = px.bar(
        chart_data, x='Project_Name', y='Rate', color='Type', barmode='group',
        labels={'Rate': 'النسبة المئوية (%)', 'Project_Name': 'اسم المشروع', 'Type': 'نوع الإنجاز'},
        color_discrete_map={'Actual_Completion_Rate': ACCENT_COLOR, 'Target_Completion_Rate': WARNING_COLOR},
        height=500
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ----------------------------------------------------
# -------------------- صفحة التحليل التفصيلي --------------------
# ----------------------------------------------------

elif page == "detailed_analysis":
    st.title("تحليل تفصيلي: المسار الزمني والمؤشرات المالية وتقييم المقاول")
    st.markdown("---")
    
    filtered_df = filter_sidebar(df)
    
    # 1. المؤشرات المالية الرئيسية
    colA, colB, colC = st.columns(3)
    
    total_target = filtered_df['Target_Financial_Value'].sum() / 1000000
    total_actual = filtered_df['Actual_Financial_Value'].sum() / 1000000
    total_deviation = filtered_df['Delayed_Financial_Value'].sum() / 1000000

    colA.metric("إجمالي القيمة المخططة (مليون)", f"{total_target:,.2f}M")
    colB.metric("إجمالي القيمة المنجزة فعليًا (مليون)", f"{total_actual:,.2f}M")
    colC.metric("الانحراف المالي (مليون)", f"{total_deviation:,.2f}M", delta_color='inverse', delta=f"{total_deviation:,.2f}M")
    
    st.markdown("---")

    # 2. الإنجاز التراكمي والشهري (Cumulative vs Monthly)
    st.subheader("تتبع الإنجاز التراكمي (مؤشر الأوزان)")
    
    monthly_data = filtered_df.groupby(filtered_df['Report_Date'].dt.to_period('M'))[['Actual_Weighted_Index', 'Target_Weighted_Index']].mean().reset_index()
    monthly_data['Report_Date'] = monthly_data['Report_Date'].dt.to_timestamp()
    
    monthly_data['Cumulative_Actual'] = monthly_data['Actual_Weighted_Index'].cumsum()
    monthly_data['Cumulative_Target'] = monthly_data['Target_Weighted_Index'].cumsum()
    
    fig_cum = px.line(
        monthly_data, x='Report_Date', y=['Cumulative_Actual', 'Cumulative_Target'], 
        title='الإنجاز التراكمي المخطط والفعلي (مؤشر الأوزان)',
        labels={'value': 'النسبة التراكمية', 'Report_Date': 'التاريخ', 'variable': 'النوع'},
        color_discrete_map={'Cumulative_Actual': SUCCESS_COLOR, 'Cumulative_Target': ACCENT_COLOR}
    )
    st.plotly_chart(fig_cum, use_container_width=True)
    
    st.markdown("---")
    
    # 3. تقييم المقاول (Contractor Evaluation)
    st.subheader("متوسط تقييم المقاول حسب مؤشر الأوزان والانحراف")
    
    # استخدام أحدث تقرير لكل عقد
    latest_per_contract = filtered_df.loc[filtered_df.groupby('Contract_ID')['Report_Date'].idxmax()]
    
    contractor_dev = latest_per_contract.groupby('Contractor')[['Actual_Weighted_Index', 'Weighted_Deviation']].mean().reset_index()
    
    fig_eval = px.bar(
        contractor_dev, x='Contractor', y='Actual_Weighted_Index', 
        color='Weighted_Deviation', # تلوين حسب الانحراف (لتمييز الأداء)
        title='متوسط مؤشر أداء المقاول الفعلي (حسب الأوزان)',
        labels={'Actual_Weighted_Index': 'متوسط المؤشر الفعلي', 'Contractor': 'المقاول', 'Weighted_Deviation': 'متوسط الانحراف'},
        color_continuous_scale=px.colors.sequential.Bluered_r
    )
    st.plotly_chart(fig_eval, use_container_width=True)

# ----------------------------------------------------
# -------------------- صفحة عرض كامل التفاصيل --------------------
# ----------------------------------------------------

elif page == "raw_data_view":
    st.title("عرض كامل التفاصيل (البيانات الخام)")
    st.markdown("---")
    
    filtered_df = filter_sidebar(df)
    
    st.subheader("جدول بيانات التقارير المفصل")
    st.dataframe(
        filtered_df,
        column_config={
            "Contract_ID": "رقم العقد", "Report_Date": "تاريخ التقرير", "Contractor": "المقاول", 
            "Project_Name": "المشروع", "Category": "التصنيف", "Supervisor_Engineer": "المهندس المشرف", 
            "Axis": "المحور", "Actual_Completion_Rate": st.column_config.ProgressColumn(
                "نسبة الإنجاز الفعلي", format="%.1f%%", min_value=0, max_value=1
            ),
            "Target_Completion_Rate": st.column_config.ProgressColumn(
                "نسبة الإنجاز المخطط", format="%.1f%%", min_value=0, max_value=1
            ),
            "Elapsed_Time_Rate": st.column_config.ProgressColumn(
                "نسبة المدة المنقضية", format="%.1f%%", min_value=0, max_value=1
            ),
            "Actual_Deviation_Rate": st.column_config.NumberColumn("معدل الانحراف", format="%.2f"),
            "Project_Status": "حالة المشروع",
            "Total_Contract_Value": st.column_config.NumberColumn("قيمة العقد الإجمالية (ريال)", format="%.0f")
        },
        hide_index=True,
        use_container_width=True
    )
