import streamlit as st
import pandas as pd
import plotly.express as px

# Set page config for dark mode
st.set_page_config(page_title="27-Month Rolling Sales Dashboard", layout="wide")
st.markdown("""
    <style>
        body {
            background-color: #0e1117;
            color: #ffffff;
        }
        .stApp {
            background-color: #0e1117;
        }
        .css-1d391kg, .css-ffhzg2 {
            background-color: #262730;
        }
        .st-bx, .st-dg, .st-cj, .st-bo, .st-bn {
            background-color: #1f2128;
        }
    </style>
""", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    excel_file = pd.ExcelFile("27_Month_rolling.xlsx")
    df = excel_file.parse("Rolling Periods 27 Month")
    df["Year"] = pd.to_datetime(df["Year"]).dt.year
    df["FullDate"] = pd.to_datetime(df["Year"].astype(str) + '-' + df["Month"].astype(str) + '-01')
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

def multiselect_with_select_all(label, options, key):
    select_all = st.sidebar.checkbox(f"Select All {label}", value=True, key=f"{key}_all")
    if select_all:
        return options
    else:
        return st.sidebar.multiselect(label=f"Select {label}:", options=options, key=key)

all_items = sorted(df["Item Names"].unique())
all_distributors = sorted(df["Distributors"].unique())
all_states = sorted(df["State"].unique())

selected_items = multiselect_with_select_all("Item(s)", all_items, "items")
selected_distributors = multiselect_with_select_all("Distributor(s)", all_distributors, "distributors")
selected_states = multiselect_with_select_all("State(s)", all_states, "states")

# Date filter
min_year = int(df["Year"].min())
max_year = int(df["Year"].max())
date_range = st.sidebar.slider("Select Year Range:", min_value=min_year, max_value=max_year, value=(min_year, max_year), step=1)

# Filtered data
filtered_df = df[
    (df["Item Names"].isin(selected_items)) &
    (df["Distributors"].isin(selected_distributors)) &
    (df["State"].isin(selected_states)) &
    (df["Year"] >= date_range[0]) &
    (df["Year"] <= date_range[1])
]

# Tabs
tab1, tab2 = st.tabs(["Dashboard", "Data View"])

with tab1:
    # KPIs
    total_cases = filtered_df["Case Equivs"].sum()
    total_units = filtered_df["Units Sold"].sum()
    total_revenue = filtered_df["Net Price"].sum()

    st.title("27-Month Rolling Sales Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Case Equivs", f"{total_cases:,.2f}")
    col2.metric("Total Units Sold", f"{int(total_units):,}")
    col3.metric("Total Revenue", f"${total_revenue:,.2f}")

    # Time Series Plot
    monthly_summary = (
        filtered_df.groupby([filtered_df["Year"], filtered_df["Month"]])
        .agg({"Case Equivs": "sum", "Units Sold": "sum", "Net Price": "sum"})
        .reset_index()
    )
    monthly_summary.columns = ["Year", "Month", "Case Equivs", "Units Sold", "Net Price"]
    monthly_summary["Date"] = pd.to_datetime(monthly_summary["Year"].astype(str) + '-' + monthly_summary["Month"].astype(str) + '-01')

    fig = px.line(monthly_summary, x="Date", y=["Case Equivs", "Units Sold", "Net Price"],
                  labels={"value": "Metric", "Date": "Date"},
                  title="Monthly Sales Metrics Over Time")
    fig.update_layout(paper_bgcolor='#0e1117', plot_bgcolor='#0e1117', font_color='white')
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Last 12 Months vs Previous 12 Months Comparison")
    comparison_metric = st.selectbox("Select Metric:", ["Case Equivs", "Units Sold", "Net Price"], key="compare_metric")

    latest_date = filtered_df["FullDate"].max()
    one_year_ago = latest_date - pd.DateOffset(months=12)
    two_years_ago = latest_date - pd.DateOffset(months=24)

    last_12 = filtered_df[(filtered_df["FullDate"] > one_year_ago) & (filtered_df["FullDate"] <= latest_date)]
    prev_12 = filtered_df[(filtered_df["FullDate"] > two_years_ago) & (filtered_df["FullDate"] <= one_year_ago)]

    last_agg = last_12.groupby(filtered_df["FullDate"].dt.to_period("M")).agg({comparison_metric: "sum"}).reset_index()
    prev_agg = prev_12.groupby(filtered_df["FullDate"].dt.to_period("M")).agg({comparison_metric: "sum"}).reset_index()

    last_agg["Period"] = last_agg["FullDate"].astype(str)
    prev_agg["Period"] = prev_agg["FullDate"].astype(str)
    last_agg["Type"] = "Last 12 Months"
    prev_agg["Type"] = "Previous 12 Months"

    # Align months and years for hurdle-style chart
last_agg["Month"] = last_agg["FullDate"].dt.month
last_agg["Year"] = last_agg["FullDate"].dt.year
prev_agg["Month"] = prev_agg["FullDate"].dt.month
prev_agg["Year"] = prev_agg["FullDate"].dt.year

last_agg["Label"] = last_agg["Month"].apply(lambda m: pd.to_datetime(f'2024-{m:02d}-01').strftime('%b'))
prev_agg["Label"] = prev_agg["Month"].apply(lambda m: pd.to_datetime(f'2023-{m:02d}-01').strftime('%b'))

comparison_df = pd.concat([last_agg, prev_agg])

pivot_comparison = comparison_df.pivot(index="Label", columns="Type", values=comparison_metric)
if "Last 12 Months" in pivot_comparison.columns and "Previous 12 Months" in pivot_comparison.columns:
        pivot_comparison["YoY % Change"] = ((pivot_comparison["Last 12 Months"] - pivot_comparison["Previous 12 Months"]) / pivot_comparison["Previous 12 Months"]) * 100
        styled_df = pivot_comparison.style.format({"YoY % Change": "{:.2f}%"}).apply(
            lambda x: ["color: green" if v > 0 else "color: red" if v < 0 else "" for v in x], subset=["YoY % Change"]
        )
        st.dataframe(styled_df)

        comparison_df = comparison_df.merge(
    pivot_comparison["YoY % Change"].reset_index().rename(columns={"Label": "MonthLabel"}),
    left_on="Label",
    right_on="MonthLabel",
    how="left"
)

bar_12_fig = px.bar(
        comparison_df,
        x="Label",
        y=comparison_metric,
        color="Type",
        barmode="group",
        hover_data={"YoY % Change": ':.2f'},
        title=f"{comparison_metric} - Last 12 Months vs Previous 12 Months"
    )
bar_12_fig.update_layout(paper_bgcolor='#0e1117', plot_bgcolor='#0e1117', font_color='white', xaxis_tickangle=-45)
st.plotly_chart(bar_12_fig, use_container_width=True)

st.header("Filtered Data Table")
st.dataframe(filtered_df, use_container_width=True)








