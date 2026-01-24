import pandas as pd
from datetime import datetime
from collections import Counter
import nadeo_api.live as live
import nadeo_api.live as core

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
                    "day": day.get("day"),
                    "monthDay": day.get("monthDay"),
                    "campaignId": day.get("campaignId"),
                    "mapUid": day.get("mapUid"),
                    "seasonUid": day.get("seasonUid"),
                    "leaderboardGroup": day.get("leaderboardGroup"),
                    "startTimestamp": day.get("startTimestamp"),
                    "endTimestamp": day.get("endTimestamp"),
                    "startDatetime": datetime.fromtimestamp(day.get("startTimestamp")),
                    "endDatetime": datetime.fromtimestamp(day.get("endTimestamp"))
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
            "mapId": data.get("mapId"),
            "name": data.get("name"),
            "author": data.get("author"),
            "submitter": data.get("submitter"),
            "authorTime": data.get("authorTime"),
            "goldTime": data.get("goldTime"),
            "silverTime": data.get("silverTime"),
            "bronzeTime": data.get("bronzeTime"),
            "nbLaps": data.get("nbLaps"),
            "valid": data.get("valid"),
            "downloadUrl": data.get("downloadUrl"),
            "thumbnailUrl": data.get("thumbnailUrl"),
            "uploadTimestamp": data.get("uploadTimestamp"),
            "updateTimestamp": data.get("updateTimestamp"),
            "fileSize": data.get("fileSize"),
            "public": data.get("public"),
            "favorite": data.get("favorite"),
            "playable": data.get("playable"),
            "mapStyle": data.get("mapStyle"),
            "mapType": data.get("mapType"),
            "collectionName": data.get("collectionName")
        }

    def get_map_top(self, group_uid, map_uid, length=50, only_world=True, offset=0):
        """
        Récupère le top leaderboard d'une map.
        """
        endpoint = (
            f"api/token/leaderboard/group/{group_uid}/map/{map_uid}/top"
            f"?length={length}&onlyWorld={str(only_world).lower()}&offset={offset}"
        )
        data = live.get(token=self.token, endpoint=endpoint)
        records = []

        for top_zone in data.get("tops", []):
            zone_id = top_zone.get("zoneId")
            zone_name = top_zone.get("zoneName")
            for entry in top_zone.get("top", []):
                records.append({
                    "groupUid": data.get("groupUid"),
                    "mapUid": data.get("mapUid"),
                    "zoneId": zone_id,
                    "zoneName": zone_name,
                    "accountId": entry.get("accountId"),
                    "position": entry.get("position"),
                    "score": entry.get("score"),
                    "timestamp": entry.get("timestamp"),
                    "datetime": datetime.fromtimestamp(entry.get("timestamp"))
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

class NadeoCoreAPI:
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
        # Appel API via core.get pour rester cohérent avec ton code
        endpoint = (
            f"/api/display-names?accountId[]={accountId}"
        )
        data = core.get(token=self.token, endpoint=endpoint)

        # data = {accountId: displayName}
        records = [{"accountId": aid, "displayName": name} for aid, name in data.items()]

        return pd.DataFrame(records)
