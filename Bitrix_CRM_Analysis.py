import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px

# Clear cache on app update
# st.cache_data.clear()
# st.cache_resource.clear()
# Load the .xls file using the xlrd engine

@st.cache_data
def load_data(df):    
    # Selecting columns we need for analysis
    sel_cols = f"ID, Created, Modified, Stage, Created by, Modified by, Responsible, Repeat inquiry, Deal Name, Type, Source, Company, Contact, UTM Source, UTM Medium, UTM Campaign, UTM Content, UTM Term, Lead Status, Reason for Loss, Reasons for Win, Follow Up Status, Nature of Project, Services, LS - Service Fit, LS - Urgency, LG - Budget Availability, LG - Decision Making Capability, Contact: ID, Contact: First name, Contact: Last name, Contact: Position, Contact: Responsible person, Contact: Source, Contact: Work Phone, Contact: Mobile, Contact: Shopify Store URL, Contact: Do you have a shopify website, Contact: Do you want to build a shopify website, Contact: Do you have a D2C/eCommerce webiste, Contact: Do you need any help with your online business?, Company: Company Name"
    sel_cols_list = sel_cols.split(", ")
    df = df[sel_cols_list]
    for cols in sel_cols_list:
        df[cols] = df[cols].fillna('Unknown')
    df.rename(columns={
    'Contact: Shopify Store URL': 'ShopifyURL',
    'Contact: Do you have a D2C/eCommerce webiste': 'D2C Website (y/n)',
    'Contact: Do you need any help with your online business?': 'Services Needed'}, inplace=True)
    return df

# File upload widget in the sidebar
uploaded_file = st.sidebar.file_uploader("Upload your Excel file", type=["xlsx"])

# Load data based on uploaded file or default file
if uploaded_file is not None:
    # Use the uploaded file
    data_load = pd.read_excel(uploaded_file, engine='openpyxl')
else:
    # Use the default file if no file is uploaded
    data_load = pd.read_excel("Deal_Bitrix.xlsx", engine='openpyxl')

df = load_data(data_load)
# df.head()
# for col in df.columns:
#     print(f"Column: {col}")
#     print(f"Data Type: {df[col].dtype}")
#     print(f"Number of Unique Values: {df[col].nunique()}")
#     print(f"Number of Missing Values: {df[col].isnull().sum()}")
#     print(f"Sample Values: {df[col].unique()[:5]}")
#     print("-" * 30)


# Modifying time columns to datetime variable
# Safely convert 'Created' and 'Modified' columns to datetime
df.loc[:, 'Created'] = pd.to_datetime(df['Created'], format='%d.%m.%Y %H:%M:%S')
df.loc[:, 'Modified'] = pd.to_datetime(df['Modified'], format='%d.%m.%Y %H:%M:%S')

#Extracting all stages
# stages = df['Stage'].unique().tolist()
stages = ['Reach','Attract','Develop','Meeting Booked','SQL','Proposal','Contract Sent','Negotiation','Onboarded','Renewal', 'Analyze failure']
#stages

# Making cumulative of stages by repeating all stages after it to that stage in an expanded dataframe
@st.cache_data
def expand_cumulative_stages(df, stages, stage_col='Stage'):
    expanded_data = []
    
    # Iterate through each row in the DataFrame
    for _, row in df.iterrows():
        current_stage_index = stages.index(row[stage_col])
        
        # Repeat the row for the current stage and all preceding stages
        for stage in stages[:current_stage_index + 1]:
            new_row = row.copy()
            new_row[stage_col] = stage
            expanded_data.append(new_row)
    
    # Create a new DataFrame with the expanded data
    expanded_df = pd.DataFrame(expanded_data)
    return expanded_df

# Apply the transformation to create cumulative stages
cum_stages_breakdown_expanded = expand_cumulative_stages(df, stages)
cum_stages_breakdown_expanded['Count']=1
# Only keep rows that appear once (no duplicates at all) - non_cumulative
non_cum_stages_breakdown_expanded = cum_stages_breakdown_expanded.drop_duplicates(keep=False)
# Sidebar for user inputs
st.sidebar.title("Expedify Bitrix CRM Analytics")

