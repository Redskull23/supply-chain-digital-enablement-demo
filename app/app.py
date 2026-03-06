import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Supply Chain Digital Enablement Demo",
    page_icon="📦",
    layout="wide",
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    plans = pd.read_csv(DATA_DIR / "planning_data.csv")
    network = pd.read_csv(DATA_DIR / "network_data.csv")
    alerts = pd.read_csv(DATA_DIR / "action_queue.csv")
    lanes = pd.read_csv(DATA_DIR / "lane_data.csv")
    return plans, network, alerts, lanes


plans, network, alerts, lanes = load_data()

st.sidebar.title("Demo Controls")
selected_region = st.sidebar.multiselect(
    "Region",
    sorted(plans["region"].unique()),
    default=sorted(plans["region"].unique()),
)
selected_scenario = st.sidebar.selectbox(
    "Scenario",
    ["Base Plan", "Promo Surge", "Supplier Constraint", "Weather Disruption"],
)
selected_horizon = st.sidebar.slider("Planning horizon (weeks)", min_value=4, max_value=16, value=8)

multiplier_map = {
    "Base Plan": 1.00,
    "Promo Surge": 1.12,
    "Supplier Constraint": 0.93,
    "Weather Disruption": 0.96,
}

risk_map = {
    "Base Plan": 1.00,
    "Promo Surge": 1.18,
    "Supplier Constraint": 1.28,
    "Weather Disruption": 1.22,
}

plans_view = plans[plans["region"].isin(selected_region)].copy()
network_view = network[network["region"].isin(selected_region)].copy()
alerts_view = alerts[alerts["region"].isin(selected_region)].copy()
lanes_view = lanes[lanes["region"].isin(selected_region)].copy()

plans_view["adj_demand"] = (plans_view["forecast_demand"] * multiplier_map[selected_scenario]).round(0)
plans_view["adj_supply"] = (plans_view["planned_supply"] * (1 - (risk_map[selected_scenario] - 1) * 0.12)).round(0)
plans_view["gap"] = plans_view["adj_supply"] - plans_view["adj_demand"]
plans_view["service_projection"] = ((plans_view["adj_supply"] / plans_view["adj_demand"]).clip(upper=1.0) * 100).round(1)

network_view["risk_score"] = (network_view["base_risk_score"] * risk_map[selected_scenario]).clip(0, 100).round(1)
network_view["inventory_days"] = (network_view["inventory_days"] / multiplier_map[selected_scenario]).round(1)
lanes_view["on_time_pct"] = (lanes_view["on_time_pct"] / (risk_map[selected_scenario] * 0.98)).clip(70, 100).round(1)

avg_service = plans_view["service_projection"].mean()
avg_gap = plans_view["gap"].sum()
avg_risk = network_view["risk_score"].mean()
avg_inventory = network_view["inventory_days"].mean()
open_critical = int((alerts_view["priority"] == "Critical").sum())
throughput = network_view["throughput_pct"].mean()

st.title("Supply Chain Digital Enablement Demo")
st.caption(
    "A portfolio-ready product demo for planning intelligence, network visibility, and execution orchestration. "
    "Built for hiring manager review and live stakeholder demos."
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Projected Service Level", f"{avg_service:.1f}%", delta=f"{avg_service - 95.0:+.1f} pts")
c2.metric("Net Demand/Supply Gap", f"{avg_gap:,.0f}", delta="units")
c3.metric("Average Network Risk", f"{avg_risk:.1f}", delta="composite")
c4.metric("Inventory Coverage", f"{avg_inventory:.1f} days")
c5.metric("Critical Actions Open", f"{open_critical}", delta="needs action")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "Executive Overview",
    "Planning Intelligence",
    "Network Visibility",
    "Execution Orchestration",
])

with tab1:
    left, right = st.columns([1.4, 1])
    with left:
        by_week = (
            plans_view.groupby("week", as_index=False)[["adj_demand", "adj_supply"]]
            .sum()
            .head(selected_horizon)
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=by_week["week"], y=by_week["adj_demand"], mode="lines+markers", name="Demand"))
        fig.add_trace(go.Scatter(x=by_week["week"], y=by_week["adj_supply"], mode="lines+markers", name="Supply"))
        fig.update_layout(title="Demand vs Supply Outlook", height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        risk_by_site = network_view.sort_values("risk_score", ascending=False)
        fig2 = px.bar(
            risk_by_site,
            x="site",
            y="risk_score",
            color="node_type",
            title="Highest Risk Nodes",
        )
        fig2.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig2, use_container_width=True)

    a, b = st.columns(2)
    with a:
        st.subheader("Portfolio Story")
        st.markdown(
            f"""
            - **Planning domain:** scenario-aware demand, supply, and service projections across {len(selected_region)} region(s)
            - **Operations domain:** throughput tracking across plants, DCs, and suppliers
            - **Visibility domain:** lane and node risk surfaced in one operating view
            - **Execution domain:** actionable queue converts insights into owned work
            """
        )
    with b:
        st.subheader("Leadership Talking Points")
        st.markdown(
            """
            - Multi-domain product portfolio with shared data and workflow foundations
            - Aligned roadmaps across supply chain, operations, finance, and technology
            - Rationalized fragmented reporting into a decision-support layer
            - Designed around measurable business outcomes, not isolated features
            """
        )

