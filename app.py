# Libraries
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import PIL
from datetime import date, datetime, timedelta

# Page Favicon
favicon = PIL.Image.open('favicon.png')

# Layout
st.set_page_config(page_title='Outlier - Blockchain Analytics', page_icon=favicon, layout='wide')

# Variables
theme_plotly = 'streamlit'
queries = pd.read_csv('data/queries.csv')
charts = pd.read_csv('data/charts.csv')
week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# App Description
with st.expander('**How Outlier Works?**'):
    st.write("""
        **Outlier** is a multi-blockchain (cross-chain) analytical tool that allows users to select
        their desired metrics and compare the state of the available blockchains since **2022**.
        
        The app consists of two main sections: the filtering section on top and the data visualization
        follows after.

        In the top part, there are multiple dropdowns and select boxes that users can interact
        with the determine their desired metric. The **Segment** dropdown determines the sector
        within the crypto industry, for example, the addresses or transactions. The **Metric**
        dropdown determines a specific area within the selected segment. The **Blockchains**
        select box provides a list of all the available blockchains for the selected metric.
        After that, users are able to select the scale of the following charts and also, determine
        the date range they would like to see the data for.

        The visualization part includes three different charts. The first one is a line chart
        showing the values of the selected metric for the selected blockchains on a daily basis.
        The second chart is a normalized area chart that depicts the daily share of the selected
        metric for different blockchains. Lastly, the third chart shows a normalized heatmap of
        the selected metric over different days of a week that demonstrates when the selected
        metrics had the highest/ lowest activity.
    """)

# Filters
c1, c2 = st.columns(2)
with c1:
    option_segments = st.selectbox(
        '**Segment**',
        options=queries['Segment'].unique(),
        key='option_segments'
    )

with c2:
    option_metrics = st.selectbox(
        '**Metric**',
        options=queries.query("Segment == @option_segments")['Metric'].unique(),
        key='option_metrics'
    )

option_blockchains = st.multiselect(
    '**Blockchains**',
    options=queries.query("Segment == @option_segments & Metric == @option_metrics")['Blockchain'].unique(),
    default=queries.query("Segment == @option_segments & Metric == @option_metrics")['Blockchain'].unique(),
    key='option_blockchains'
)

# Data
data_file = f"data/{option_segments.lower()}_{option_metrics.lower().replace(' ', '_')}_daily.csv"
df = pd.read_csv(data_file)

if df['Date'].iloc[0] >= str(date.today() - timedelta(1)) and df.loc[df['Date'] == df['Date'].iloc[0], 'Blockchain'].unique().size == df['Blockchain'].unique().size:
    df = df.query("Blockchain == @option_blockchains")

else:
    query_result = pd.DataFrame()
    for blockchain in option_blockchains:
        if df[df['Blockchain'] == blockchain]['Date'].iloc[0] < str(date.today() - timedelta(2)):
            query_id = queries.query("Segment == @option_segments & Metric == @option_metrics & Blockchain == @blockchain")['Query'].iloc[0]
            query_result = pd.read_json(f"https://api.flipsidecrypto.com/api/v2/queries/{query_id}/data/latest")
            query_result['Blockchain'] = blockchain
            query_result['Date'] = query_result['Date'].dt.strftime('%Y-%m-%d')
            df = pd.concat([query_result[~query_result['Date'].isin(df[df['Blockchain'] == blockchain]['Date'])], df]).sort_values(['Date', 'Blockchain'], ascending=[False, True]).reset_index(drop=True)

    df.to_csv(data_file, index=False)

if df.loc[df['Date'] == df['Date'].iloc[0], 'Blockchain'].unique().size < df['Blockchain'].unique().size:
    df.drop(df[df['Date'] == df['Date'].iloc[0]].index, inplace = True)

# Time Frame
c1, c2 = st.columns([1, 7])
with c1:
    # option_scale = st.checkbox('**Log Scale**', key='option_scale')
    option_scale = st.radio('**Scale**', options=['Linear', 'Log'], key='option_scale')
