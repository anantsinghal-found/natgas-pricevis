import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# State name to abbreviation mapping
state_abbrev = {
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

# Read the Excel file, specifying the sheet and header row (row 3, so header=2)
file_path = 'Domestic Natural Gas Data.xls'
sheet_name = 'Data 1'
df = pd.read_excel(file_path, sheet_name=sheet_name, header=2)

# Filter for 2020-2025
if not pd.api.types.is_datetime64_any_dtype(df['Date']):
    df['Date'] = pd.to_datetime(df['Date'])
df_2020_2025 = df[(df['Date'] >= '2020-01-01') & (df['Date'] <= '2025-12-31')]

# Extract state columns (exclude 'Date' and US total)
state_cols = [col for col in df.columns if col not in ['Date', 'United States Natural Gas Industrial Price (Dollars per Thousand Cubic Feet)']]

# Calculate average price for each state
avg_prices = df_2020_2025[state_cols].mean()

# Prepare DataFrame for mapping
# Fix typo in Nevada column name
state_names = []
for col in state_cols:
    if col.startswith('Nevada Natural Gas Indutrial Price'):
        state_names.append('Nevada')
    else:
        state_names.append(col.replace(' Natural Gas Industrial Price (Dollars per Thousand Cubic Feet)', ''))
state_abbrevs = [state_abbrev.get(name, None) for name in state_names]
avg_prices_df = pd.DataFrame({'state': state_abbrevs, 'nat_gas_price': avg_prices.values})

# Remove any rows where abbreviation is None (just in case)
avg_prices_df = avg_prices_df.dropna(subset=['state'])

# Convert from $/kcf to $/MWh (1 kcf ≈ 3.29 MWh)
avg_prices_df['nat_gas_price'] = avg_prices_df['nat_gas_price'] * 3.29

# Cap color scale at 95th percentile to reduce outlier effect (e.g., Hawaii)
color_max = avg_prices_df['nat_gas_price'].quantile(0.95)

# --- ELECTRICITY PRICE DATA ---
# Read electricity price data (cents/kWh), convert to $/MWh, and aggregate by state

elec_df = pd.read_excel('electricity_price_avg.xlsx', header=2)

# Convert from cents/kWh to $/MWh
# 1 cent/kWh = $10/MWh
# Create a new column for $/MWh

elec_df['elec_price_MWh'] = elec_df['Average Price (cents/kWh)'].astype(float) * 10

# If there are multiple months, take the average for each state
state_elec_avg = elec_df.groupby('State')['elec_price_MWh'].mean().reset_index()

# Map state names to abbreviations for merging
state_elec_avg['state'] = state_elec_avg['State'].map(state_abbrev)
state_elec_avg = state_elec_avg.dropna(subset=['state'])

# Merge with gas price DataFrame
merged_df = avg_prices_df.merge(state_elec_avg[['state', 'elec_price_MWh']], on='state', how='inner')
merged_df = merged_df.rename(columns={'elec_price_MWh': 'elec_price'})

# --- COLOR ASSIGNMENT ---
# Green: both gas > $10/MWh and elec > $30/MWh
# Red: both gas <= $10/MWh and elec <= $30/MWh
# Gray: all other cases

def assign_color(row):
    if row['nat_gas_price'] > 30 or row['elec_price'] > 105:
        return 'green'
    elif row['nat_gas_price'] <= 30 and row['elec_price'] <= 105:
        return 'red'
    else:
        return 'gray'

merged_df['color'] = merged_df.apply(assign_color, axis=1)

# --- PLOT MAP WITH CUSTOM COLORS ---
fig = go.Figure()

for color in ['green', 'red', 'gray']:
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
    title_text='States with High Gas (> $10/MWh) and Electricity (> $30/MWh) Prices (Green), Both Low (Red), Mixed (Gray)',
    geo=dict(scope='usa'),
    legend_title_text='Price Category',
)

# Custom label positions for crowded Northeast states (lat, lon) - staggered and spread out
custom_label_positions = {
    'ME': (49.0, -62.0),
    'NH': (48.0, -63.5),
    'VT': (47.0, -65.0),
    'MA': (46.0, -66.5),
    'RI': (45.0, -68.0),
    'CT': (44.0, -69.5),
    'NY': (43.0, -71.0),
    'NJ': (42.0, -72.5),
    'DE': (41.0, -74.0),
    'MD': (40.0, -75.5),
    'DC': (39.0, -77.0)
}

