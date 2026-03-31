import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ----------------------------------------------------------------------
# 1. App Configuration & Header
# ----------------------------------------------------------------------
st.set_page_config(page_title="LEC Simulator", layout="wide")

st.title("Local Energy Community Simulator")
st.markdown("""
**Welcome to the interactive LEC Sandbox.**  
Explore how different mathematical **Sharing Coefficients** impact the physical energy flows and the financial bills of the community members.
""")

# ----------------------------------------------------------------------
# 2. Sidebar: Controls & Tariffs
# ----------------------------------------------------------------------
st.sidebar.header("Community Settings")

# Coefficient Selector
coefficient = st.sidebar.selectbox(
    "1. Select Sharing Coefficient",
    ("Proportional (DSO Standard)", "Fixed (50/50 Split)", "Hierarchical (SME is Tier 1)", "Dynamic (Price Optimized)")
)

st.sidebar.markdown("---")
st.sidebar.header("Economic Parameters")
st.sidebar.caption("Set the tariffs (in CHF/kWh)")

# Tariffs
tariff_SME = st.sidebar.slider("Grid Tariff SME (Daytime peak)", 0.10, 0.40, 0.20, 0.01)
tariff_SFH = st.sidebar.slider("Grid Tariff SFH (Evening peak)", 0.10, 0.40, 0.30, 0.01)
feed_in_tariff = st.sidebar.slider("Feed-in Tariff (Export)", 0.00, 0.15, 0.06, 0.01)

st.sidebar.markdown("---")
st.sidebar.info("""
** Note:**
* **SME** = Small Business (e.g., Bakery). High daytime load.
* **SFH** = Single Family Home. High evening load (EV + Cooking).
""")

# ----------------------------------------------------------------------
# 3. Generate Synthetic 24h Data
# ----------------------------------------------------------------------
# Create a 24-hour timeline
hours = np.arange(0, 24)
df = pd.DataFrame({"Hour": hours})

# PV Generation (Bell curve peaking at 13:00)
df['PV_Gen'] = 25 * np.exp(-((hours - 13)**2) / 10)

# SME Load (Bakery: peaks in the morning, runs steady during day)
df['Load_SME'] = 5 + 15 * np.exp(-((hours - 8)**2) / 6) + 8 * np.exp(-((hours - 14)**2) / 12)

# SFH Load (Household + EV: low during day, massive spike at 18:00)
df['Load_SFH'] = 2 + 12 * np.exp(-((hours - 19)**2) / 4)

df['Total_Load'] = df['Load_SME'] + df['Load_SFH']

# ----------------------------------------------------------------------
# 4. The Mathematical Engine (Sharing Coefficients)
# ----------------------------------------------------------------------
# Initialize allocation columns
df['Alloc_SME'] = 0.0
df['Alloc_SFH'] = 0.0

if coefficient == "Fixed (50/50 Split)":
    # 50% to SME, 50% to SFH (Capped by actual load)
    df['Alloc_SME'] = np.minimum(df['PV_Gen'] * 0.5, df['Load_SME'])
    df['Alloc_SFH'] = np.minimum(df['PV_Gen'] * 0.5, df['Load_SFH'])

elif coefficient == "Proportional (DSO Standard)":
    # Share based on the ratio of instantaneous load
    safe_total = np.where(df['Total_Load'] == 0, 1, df['Total_Load']) # Prevent division by zero
    ratio_SME = df['Load_SME'] / safe_total
    ratio_SFH = df['Load_SFH'] / safe_total
    
    df['Alloc_SME'] = np.minimum(df['PV_Gen'] * ratio_SME, df['Load_SME'])
    df['Alloc_SFH'] = np.minimum(df['PV_Gen'] * ratio_SFH, df['Load_SFH'])

elif coefficient == "Hierarchical (SME is Tier 1)":
    # SME gets everything it needs first. Leftovers go to SFH.
    df['Alloc_SME'] = np.minimum(df['PV_Gen'], df['Load_SME'])
    leftover_pv = df['PV_Gen'] - df['Alloc_SME']
    df['Alloc_SFH'] = np.minimum(leftover_pv, df['Load_SFH'])

elif coefficient == "Dynamic (Price Optimized)":
    # Algorithm checks who has the more expensive grid tariff and feeds them first 
    # to maximize total community financial savings.
    if tariff_SME > tariff_SFH:
        df['Alloc_SME'] = np.minimum(df['PV_Gen'], df['Load_SME'])
        df['Alloc_SFH'] = np.minimum(df['PV_Gen'] - df['Alloc_SME'], df['Load_SFH'])
    else:
        df['Alloc_SFH'] = np.minimum(df['PV_Gen'], df['Load_SFH'])
        df['Alloc_SME'] = np.minimum(df['PV_Gen'] - df['Alloc_SFH'], df['Load_SME'])

# Calculate Grid Imports and Exports
df['Grid_Import_SME'] = df['Load_SME'] - df['Alloc_SME']
df['Grid_Import_SFH'] = df['Load_SFH'] - df['Alloc_SFH']
df['Total_Allocated'] = df['Alloc_SME'] + df['Alloc_SFH']
df['Grid_Export'] = df['PV_Gen'] - df['Total_Allocated']

# ----------------------------------------------------------------------
# 5. Financial Calculations
# ----------------------------------------------------------------------
cost_grid_SME = df['Grid_Import_SME'].sum() * tariff_SME
cost_grid_SFH = df['Grid_Import_SFH'].sum() * tariff_SFH
revenue_export = df['Grid_Export'].sum() * feed_in_tariff

