from dotenv import load_dotenv
from nadeo_api.auth import get_token
import os
from nadeo_api_class import NadeoLiveAPI
from nadeo_api_class import NadeoCoreAPI
from DataBaseUtils import GameDatabase


load_dotenv()  # charge le fichier .env

EMAIL = os.getenv("UBISOFT_EMAIL")
PASSWORD = os.getenv("UBISOFT_PASSWORD")

tokenCore = get_token(
    audience="NadeoServices",
    username=EMAIL,
    password=PASSWORD,
    agent="ApiTM/1.0"
)

# tokenLive = get_token(
#     audience="NadeoLiveServices",
#     username=EMAIL,
#     password=PASSWORD,
#     agent="ApiTM/1.0"
# )

db = GameDatabase()
# apiLive = NadeoLiveAPI(tokenLive)
apiCore = NadeoCoreAPI(tokenCore)

# df_totd_maps = apiLive.get_totd_maps(
#     length=1,
#     offset=0
# )

# # for _, row in df_totd_maps.iterrows():
# for _, row in df_totd_maps.iloc[:2].iterrows():
#     print(row["startDatetime"])

#     fb_players_with_author = apiLive.get_players_with_author(
#         group_uid="Personal_Best",
#         map_uid=row["mapUid"]
#     )

#     for _, playerRow in fb_players_with_author.iterrows():
#         db.add_player(playerRow["player"]) 
#         db.set_record(
#             player_identifier=playerRow["player"],
#             map_id=row["mapUid"],
#             score=playerRow["score"])

# for player_id, name, count in db.get_players_by_record_count_cursor(limit=10, ascending=False):
#     print(f"{name} (ID {player_id}) a {count} record(s)")

id = "04b139f8-02b9-43bb-9312-39a2cea0a48c"
df = apiCore.get_display_names([id])
name = df.loc[0, "displayName"]

print("Records " , name, ":", db.get_player_records(id))

alice_count = db.get_player_record_count(id)
print(name," a", alice_count, "records")