# State centroid coordinates (approximate, for leader lines)
state_centroids = {
    'CT': (41.6, -72.7), 'DE': (38.9, -75.5), 'DC': (38.9, -77.0), 'MD': (39.0, -76.7),
    'MA': (42.3, -71.8), 'NH': (43.7, -71.6), 'NJ': (40.1, -74.7), 'RI': (41.6, -71.5),
    'VT': (44.0, -72.7), 'NY': (43.0, -75.0)
}

# Add state name and price as text labels, with leader lines for crowded states
for i, row in avg_prices_df.iterrows():
    state = row['state']
    price = row['nat_gas_price']
    if pd.isna(price):
        continue  # Skip NaN values
    if state in custom_label_positions:
        centroid_lat, centroid_lon = state_centroids.get(state, (None, None))
        label_lat, label_lon = custom_label_positions[state]
        if centroid_lat is not None and centroid_lon is not None:
            fig.add_trace(go.Scattergeo(
                locationmode='USA-states',
                lon=[centroid_lon, label_lon],
                lat=[centroid_lat, label_lat],
                mode='lines',
                line=dict(width=1, color='black'),
                showlegend=False,
                hoverinfo='skip',
            ))
        fig.add_trace(go.Scattergeo(
            locationmode='USA-states',
            lon=[label_lon],
            lat=[label_lat],
            text=f"{state}: ${price:.2f}",
            mode='text',
            showlegend=False,
            textfont=dict(color='black', size=16, family='Arial Black'),
        ))
    else:
        fig.add_trace(go.Scattergeo(
            locationmode='USA-states',
            locations=[state],
            text=f"{state}: ${price:.2f}",
            mode='text',
            showlegend=False,
            textfont=dict(color='black', size=16, family='Arial Black'),
        ))

# Calculate US low, median, and high average state prices (in $/MWh) for 2024-2025
state_prices = avg_prices_df['nat_gas_price'].dropna()
low_price = state_prices.min()
median_price = state_prices.median()
high_price = state_prices.max()

print(f'US State Average Price (2024-2025, $/MWh):')
print(f'  Low:    ${low_price:.2f}')
print(f'  Median: ${median_price:.2f}')
print(f'  High:   ${high_price:.2f}')

# Calculate 25th, 50th, and 75th percentiles
p25 = state_prices.quantile(0.25)
p50 = state_prices.quantile(0.50)
p75 = state_prices.quantile(0.75)

print(f'Percentiles (2024-2025, $/MWh):')
print(f'  25th: ${p25:.2f}')
print(f'  50th: ${p50:.2f}')
print(f'  75th: ${p75:.2f}')

# Calculate and print all percentiles in 5 percentile increments
percentiles = list(range(0, 101, 5))
percentile_values = state_prices.quantile([p/100 for p in percentiles])

print('Percentiles (2024-2025, $/MWh):')
for p, value in zip(percentiles, percentile_values):
    print(f'  {p:3d}th: ${value:.2f}')

# Cluster states into 'Low', 'Median', and 'High' price groups with High defined as >$50
high_cut = 50.0
low_cut = state_prices.quantile(0.5)  # Use median for low/median split

low_states = avg_prices_df[avg_prices_df['nat_gas_price'] <= low_cut]['state'].tolist()
median_states = avg_prices_df[(avg_prices_df['nat_gas_price'] > low_cut) & (avg_prices_df['nat_gas_price'] <= high_cut)]['state'].tolist()
high_states = avg_prices_df[avg_prices_df['nat_gas_price'] > high_cut]['state'].tolist()

print('\nState Clusters (2024-2025, $/MWh):')
print(f'Low   (<= ${low_cut:.2f}): {", ".join(low_states)}')
print(f'Median(>  ${low_cut:.2f} and <= ${high_cut:.2f}): {", ".join(median_states)}')
print(f'High  (>  ${high_cut:.2f}): {", ".join(high_states)}')

fig.show()
