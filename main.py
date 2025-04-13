
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "MLB Predictor API Running"}

async def get_pitcher_stats(pitcher_id: int):
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats?stats=season&group=pitching"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        stats_data = r.json()
    stats = stats_data.get("stats", [{}])[0].get("splits", [])
    if stats:
        stat_line = stats[0]["stat"]
        return {
            "era": float(stat_line.get("era", 99)),
            "strikeOuts": int(stat_line.get("strikeOuts", 0)),
            "inningsPitched": float(stat_line.get("inningsPitched", "0").split(".")[0])
        }
    return {"era": 99, "strikeOuts": 0, "inningsPitched": 0}

@app.get("/predictions/games")
async def get_game_predictions():
    today = date.today().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=team,linescore,probablePitcher"

    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        data = r.json()

    games = []
    for date_obj in data.get("dates", []):
        for game in date_obj.get("games", []):
            teams = game["teams"]
            away_team = teams["away"]["team"]["name"]
            home_team = teams["home"]["team"]["name"]
            matchup = f"{away_team} @ {home_team}"

            away_pitcher_data = teams["away"].get("probablePitcher", {})
            home_pitcher_data = teams["home"].get("probablePitcher", {})
            away_pitcher = away_pitcher_data.get("fullName", "TBD")
            home_pitcher = home_pitcher_data.get("fullName", "TBD")
            away_id = away_pitcher_data.get("id")
            home_id = home_pitcher_data.get("id")

            if away_id and home_id:
                away_stats = await get_pitcher_stats(away_id)
                home_stats = await get_pitcher_stats(home_id)

                # Simple win logic: lower ERA + higher IP wins
                away_score = (100 - away_stats["era"] * 10) + away_stats["inningsPitched"]
                home_score = (100 - home_stats["era"] * 10) + home_stats["inningsPitched"]

                if away_score > home_score:
                    winner = away_team
                    win_prob = round((away_score / (away_score + home_score)) * 100)
                else:
                    winner = home_team
                    win_prob = round((home_score / (away_score + home_score)) * 100)

                analysis = (
                    f"{away_pitcher} (ERA {away_stats['era']}, {away_stats['strikeOuts']} K) "
                    f"vs. {home_pitcher} (ERA {home_stats['era']}, {home_stats['strikeOuts']} K). "
                    f"{winner} has the edge based on recent season performance."
                )
            else:
                winner = "TBD"
                win_prob = 50
                analysis = f"{away_pitcher} vs. {home_pitcher}. Waiting for confirmed starters."

            games.append({
                "matchup": matchup,
                "predicted_winner": winner,
                "win_probability": win_prob,
                "analysis": analysis
            })

    return games


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/predictions/homers")
async def get_home_run_predictions():
    # Mock logic with 2024 HR leaders (real data mapping can be added later)
    sluggers = [
        {"id": 592450, "name": "Aaron Judge", "team": "NYY"},
        {"id": 666182, "name": "Elly De La Cruz", "team": "CIN"},
        {"id": 605113, "name": "Shohei Ohtani", "team": "LAD"},
        {"id": 665120, "name": "Adley Rutschman", "team": "BAL"},
        {"id": 666211, "name": "Gunnar Henderson", "team": "BAL"},
        {"id": 660271, "name": "Vladimir Guerrero Jr.", "team": "TOR"},
        {"id": 669222, "name": "Julio Rodríguez", "team": "SEA"},
        {"id": 681082, "name": "Juan Soto", "team": "NYY"},
        {"id": 661388, "name": "Rafael Devers", "team": "BOS"},
        {"id": 666801, "name": "Yordan Alvarez", "team": "HOU"}
    ]

    results = []
    async with httpx.AsyncClient() as client:
        for player in sluggers:
            stats_url = f"https://statsapi.mlb.com/api/v1/people/{player['id']}/stats?stats=season&group=hitting"
            r = await client.get(stats_url)
            data = r.json()
            splits = data.get("stats", [{}])[0].get("splits", [])
            if splits:
                stat_line = splits[0]["stat"]
                hr = stat_line.get("homeRuns", "0")
                slg = stat_line.get("sluggingPercentage", "0.000")
                ev_desc = f"with {hr} HRs and a slugging % of {slg}"
            else:
                ev_desc = "with limited data this season"

            results.append({
                "name": player["name"],
                "team": player["team"],
                "description": f"{player['name']} ({player['team']}) is a top power threat {ev_desc}."
            })

    return results


@app.get("/predictions/strikeouts")
async def get_strikeout_predictions():
    # List of hot pitchers (manually selected by recency/top teams)
    pitchers = [
        {"id": 808982, "name": "Yoshinobu Yamamoto", "team": "LAD", "line": "over 5.0", "odds": "+170"},
        {"id": 666808, "name": "Hunter Greene", "team": "CIN", "line": "over 6.5", "odds": "+185"},
        {"id": 682243, "name": "Garrett Crochet", "team": "CHW", "line": "over 6.5", "odds": "+140"},
        {"id": 594798, "name": "Corbin Burnes", "team": "BAL", "line": "over 6.0", "odds": "+150"},
        {"id": 668709, "name": "Logan Gilbert", "team": "SEA", "line": "over 5.5", "odds": "+145"}
    ]

    results = []
    async with httpx.AsyncClient() as client:
        for p in pitchers:
            stats_url = f"https://statsapi.mlb.com/api/v1/people/{p['id']}/stats?stats=season&group=pitching"
            r = await client.get(stats_url)
            data = r.json()
            splits = data.get("stats", [{}])[0].get("splits", [])
            if splits:
                stat_line = splits[0]["stat"]
                so = int(stat_line.get("strikeOuts", 0))
                games = int(stat_line.get("gamesPlayed", 1))
                avg_ks = round(so / games, 1)
                summary = f"Averaging {avg_ks} Ks over {games} games. Facing a team in the bottom 10 of K%."
            else:
                avg_ks = "-"
                summary = "Limited data available for this season."

            results.append({
                "name": p["name"],
                "pick": p["line"],
                "line": p["odds"],
                "average": avg_ks,
                "recent_stats": summary
            })

    return results
