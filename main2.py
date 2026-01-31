from dotenv import load_dotenv
from nadeo_api.auth import get_token
from nadeo_api import auth
import os
from nadeo_api_class import NadeoLiveAPI
from nadeo_api_class import NadeoOAuthAPI
from DataBaseUtils2 import GameDatabase


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

apiCore = NadeoOAuthAPI(tokenCore)

# Add Month to Databse
apiLive = NadeoLiveAPI(tokenLive)

df_totd_maps = apiLive.get_totd_maps(
    length=1, # Mois
    offset=0  # Offset Mois+
)

for _, row in df_totd_maps.iterrows():
# for _, row in df_totd_maps.iloc[:2].iterrows():

    print(f"Filling map for {row['year']}-{row['month']:02d}-{row['monthDay']:02d}")
    db.fill_map_with_author_medals(row, apiLive)

db.update_player_names(apiCore)