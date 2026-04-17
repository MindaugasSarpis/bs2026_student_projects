import io
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

st.set_page_config(page_title="Obligation Analysis", layout="wide")

with open(Path(__file__).parent.parent / "ui/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """<div class="app-header">
        <div>
            <div class="app-title">Obligation Analysis</div>
            <div class="app-sub">Visual analysis of extracted obligations</div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

COLORS = [
    "#4C72B0",
    "#DD8452",
    "#55A868",
    "#C44E52",
    "#8172B2",
    "#937860",
    "#DA8BC3",
    "#8C8C8C",
    "#CCB974",
    "#64B5CD",
]


def build_df_from_session():
    results = st.session_state.get("results", {})
    if not results:
        return None
    rows = []
    for idx, res in results.items():
        for obl in res["obligations"]:
            rows.append(
                {
                    "paragraph": idx + 1,
                    "actor": obl.get("actor", ""),
                    "action": obl.get("action", ""),
                    "modality": obl.get("modality", ""),
                    "condition": obl.get("condition", ""),
                    "source_text": obl.get("span", ""),
                    "rationale": obl.get("rationale", ""),
                }
            )
    return pd.DataFrame(rows) if rows else None


df = build_df_from_session()

if df is not None:
    st.info(f"Using current session data - {len(df)} obligations from the extractor.")
else:
    uploaded = st.file_uploader(
        "Upload an obligations CSV",
        type=["csv"],
        label_visibility="visible",
    )
    if uploaded:
        df = pd.read_csv(io.BytesIO(uploaded.read()))
    else:
        st.markdown(
            """<div class="empty-state">
                <p>Run the extractor on the <strong>Home</strong> page first,<br>
                or upload an obligations CSV here.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        st.stop()

# Normalise text
for col in ["actor", "action", "condition", "source_text"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.lower().replace({"nan": ""})

st.markdown("### 1. Obligation Structure")

col1, col2 = st.columns(2)

with col1:
    actor_counts = df["actor"].value_counts().head(10).reset_index()
    actor_counts.columns = ["actor", "count"]
    actor_counts["actor"] = actor_counts["actor"]
    fig = px.bar(
        actor_counts.sort_values("count"),
        x="count",
        y="actor",
        orientation="h",
        color="actor",
        color_discrete_sequence=COLORS,
        title="Top Actors by Number of Obligations",
        labels={"count": "Number of Obligations", "actor": ""},
    )
    fig.update_layout(showlegend=False, margin=dict(t=50, b=0, l=0, r=0))
    fig.update_traces(hovertemplate="%{y}<br>%{x} obligations<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    para_counts = df["paragraph"].value_counts().sort_index().reset_index()
    para_counts.columns = ["paragraph", "count"]
    fig = px.bar(
        para_counts,
        x="paragraph",
        y="count",
        title="Obligations per Paragraph",
        labels={"paragraph": "Paragraph", "count": "Obligations"},
        color_discrete_sequence=[COLORS[0]],
    )
    fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
    fig.update_traces(hovertemplate="Paragraph %{x}<br>%{y} obligations<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)


col3, col4 = st.columns(2)

with col3:
    modality_map = {
        "should": "Directive (should)",
        "should not": "Prohibition (should not)",
        "shall not": "Prohibition (shall not)",
        "must": "Mandatory (must)",
        "necessary": "Mandatory (necessary)",
        "shall": "Mandatory (shall)",
        "should only have": "Conditional (should only have)",
    }
    mapped = df["modality"].map(modality_map).fillna(df["modality"])
    modality_counts = mapped.value_counts().reset_index()
    modality_counts.columns = ["modality", "count"]
    fig = px.pie(
        modality_counts,
        names="modality",
        values="count",
        color_discrete_sequence=COLORS,
        title="Modality Distribution",
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>%{value} obligations (%{percent})<extra></extra>",
    )
    fig.update_layout(
        showlegend=True, legend_title_text="Modality", margin=dict(t=50, b=0, l=0, r=0)
    )
    st.plotly_chart(fig, use_container_width=True)

with col4:
    cond_counts = (
        df["condition"]
        .replace("", float("nan"))
        .isna()
        .map({True: "Unconditional", False: "Conditional"})
        .value_counts()
        .reset_index()
    )
    cond_counts.columns = ["type", "count"]
    fig = px.pie(
        cond_counts,
        names="type",
        values="count",
        color_discrete_sequence=COLORS,
        title="Conditional vs Unconditional Obligations",
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>%{value} obligations (%{percent})<extra></extra>",
    )
    fig.update_layout(showlegend=True, margin=dict(t=50, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### 2. Semantic Clustering")
N_CLUSTERS = st.slider("Number of clusters", 2, 10, 5)

texts = (
    df["actor"].fillna("")
    + " "
    + df["action"].fillna("")
    + " "
    + df["condition"].fillna("")
).str.strip()

empty_mask = texts == ""
df_cluster = df[~empty_mask].copy()
texts = texts[~empty_mask]

if len(df_cluster) < N_CLUSTERS:
    st.warning(f"Not enough data rows ({len(df_cluster)}) for {N_CLUSTERS} clusters.")
    st.stop()

vectorizer = TfidfVectorizer(stop_words="english", max_features=200, ngram_range=(1, 2))
X = vectorizer.fit_transform(texts)

km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=20)
df_cluster["cluster_id"] = km.fit_predict(X)
df = df.drop(columns=["cluster_id"], errors="ignore").join(df_cluster["cluster_id"])

col5, col6 = st.columns(2)

with col5:
    cluster_sizes = df.groupby("cluster_id").size().sort_values().reset_index()
    cluster_sizes.columns = ["cluster_id", "count"]
    cluster_sizes["label"] = "Cluster " + cluster_sizes["cluster_id"].astype(str)
    fig = px.bar(
        cluster_sizes,
        x="count",
        y="label",
        orientation="h",
        color="label",
        color_discrete_sequence=COLORS,
        title="Obligations per Cluster",
        labels={"count": "Number of Obligations", "label": ""},
    )
    fig.update_layout(showlegend=False, margin=dict(t=50, b=0, l=0, r=0))
    fig.update_traces(hovertemplate="%{y}<br>%{x} obligations<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

with col6:
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X.toarray())
    df_cluster["pca_x"] = coords[:, 0]
    df_cluster["pca_y"] = coords[:, 1]
    df_cluster["cluster_label"] = "Cluster " + df_cluster["cluster_id"].astype(str)

    fig = px.scatter(
        df_cluster,
        x="pca_x",
        y="pca_y",
        color="cluster_label",
        color_discrete_sequence=COLORS,
        hover_data={
            "actor": True,
            "action": True,
            "modality": True,
            "pca_x": False,
            "pca_y": False,
            "cluster_label": False,
        },
        labels={
            "pca_x": f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)",
            "pca_y": f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)",
            "cluster_label": "Cluster",
        },
        title="Semantic Clusters (PCA 2-D Projection)",
    )
    fig.update_traces(
        marker=dict(size=9, opacity=0.75, line=dict(width=0.5, color="white"))
    )
    fig.update_layout(legend_title_text="Cluster", margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig, width="stretch")

with st.expander("Cluster details"):
    for cid in sorted(df_cluster["cluster_id"].unique()):
        subset = df_cluster[df_cluster["cluster_id"] == cid][
            ["paragraph", "actor", "action"]
        ]
        st.markdown(f"**Cluster {cid}** — {len(subset)} obligations")
        st.dataframe(subset.reset_index(drop=True), width="stretch")

st.markdown("### 3. Actor -> Action Network")


def shorten(s, n=35):
    s = str(s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


G = nx.DiGraph()
for _, row in df.iterrows():
    actor = shorten(row["actor"])
    action_words = str(row["action"]).split()
    action = " ".join(action_words[:5]) + ("…" if len(action_words) > 5 else "")
    G.add_node(actor, node_type="actor")
    G.add_node(action, node_type="action")
    G.add_edge(
        actor,
        action,
        modality=row.get("modality", ""),
        cluster_id=row.get("cluster_id", 0),
    )

all_actor_nodes = [n for n, d in G.nodes(data=True) if d["node_type"] == "actor"]
top_actors = sorted(all_actor_nodes, key=lambda n: G.out_degree(n), reverse=True)[:20]
nodes_to_keep = set(top_actors)
for a in top_actors:
    nodes_to_keep.update(G.successors(a))
G = G.subgraph(nodes_to_keep).copy()

actor_nodes = [n for n, d in G.nodes(data=True) if d["node_type"] == "actor"]
action_nodes = [n for n, d in G.nodes(data=True) if d["node_type"] == "action"]
pos = nx.spring_layout(G, k=1.2, seed=42, iterations=150)

all_modalities = sorted(
    {d.get("modality", "") for _, _, d in G.edges(data=True)} - {""}
)
MODALITY_COLOR = {mod: COLORS[i % len(COLORS)] for i, mod in enumerate(all_modalities)}


def dominant_cluster(node):
    clusters = [
        d["cluster_id"] for _, _, d in G.in_edges(node, data=True) if "cluster_id" in d
    ]
    return max(set(clusters), key=clusters.count) if clusters else 0


traces = []

edges_by_modality: dict[str, list] = {}
for u, v, data in G.edges(data=True):
    mod = data.get("modality", "other")
    edges_by_modality.setdefault(mod, []).append((u, v))

for mod, edge_list in edges_by_modality.items():
    ex, ey, hover = [], [], []
    for u, v in edge_list:
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        ex += [x0, x1, None]
        ey += [y0, y1, None]
        hover += [f"{u} → {v} ({mod})", f"{u} → {v} ({mod})", None]
    color = MODALITY_COLOR.get(mod, "#aaa")
    traces.append(
        go.Scatter(
            x=ex,
            y=ey,
            mode="lines",
            line=dict(width=1.2, color=color),
            hoverinfo="text",
            hovertext=hover,
            opacity=0.55,
            name=mod,
            legendgroup=mod,
        )
    )

ax_x = [pos[n][0] for n in action_nodes]
ax_y = [pos[n][1] for n in action_nodes]
ax_colors = [COLORS[dominant_cluster(n) % len(COLORS)] for n in action_nodes]
traces.append(
    go.Scatter(
        x=ax_x,
        y=ax_y,
        mode="markers",
        marker=dict(
            size=8, color=ax_colors, opacity=0.65, line=dict(width=0.5, color="white")
        ),
        hoverinfo="text",
        hovertext=[
            f"<b>Action:</b> {n}<br>Cluster {dominant_cluster(n)}" for n in action_nodes
        ],
        name="Action nodes",
        showlegend=True,
    )
)

ac_x = [pos[n][0] for n in actor_nodes]
ac_y = [pos[n][1] for n in actor_nodes]
ac_sizes = [12 + 3 * G.out_degree(n) for n in actor_nodes]
traces.append(
    go.Scatter(
        x=ac_x,
        y=ac_y,
        mode="markers+text",
        marker=dict(
            size=ac_sizes,
            color="#2C3E50",
            opacity=0.92,
            line=dict(width=1, color="white"),
        ),
        text=actor_nodes,
        textposition="bottom center",
        textfont=dict(size=9, color="#1a1a1a"),
        hoverinfo="text",
        hovertext=[
            f"<b>{n}</b><br>{G.out_degree(n)} obligation(s)" for n in actor_nodes
        ],
        name="Actor nodes",
        showlegend=True,
    )
)

fig = go.Figure(
    data=traces,
    layout=go.Layout(
        title="Top 20 Actors",
        showlegend=True,
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#F8F9FA",
        margin=dict(t=50, b=20, l=20, r=20),
        height=650,
    ),
)

st.plotly_chart(fig, width="stretch")