# Baseline Costs (What if there was no PV?)
baseline_SME = df['Load_SME'].sum() * tariff_SME
baseline_SFH = df['Load_SFH'].sum() * tariff_SFH

# Savings
savings_SME = baseline_SME - cost_grid_SME
savings_SFH = baseline_SFH - cost_grid_SFH
total_community_savings = savings_SME + savings_SFH + revenue_export

# SSR (Self-Sufficiency Rate)
ssr = (df['Total_Allocated'].sum() / df['Total_Load'].sum()) * 100

# ----------------------------------------------------------------------
# 6. Dashboard Render: KPIs
# ----------------------------------------------------------------------
st.subheader(f"Results for: {coefficient}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Community Self-Sufficiency", f"{ssr:.1f} %")
col2.metric("Total Grid Export (Wasted)", f"{df['Grid_Export'].sum():.1f} kWh")
col3.metric("Highest Grid Peak (kW)", f"{(df['Grid_Import_SME'] + df['Grid_Import_SFH']).max():.1f} kW")
col4.metric("Total Comm. Value Created", f"CHF {total_community_savings:.2f}")

st.markdown("---")

# ----------------------------------------------------------------------
# 7. Dashboard Render: Visualizations (Plotly)
# ----------------------------------------------------------------------
col_charts_1, col_charts_2 = st.columns([2, 1])

with col_charts_1:
    st.markdown("Physical Energy Flows (24h)")
    
    # Create an interactive Plotly Area Chart
    fig1 = go.Figure()
    
    # PV Generation Line
    fig1.add_trace(go.Scatter(x=df['Hour'], y=df['PV_Gen'], mode='lines', 
                              name='Total PV Generation', line=dict(color='#f1c40f', width=4)))
    
    # Allocated SME
    fig1.add_trace(go.Scatter(x=df['Hour'], y=df['Alloc_SME'], mode='none', fill='tozeroy', 
                              name='Allocated to SME', fillcolor='rgba(41, 128, 185, 0.7)'))
    
    # Allocated SFH (Stacked on top of SME)
    fig1.add_trace(go.Scatter(x=df['Hour'], y=df['Alloc_SME'] + df['Alloc_SFH'], mode='none', fill='tonexty', 
                              name='Allocated to SFH', fillcolor='rgba(39, 174, 96, 0.7)'))
    
    # Total Load Line (Dotted)
    fig1.add_trace(go.Scatter(x=df['Hour'], y=df['Total_Load'], mode='lines', 
                              name='Total Community Demand', line=dict(color='red', width=2, dash='dash')))

    fig1.update_layout(xaxis_title="Hour of Day", yaxis_title="Power (kW)", 
                       hovermode="x unified", height=400, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig1, use_container_width=True)

with col_charts_2:
    st.markdown("Financial Value Created")
    st.caption("Avoided grid costs + Export revenues")
    
    # Bar Chart for Financials
    fin_data = pd.DataFrame({
        "Entity": ["SME Savings", "SFH Savings", "Export Revenue"],
        "CHF": [savings_SME, savings_SFH, revenue_export]
    })
    
    fig2 = px.bar(fin_data, x="Entity", y="CHF", text="CHF", 
                  color="Entity", color_discrete_sequence=['#2980b9', '#27ae60', '#f39c12'])
    fig2.update_traces(texttemplate='CHF %{text:.2f}', textposition='outside')
    fig2.update_layout(showlegend=False, height=400, margin=dict(l=0, r=0, t=30, b=0), yaxis_range=[0, fin_data['CHF'].max() + 10])
    st.plotly_chart(fig2, use_container_width=True)

# ----------------------------------------------------------------------
# 8. Explanatory Footer
# ----------------------------------------------------------------------
with st.expander("Expand to see the mathematical logic for this coefficient"):
    if "Fixed" in coefficient:
        st.latex(r"E_{SME} = \min(PV_{gen} \times 0.5, Load_{SME})")
        st.write("The Fixed coefficient forces a strict 50/50 split. If a peer doesn't need their 50%, it is exported to the grid, even if the other peer still has a demand deficit. **Notice the high 'Wasted' Grid Export KPI.**")
    elif "Proportional" in coefficient:
        st.latex(r"E_{SME} = \min\left(PV_{gen} \times \frac{Load_{SME}}{Load_{total}}, Load_{SME}\right)")
        st.write("The legally mandated standard for Swiss LEGs. Allocation perfectly mirrors actual consumption ratios. It maximizes total physical self-consumption, but ignores financial tariffs.")
    elif "Hierarchical" in coefficient:
        st.latex(r"E_{SME} = \min(PV_{gen}, Load_{SME}) \quad | \quad E_{SFH} = \min(PV_{gen} - E_{SME}, Load_{SFH})")
        st.write("SME acts as Tier 1. It consumes as much solar as it needs first. The SFH only receives the 'leftovers' (if any). Great for securing the ROI of the primary investor.")
    elif "Dynamic" in coefficient:
        st.write("The algorithm checks the tariffs in the sidebar. It realizes that the **SFH pays a higher grid tariff** than the SME. To maximize the wealth of the community, it automatically acts like a Hierarchical key, prioritizing the SFH first to avoid the expensive grid import!")