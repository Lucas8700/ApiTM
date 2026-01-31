import pandas as pd
from datetime import datetime
from collections import Counter
import nadeo_api.live as live
import nadeo_api.oauth as oauth
import re

class NadeoLiveAPI:
    def __init__(self, token):
        """
        Classe pour interagir avec l'API Nadeo Live.
        
        Args:
            token (str): Token d'authentification valide
        """
        self.token = token

    def get_totd_maps(self, length=1, offset=1):
        """
        Récupère les maps TOTD et retourne un DataFrame.
        """
        data = live.get_maps_totd(token=self.token, length=length, offset=offset)
        records = []

        for month in data.get("monthList", []):
            year = month.get("year")
            month_num = month.get("month")
            for day in month.get("days", []):
                record = {
                    "year": year,
                    "month": month_num,
                    "monthDay": day.get("monthDay"),
                    "mapUid": day.get("mapUid")
                }
                records.append(record)

        return pd.DataFrame(records)

    def get_map_info(self, map_uid):
        """
        Récupère les informations d'une map spécifique.
        """
        endpoint = f"/api/token/map/{map_uid}"
        data = live.get(token=self.token, endpoint=endpoint)
        return {
            "uid": data.get("uid"),
            "name": data.get("name"),
            "author": data.get("author"),
            "authorTime": data.get("authorTime"),
            "goldTime": data.get("goldTime")
        }

    def get_map_top(self, group_uid, map_uid, length=50, only_world=True, offset=0):
        """
        Récupère le top leaderboard d'une map.
        """
        data = live.get_map_leaderboard(token=self.token, mapUid=map_uid, groupUid=group_uid, length=length, onlyWorld=only_world, offset=offset)
        records = []

        for top_zone in data.get("tops", []):
            for entry in top_zone.get("top", []):
                records.append({
                    "mapUid": data.get("mapUid"),
                    "accountId": entry.get("accountId"),
                    "score": entry.get("score")
                })
        return pd.DataFrame(records)

    def get_players_with_author(self, group_uid: str, map_uid: str) -> pd.DataFrame:
        """
        Récupère les joueurs ayant la médaille Auteur sur une map.
        
        Args:
            group_uid (str): identifiant du groupe de leaderboard (ex: 'Personal_Best')
            map_uid (str): identifiant de la map
        
        Returns:
            pd.DataFrame: DataFrame avec les colonnes :
                - Player : accountId du joueur
                - Score : score obtenu sur la map
        """
        map_info = self.get_map_info(map_uid)
        author_time = map_info.get("authorTime")
        if author_time is None:
            return pd.DataFrame(columns=["Player", "Score"])

        players_with_author = []
        offset = 0
        last_player_above_author = True

        while last_player_above_author:
            if (offset+100) > 10000:
                last_player_above_author = False
                break
            df_leader = self.get_map_top(group_uid=group_uid, map_uid=map_uid, length=100, offset=offset)
            for _, row in df_leader.iterrows():
                if row["score"] <= author_time:
                    players_with_author.append({
                        "player": row["accountId"],
                        "score": row["score"]
                    })
                else:
                    last_player_above_author = False
                    break
            offset += 100

        return pd.DataFrame(players_with_author)

class NadeoOAuthAPI:
    def __init__(self, token):
        """
        Classe pour interagir avec l'API Nadeo Core.
        
        Args:
            token (str): Token d'authentification valide
        """
        self.token = token

    def get_display_names(self, accountId):
        """
        Récupère les display names pour une liste d'accountId et retourne un DataFrame.
        
        Args:
            account_ids (list[str]): Liste d'accountId Trackmania.

        Returns:
            pd.DataFrame: colonnes ['accountId', 'displayName']
        """
        data = oauth.get_account_names_from_ids(
           token=self.token,
           account_ids=accountId)
        
        # data = {'uuid': 'name', ...}
        df = pd.DataFrame(
            data.items(),
            columns=["accountId", "displayName"]
        )

        return df



TM_COLOR_RE = re.compile(r"\$([0-9a-fA-F]{3})")

def tm2020_to_html(text: str) -> str:
    html = ""
    i = 0
    open_spans = []

    def close_all():
        nonlocal html, open_spans
        while open_spans:
            html += open_spans.pop()

    while i < len(text):
        if text[i] == "$" and i + 1 < len(text):
            code = text[i + 1]

            # Escaped dollar
            if code == "$":
                html += "$"
                i += 2
                continue

            # Italic
            if code == "i":
                html += "<span style='font-style: italic;'>"
                open_spans.append("</span>")
                i += 2
                continue

            # Bold
            if code == "o":
                html += "<span style='font-weight: bold;'>"
                open_spans.append("</span>")
                i += 2
                continue

            # Wide
            if code == "w":
                html += "<span style='letter-spacing: 0.15em;'>"
                open_spans.append("</span>")
                i += 2
                continue

            # Shadow
            if code == "s":
                html += (
                    "<span style='text-shadow: "
                    "1px 1px 2px rgba(0,0,0,0.6);'>"
                )
                open_spans.append("</span>")
                i += 2
                continue

            # Reset
            if code in ("n", "z"):
                close_all()
                i += 2
                continue

            # Gradient (approximation)
            if code == "G":
                html += (
                    "<span style='"
                    "background: linear-gradient(90deg, #ff00ff, #00ffff);"
                    "background-clip: text;"
                    "-webkit-background-clip: text;"
                    "color: transparent;'>"
                )
                open_spans.append("</span>")
                i += 2
                continue

            # Color ($f6f etc.)
            match = TM_COLOR_RE.match(text, i)
            if match:
                color = match.group(1)
                html += f"<span style='color: #{color};'>"
                open_spans.append("</span>")
                i += 4
                continue

        # Normal character
        html += text[i]
        i += 1

    close_all()
    return html