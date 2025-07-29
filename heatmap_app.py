import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# State name to abbreviation mapping
def get_state_abbrev():
    return {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
        'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC',
        'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL',
        'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
        'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
        'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
        'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
        'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR',
        'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD',
        'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA',
        'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
    }

def plot_map(nat_gas_threshold, elec_threshold):
    state_abbrev = get_state_abbrev()
    # --- Natural Gas Data ---
    file_path = 'Domestic Natural Gas Data.xls'
    sheet_name = 'Data 1'
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=2)
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])
    df_2020_2025 = df[(df['Date'] >= '2020-01-01') & (df['Date'] <= '2025-12-31')]
    state_cols = [col for col in df.columns if col not in ['Date', 'United States Natural Gas Industrial Price (Dollars per Thousand Cubic Feet)']]
    avg_prices = df_2020_2025[state_cols].mean()
    state_names = []
    for col in state_cols:
        if col.startswith('Nevada Natural Gas Indutrial Price'):
            state_names.append('Nevada')
        else:
            state_names.append(col.replace(' Natural Gas Industrial Price (Dollars per Thousand Cubic Feet)', ''))
    state_abbrevs = [state_abbrev.get(name, None) for name in state_names]
    avg_prices_df = pd.DataFrame({'state': state_abbrevs, 'nat_gas_price': avg_prices.values})
    avg_prices_df = avg_prices_df.dropna(subset=['state'])
    avg_prices_df['nat_gas_price'] = avg_prices_df['nat_gas_price'] * 3.29

    # --- Electricity Price Data ---
    elec_df = pd.read_excel('electricity_price_avg.xlsx', header=2)
    elec_df['elec_price_MWh'] = elec_df['Average Price (cents/kWh)'].astype(float) * 10
    state_elec_avg = elec_df.groupby('State')['elec_price_MWh'].mean().reset_index()
    state_elec_avg['state'] = state_elec_avg['State'].map(state_abbrev)
    state_elec_avg = state_elec_avg.dropna(subset=['state'])
    merged_df = avg_prices_df.merge(state_elec_avg[['state', 'elec_price_MWh']], on='state', how='inner')
    merged_df = merged_df.rename(columns={'elec_price_MWh': 'elec_price'})

    # --- Color Assignment ---
    def assign_color(row):
        if row['nat_gas_price'] > nat_gas_threshold or row['elec_price'] > elec_threshold:
            return 'green'
        else:
            return 'red'
    merged_df['color'] = merged_df.apply(assign_color, axis=1)

    # --- Plot Map ---
    fig = go.Figure()
    for color in ['green', 'red']:
        sub = merged_df[merged_df['color'] == color]
        fig.add_trace(go.Choropleth(
            locations=sub['state'],
            z=[1]*len(sub),  # dummy value
            locationmode='USA-states',
            colorscale=[[0, color], [1, color]],
            showscale=False,
            marker_line_color='white',
            name=color.capitalize(),
            hovertext=[f"{row['state']}: Gas ${row['nat_gas_price']:.2f}/MWh, Elec ${row['elec_price']:.2f}/MWh" for i, row in sub.iterrows()],
            hoverinfo='text',
        ))
    fig.update_layout(
        title={
            'text': (
                f'US States: High Gas (&gt; ${nat_gas_threshold}/MWh) or Electricity (&gt; ${elec_threshold}/MWh)<br>'
                f'Green: Either Above Threshold | Red: Both Below'
            ),
            'x': 0.5,
            'xanchor': 'center'
        },
        geo=dict(scope='usa'),
        legend_title_text='Price Category',
        height=700
    )
    return fig

st.title('US State Energy Price Heatmap')
nat_gas_threshold = st.number_input('Natural Gas Price Threshold ($/MWh)', min_value=0.0, value=30.0)
elec_threshold = st.number_input('Electricity Price Threshold ($/MWh)', min_value=0.0, value=105.0)
fig = plot_map(nat_gas_threshold, elec_threshold)
st.plotly_chart(fig, use_container_width=True)