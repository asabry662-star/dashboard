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
    
    'مؤشر غسيل الدهانات التراكمي المستهدف': 'Wash_Cum_Target', 'مؤشر