# Add date range filter in the sidebar
min_date = df['Created'].min()
max_date = df['Created'].max()
# Separate date input for start date
start_date = st.sidebar.date_input(
    "Start Date",
    value = min_date,
    min_value = min_date,
    max_value = max_date
)

# Separate date input for end date
end_date = st.sidebar.date_input(
    "End Date",
    value = max_date,
    min_value = min_date,
    max_value = max_date
)

# Display selected dates for debugging
st.write(f"Period: {start_date} to {end_date}")

# Ensure the start date is before the end date
if start_date > end_date:
    st.error("Error: Start date must be before or equal to the end date.")
# List of potential filter columns-later
filter_columns = ['Lead Status', 'Responsible','Source','UTM Source', 'UTM Medium', 'UTM Campaign', 'UTM Content','Nature of Project', 'D2C Website (y/n)', 'Services Needed','LS - Service Fit', 'LS - Urgency', 'LG - Budget Availability', 'LG - Decision Making Capability']
# 

# Dropdown for selecting the breakdown variable
breakdown_var = st.sidebar.selectbox(
    'Select Breakdown Variable',
    filter_columns
)

# Dictionary to store selected filters
selected_filters = {}

# Loop through each filter column and create multiselect dropdowns
for col in filter_columns:
    unique_values = list(df[col].dropna().unique())
    selected_values = st.sidebar.multiselect(f'Select {col}', unique_values, default=unique_values)
    selected_filters[col] = selected_values

def make_bar_chart(df,chart_key):

    # Filter the DataFrame based on user-selected filters and date range
    filtered_df = df.copy()

    # Apply the date range filter
    filtered_df = filtered_df[(filtered_df['Created'] >= pd.to_datetime(start_date)) & 
                            (filtered_df['Created'] <= pd.to_datetime(end_date))]

    # Apply additional filters for categorical columns
    for col, values in selected_filters.items():
        filtered_df = filtered_df[filtered_df[col].isin(values)]

    # Group the data by Stage and the selected breakdown variable
    cumulative_grouped = filtered_df.groupby(['Stage', breakdown_var])['Count'].sum().reset_index()
    # Group the data by Stage 
    cumulative_stage = filtered_df.groupby(['Stage'])['Count'].sum().reset_index()

    # Create a stacked horizontal bar chart using Plotly
    fig = px.bar(
        cumulative_grouped,
        x='Count',
        y='Stage',
        color=breakdown_var,
        orientation='h',
        barmode='stack',
        labels={'Count': 'Cumulative Count', 'Stage': 'Stage'},
        title=f'Cumulative Stage Counts by {breakdown_var} (Date Range: {start_date} to {end_date})'
    )

    # Update layout to reverse the y-axis order
    fig.update_layout(
        yaxis={'categoryorder': 'array', 'categoryarray': stages[::-1]},
        xaxis_title='Cumulative Count',
        yaxis_title='Stage',
        legend_title=breakdown_var
    )

    # Add text labels for  cumulative totals
    for i, stage in enumerate(reversed(stages)):
        try: 
            cumulative_value = cumulative_stage[cumulative_stage['Stage'] == stage]['Count'].values[0]
        except: 
            cumulative_value = 0
        fig.add_annotation(
            x=cumulative_value,
            y=i, # Corresponds to the y-position for each stage
            text=str(cumulative_value),
            showarrow=False,
            xanchor='left',
            yanchor='middle',
            font=dict(size=14, color='red')
        )

    # Display the chart
    st.plotly_chart(fig, key=chart_key)

st.write("Cumulative for All Stages")
make_bar_chart(cum_stages_breakdown_expanded, chart_key = 'cumulative_bar')
st.write("Current Status for All Stages")
make_bar_chart(non_cum_stages_breakdown_expanded, chart_key = 'current_status_bar')
# Add a footer message
st.sidebar.write("Expedify CRM")