with tab2:
    st.subheader("Planning Intelligence")
    p1, p2 = st.columns([1.2, 1])
    with p1:
        sku_summary = (
            plans_view.groupby(["sku_family"], as_index=False)[["adj_demand", "adj_supply", "gap"]]
            .sum()
            .sort_values("gap")
        )
        fig3 = px.bar(
            sku_summary,
            x="sku_family",
            y="gap",
            title="Demand/Supply Gap by SKU Family",
        )
        fig3.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig3, use_container_width=True)
    with p2:
        region_service = plans_view.groupby("region", as_index=False)["service_projection"].mean()
        fig4 = px.line(region_service, x="region", y="service_projection", markers=True, title="Projected Service by Region")
        fig4.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20), yaxis_title="Service %")
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("#### Scenario Recommendation")
    worst_gap = sku_summary.iloc[0]
    st.info(
        f"Under **{selected_scenario}**, the most constrained family is **{worst_gap['sku_family']}** with a projected gap of "
        f"**{worst_gap['gap']:,.0f} units**. Recommended actions include sequencing supply reallocation, activating alternate "
        "sourcing, and prioritizing service-level tradeoff decisions by business criticality."
    )

    st.dataframe(
        plans_view[["week", "region", "sku_family", "forecast_demand", "planned_supply", "adj_demand", "adj_supply", "gap", "service_projection"]]
        .head(20),
        use_container_width=True,
        hide_index=True,
    )

with tab2.expander("Decision Narrative"):
    st.markdown(
        """
        This planning domain helps leaders answer:
        - Where are we constrained?
        - Which decisions improve service fastest?
        - What happens if demand spikes or supply is disrupted?
        - Which tradeoffs should be made across cost, service, and availability?
        """
    )

with tab3:
    st.subheader("Network Visibility")
    v1, v2 = st.columns([1, 1])
    with v1:
        bubble = px.scatter(
            network_view,
            x="inventory_days",
            y="throughput_pct",
            size="risk_score",
            color="node_type",
            hover_name="site",
            title="Node Health: Inventory vs Throughput vs Risk",
        )
        bubble.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(bubble, use_container_width=True)
    with v2:
        lane_chart = px.bar(
            lanes_view.sort_values("on_time_pct"),
            x="lane",
            y="on_time_pct",
            color="status",
            title="Lane Performance",
        )
        lane_chart.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20), yaxis_title="On-time %")
        st.plotly_chart(lane_chart, use_container_width=True)

    st.dataframe(
        network_view[["site", "region", "node_type", "inventory_days", "throughput_pct", "risk_score", "top_issue"]]
        .sort_values("risk_score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

with tab4:
    st.subheader("Execution Orchestration")
    e1, e2 = st.columns([1, 1])
    with e1:
        priority_counts = alerts_view.groupby("priority", as_index=False).size()
        fig5 = px.pie(priority_counts, names="priority", values="size", title="Action Queue by Priority")
        fig5.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig5, use_container_width=True)
    with e2:
        owner_counts = alerts_view.groupby("owner_team", as_index=False).size()
        fig6 = px.bar(owner_counts, x="owner_team", y="size", title="Workload by Team")
        fig6.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20), xaxis_title="Owner team", yaxis_title="Open items")
        st.plotly_chart(fig6, use_container_width=True)

    st.dataframe(
        alerts_view[["priority", "region", "alert_type", "recommended_action", "owner_team", "due_days", "status"]]
        .sort_values(["priority", "due_days"]),
        use_container_width=True,
        hide_index=True,
    )

    st.success(
        "This tab reflects product maturity: insights do not stop at dashboards. "
        "They become owned actions with recommended next steps, accountable teams, and closed-loop follow-through."
    )

st.divider()
with st.expander("Platform Architecture Summary"):
    st.markdown(
        """
        **Architecture overview**

        - ERP and manufacturing systems feed planning, inventory, order, and execution signals
        - A unified data layer standardizes events and metrics across suppliers, plants, DCs, and delivery lanes
        - Product experiences sit on top of shared services for scenario modeling, alerts, workflow, and KPI reporting
        - Role-specific views support executives, planners, plant operations, and logistics stakeholders
        - Governance focuses on data quality, trusted metrics, and consistent ownership across domains
        """
    )