with c2:
    option_dates = st.slider(
        '**Date Range**',
        min_value=datetime.strptime(df['Date'].min(), '%Y-%m-%d').date(),
        max_value=datetime.strptime(df['Date'].max(), '%Y-%m-%d').date(),
        value=(datetime.strptime(str(date.today() - timedelta(90)), '%Y-%m-%d').date(), datetime.strptime(df['Date'].max(), '%Y-%m-%d').date()),
        key='option_dates'
    )

# Divider
st.divider()

# Metric Description
metric_descrption = charts.query("Segment == @option_segments & Metric == @option_metrics")['Description'].iloc[0]
st.info(f"**Metric Description**: {metric_descrption}", icon="💡")

df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
df = df.query("Blockchain == @option_blockchains & Date >= @option_dates[0] & Date <= @option_dates[1]").reset_index(drop=True)

# Charts
if len(option_blockchains) <= 1:
    st.warning('Please select at least 2 blockchains to see the metrics.')

else:
    title = charts.query("Segment == @option_segments & Metric == @option_metrics")['Title'].iloc[0]
    y_axis = charts.query("Segment == @option_segments & Metric == @option_metrics")['Y Axis'].iloc[0]

    fig = px.line(df, x='Date', y='Values', color='Blockchain', custom_data=['Blockchain'], title=f"Daily {title}", log_y=(option_scale == 'Log'))
    fig.update_layout(legend_title=None, xaxis_title=None, yaxis_title=y_axis, hovermode='x unified')
    fig.update_traces(hovertemplate='%{customdata}: %{y:,.0f}<extra></extra>')
    st.plotly_chart(fig, use_container_width=True, theme=theme_plotly)

    fig = go.Figure()
    for i in option_blockchains:
        fig.add_trace(go.Scatter(
            name=i,
            x=df.query("Blockchain == @i")['Date'],
            y=df.query("Blockchain == @i")['Values'],
            mode='lines',
            stackgroup='one',
            groupnorm='percent'
        ))
    fig.update_layout(title=f'Daily Share of {title}')
    st.plotly_chart(fig, use_container_width=True, theme=theme_plotly)

    df_heatmap = df.copy()
    df_heatmap['Normalized'] = df.groupby('Blockchain')['Values'].transform(lambda x: (x - x.min()) / (x.max() - x.min()))
    fig = px.density_heatmap(df_heatmap, x='Blockchain', y=df_heatmap.Date.dt.strftime('%A'), z='Normalized', histfunc='avg', title=f"Daily Heatmap of Normalized {title}")
    fig.update_layout(legend_title=None, xaxis_title=None, yaxis_title=None, coloraxis_colorbar=dict(title='Normalized'))
    fig.update_xaxes(categoryorder='category ascending')
    fig.update_yaxes(categoryorder='array', categoryarray=week_days)
    st.plotly_chart(fig, use_container_width=True, theme=theme_plotly)

    with st.expander('**View and Download Data**'):
        column_values = f"{option_segments} {option_metrics}"
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df = df.rename(columns={'Values': column_values})
        df = df[['Date', 'Blockchain', column_values]]
        df.index += 1
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="Download CSV",
            data=df.to_csv().encode('utf-8'),
            file_name=f"outlier_{option_segments.lower()}_{option_metrics.lower().replace(' ', '_')}.csv",
            mime='text/csv',
        )

# Divider
st.divider()

# Credits
c1, c2, c3 = st.columns(3)
with c1:
    st.info('**Data Analyst: [@AliTslm](https://twitter.com/AliTslm)**', icon="💡")
with c2:
    st.info('**GitHub: [@alitaslimi](https://github.com/alitaslimi)**', icon="💻")
with c3:
    st.info('**Data: [Flipside Crypto](https://flipsidecrypto.xyz)**', icon="🧠")