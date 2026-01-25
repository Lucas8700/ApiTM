import streamlit as st
import pandas as pd
from DataBaseUtils import GameDatabase
from nadeo_api_class import NadeoOAuthAPI
from nadeo_api import auth
from nadeo_api.auth import get_token
import plotly.express as px

# Configuration de la page
st.set_page_config(
    page_title="TrackMania Players Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Titre principal
st.title("🏎️ TrackMania Players Dashboard")
st.markdown("Visualisez les meilleurs joueurs et leurs records")

# Initialiser la connexion à la base de données
@st.cache_resource
def get_database():
    return GameDatabase()

@st.cache_resource
def get_api_client():
    try:
        tokenCore = get_token(
            audience=auth.audience_oauth,
            username='bdb0007074994c7fda87',
            password='ac8de4fc2da739a81fb98336554b6d6cf13f4d71',
        )
        return NadeoOAuthAPI(tokenCore)
    except Exception as e:
        st.error(f"Erreur lors de la connexion à l'API: {e}")
        return None

db = get_database()
api_client = get_api_client()

# Sidebar pour les filtres
st.sidebar.header("⚙️ Filtres")

# Récupérer les joueurs avec pagination
@st.cache_data
def load_all_players():
    """Charge tous les joueurs par batches de 50"""
    players_data = []
    last_count = None
    last_id = None
    
    while True:
        # Charger le batch suivant
        rows = db.get_players_by_record_count_cursor(
            last_count=last_count, 
            last_id=last_id, 
            limit=50, 
            ascending=False
        )
        
        if not rows:
            break
        
        # Récupérer les noms d'affichage pour ce batch
        if api_client:
            player_ids = [name for _, name, _ in rows]
            try:
                df_names = api_client.get_display_names(player_ids)
                id_to_display = dict(zip(df_names["accountId"], df_names["displayName"]))
            except:
                id_to_display = {}
        else:
            id_to_display = {}
        
        # Ajouter les joueurs du batch
        for player_id, name, count in rows:
            display_name = id_to_display.get(name, "Unknown")
            players_data.append({
                "ID": player_id,
                "Nom": name,
                "Nom d'affichage": display_name,
                "Nombre de records": count
            })
        
        # Préparer le curseur pour le batch suivant
        last_count = rows[-1][2]
        last_id = rows[-1][0]
    
    return pd.DataFrame(players_data)

# Charger les données
if st.sidebar.button("🔄 Actualiser les données"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

df_players = load_all_players()

if df_players.empty:
    st.warning("Aucun joueur trouvé dans la base de données.")
else:
    # Filtres
    min_records = st.sidebar.slider(
        "Nombre minimum de records",
        min_value=0,
        max_value=int(df_players["Nombre de records"].max()),
        value=0,
        step=1
    )
    
    search_name = st.sidebar.text_input(
        "🔍 Rechercher un joueur",
        placeholder="Entrez un nom..."
    )
    
    # Appliquer les filtres
    df_filtered = df_players[df_players["Nombre de records"] >= min_records]
    
    if search_name:
        df_filtered = df_filtered[
            df_filtered["Nom d'affichage"].str.contains(search_name, case=False, na=False) |
            df_filtered["Nom"].str.contains(search_name, case=False, na=False)
        ]
    
    # Afficher les statistiques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total joueurs", len(df_players))
    with col2:
        st.metric("🎯 Joueurs filtrés", len(df_filtered))
    with col3:
        st.metric("🏆 Max records", int(df_players["Nombre de records"].max()))
    with col4:
        st.metric("📈 Moyenne records", f"{df_players['Nombre de records'].mean():.1f}")
    
    # Afficher le graphique
    st.subheader("📈 Distribution des records")
    
    fig = px.histogram(
        df_players,
        x="Nombre de records",
        nbins=50,
        title="Distribution du nombre de records par joueur",
        labels={"Nombre de records": "Nombre de records", "count": "Nombre de joueurs"},
        color_discrete_sequence=["#FF6B6B"]
    )
    fig.update_layout(
        xaxis_title="Nombre de records",
        yaxis_title="Nombre de joueurs",
        hovermode="x unified",
        height=400
    )
    st.plotly_chart(fig, width='stretch')
    
    # Classement des meilleurs joueurs
    st.subheader("🏅 Top Joueurs")
    
    cols = st.columns(3)
    with cols[0]:
        st.write("**Tri par :**")
    with cols[1]:
        sort_by = st.selectbox(
            "Tri par",
            ["Nombre de records", "Nom d'affichage"],
            label_visibility="collapsed"
        )
    with cols[2]:
        ascending = st.checkbox("Ordre croissant")
    
    df_sorted = df_filtered.sort_values(
        by=sort_by,
        ascending=ascending
    )
    
    # Affichage du tableau avec pagination
    limit = st.slider("Nombre de joueurs à afficher", min_value=10, max_value=1000, value=50)
    df_display = df_sorted.head(limit).reset_index(drop=True)
    df_display.index = df_display.index + 1
    
    st.dataframe(
        df_display[["Nom d'affichage", "Nombre de records"]],
        width='stretch',
        height=min(600, 35 + len(df_display) * 35),
        column_config={
            "Nom d'affichage": st.column_config.TextColumn(width="medium"),
            "Nombre de records": st.column_config.NumberColumn(width="small"),
        }
    )
    
    # Détails d'un joueur sélectionné
    st.subheader("🎮 Détails d'un joueur")
    
    player_names = df_filtered["Nom d'affichage"].unique().tolist()
    selected_player = st.selectbox("Sélectionnez un joueur", player_names)
    
    if selected_player:
        player_data = df_filtered[df_filtered["Nom d'affichage"] == selected_player].iloc[0]
        player_id = player_data["ID"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👤 ID Joueur", player_id)
        with col2:
            st.metric("📍 Nom système", player_data["Nom"])
        with col3:
            st.metric("🏆 Records", player_data["Nombre de records"])
        
        # Afficher les records du joueur
        st.write("**Records détaillés :**")
        records = db.get_player_records(player_data["Nom"])
        
        if records:
            df_records = pd.DataFrame(records, columns=["Map ID", "Score"])
            df_records["Score"] = df_records["Score"].apply(lambda x: f"{x:,}")
            st.dataframe(df_records, width='stretch', hide_index=True)
        else:
            st.info("Ce joueur n'a pas encore de records.")
    
    # Graphique comparatif
    st.subheader("📊 Graphique du Top 20")
    
    df_top20 = df_filtered.nlargest(20, "Nombre de records")
    
    fig_top = px.bar(
        df_top20,
        x="Nom d'affichage",
        y="Nombre de records",
        title="Top 20 Joueurs",
        labels={"Nombre de records": "Records", "Nom d'affichage": "Joueur"},
        color="Nombre de records",
        color_continuous_scale="Viridis"
    )
    fig_top.update_layout(
        xaxis_tickangle=-45,
        height=500,
        hovermode="x unified"
    )
    st.plotly_chart(fig_top, width='stretch')

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 0.8em;'>
    TrackMania Players Dashboard | Données en temps réel
    </div>
    """,
    unsafe_allow_html=True
)
