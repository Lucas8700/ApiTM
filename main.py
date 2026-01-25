from dotenv import load_dotenv
from nadeo_api.auth import get_token
from nadeo_api import auth
import os
from nadeo_api_class import NadeoLiveAPI
from nadeo_api_class import NadeoOAuthAPI
from DataBaseUtils import GameDatabase


load_dotenv()  # charge le fichier .env

EMAIL = os.getenv("UBISOFT_EMAIL")
PASSWORD = os.getenv("UBISOFT_PASSWORD")

tokenCore = get_token(
    audience= auth.audience_oauth,
    username='bdb0007074994c7fda87',
    password='ac8de4fc2da739a81fb98336554b6d6cf13f4d71',
)

tokenLive = get_token(
    audience= auth.audience_live,
    username=EMAIL,
    password=PASSWORD,
    agent="ApiTM/1.0"
)

db = GameDatabase()



# Add Month to Databse
apiLive = NadeoLiveAPI(tokenLive)

df_totd_maps = apiLive.get_totd_maps(
    length=1, # Mois
    offset=1  # Offset Mois+
)

for _, row in df_totd_maps.iterrows():
# for _, row in df_totd_maps.iloc[:2].iterrows():
    print(row["startDatetime"])

    fb_players_with_author = apiLive.get_players_with_author(
        group_uid="Personal_Best",
        map_uid=row["mapUid"]
    )

    for _, playerRow in fb_players_with_author.iterrows():
        db.add_player(playerRow["player"]) 
        db.set_record(
            player_identifier=playerRow["player"],
            map_id=row["mapUid"],
            score=playerRow["score"])


rows = db.get_players_by_record_count_cursor(limit=50, ascending=False)


apiCore = NadeoOAuthAPI(tokenCore)
name = [name for _, name, _ in rows]
df = apiCore.get_display_names(name)

id_to_display = dict(
    zip(df["accountId"], df["displayName"])
)

for player_id, name, count in rows:
    display_name = id_to_display.get(name, "Unknown")
    print(f"{name} ({display_name}) (ID {player_id}) a {count} record(s)")
