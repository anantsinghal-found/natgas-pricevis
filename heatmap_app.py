import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide")


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
    
    # --- Industrial Sites Circles ---
    try:
        industrial_df = pd.read_excel('industrial_sites_rtc_member_data.xlsx')
        # Filter out states with 0 companies
        industrial_df = industrial_df[industrial_df['Number of Companies with Industrial/Manufacturing Sites'] > 0]
        
        # State centroid coordinates (approximate)
        state_centroids = {
            'AL': (32.8, -86.8), 'AK': (64.0, -152.0), 'AZ': (33.7, -111.6), 'AR': (35.2, -92.4),
            'CA': (36.8, -119.4), 'CO': (39.0, -105.5), 'CT': (41.6, -72.7), 'DE': (38.9, -75.5),
            'DC': (38.9, -77.0), 'FL': (27.7, -81.5), 'GA': (32.6, -83.4), 'HI': (19.9, -155.6),
            'ID': (44.4, -114.7), 'IL': (40.0, -89.0), 'IN': (39.8, -86.1), 'IA': (42.0, -93.2),
            'KS': (38.5, -98.0), 'KY': (37.5, -85.3), 'LA': (31.2, -91.8), 'ME': (44.5, -69.2),
            'MD': (39.0, -76.7), 'MA': (42.3, -71.8), 'MI': (44.3, -85.6), 'MN': (46.7, -94.7),
            'MS': (32.7, -89.6), 'MO': (38.5, -92.5), 'MT': (47.0, -110.5), 'NE': (41.5, -99.7),
            'NV': (39.3, -116.6), 'NH': (43.7, -71.6), 'NJ': (40.1, -74.7), 'NM': (34.5, -106.0),
            'NY': (43.0, -75.0), 'NC': (35.6, -79.8), 'ND': (47.5, -100.5), 'OH': (40.4, -82.7),
            'OK': (35.6, -97.1), 'OR': (44.0, -120.6), 'PA': (40.9, -77.8), 'RI': (41.6, -71.5),
            'SC': (33.9, -80.9), 'SD': (44.3, -100.3), 'TN': (35.7, -86.7), 'TX': (31.5, -100.0),
            'UT': (39.3, -111.6), 'VT': (44.0, -72.7), 'VA': (37.5, -78.5), 'WA': (47.4, -121.5),
            'WV': (38.6, -80.9), 'WI': (44.3, -89.6), 'WY': (42.7, -107.2)
        }
        
        # Add circles for industrial sites
        for _, row in industrial_df.iterrows():
            state = row['State']
            num_companies = row['Number of Companies with Industrial/Manufacturing Sites']
            
            if state in state_centroids:
                lat, lon = state_centroids[state]
                # Scale circle size based on number of companies (min 5, max 20)
                size = max(5, min(20, 5 + (num_companies * 2)))
                
                fig.add_trace(go.Scattergeo(
                    lon=[lon],
                    lat=[lat],
                    mode='markers',
                    marker=dict(
                        size=size,
                        color='blue',
                        opacity=0.2,
                        line=dict(width=1, color='darkblue')
                    ),
                    name=f'{state}: {num_companies} companies',
                    showlegend=False,
                    hovertext=f'{state}: {num_companies} industrial companies',
                    hoverinfo='text'
                ))
        
        # Add legend circles for scale (positioned off-map)
        legend_sizes = [5, 20]
        legend_companies = [1, 15]
        #legend_lat = 25  # Below the map
        #legend_lon = -110  # West of the map
        
        for i, (size, companies) in enumerate(zip(legend_sizes, legend_companies)):
            fig.add_trace(go.Scattergeo(
                lon=[None], 
                lat=[None],
                mode='markers',
                marker=dict(
                    size=size,
                    color='blue',
                    opacity=0.2,
                    line=dict(width=1, color='darkblue')
                ),
                name=f'{companies} industrial sites',
                showlegend=True,
                hovertext=f'Legend: {companies} industrial sites',
                hoverinfo='text'
            ))
            
    except Exception as e:
        st.warning(f"Could not load industrial sites data: {e}")
    
    fig.update_layout(
        title={
            'text': (
                f'Green: High-Cost State (Gas > ${nat_gas_threshold}/MWh or Electricity > ${elec_threshold}/MWh) <br>'
                f' Red: Low-Cost State (Both < Threshold)'
            ),
            'x': 0.5,
            'xanchor': 'center'
        },
        geo=dict(scope='usa'),
        legend_title_text='No. of Industrial Sites',
        height=700
    )
    return fig

st.title('US Energy Price Analysis')
nat_gas_threshold = st.number_input('Natural Gas Price Threshold ($/MWh)', min_value=0.0, value=30.0)
elec_threshold = st.number_input('Electricity Price Threshold ($/MWh)', min_value=0.0, value=105.0)
fig = plot_map(nat_gas_threshold, elec_threshold)
st.plotly_chart(fig, use_container_width=True)