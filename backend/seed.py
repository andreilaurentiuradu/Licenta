"""
Database seeder.

Reads data.csv (800 players), splits among 3 teams, fits the scaler,
trains an initial global model, and creates demo users.

Run: python seed.py
"""

import os
import sys
import json
import numpy as np
import pandas as pd

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.team import Team
from app.models.player import Player, PlayerMetrics
from app.models.prediction import Prediction
from app.ml.model import NeuralNetwork, POSITION_CLASSES, NUMERICAL_FEATURES
from app.ml.predictor import save_global_model, save_scaler

PLAYER_NAMES = [
    "Alexandru Ionescu", "Bogdan Popescu", "Cătălin Dumitrescu", "Dan Georgescu",
    "Emil Stanescu", "Florin Constantin", "Gheorghe Marin", "Horia Popa",
    "Ioan Draghici", "Julien Lacroix", "Kevin Müller", "Lorenzo Ricci",
    "Marco Ferrari", "Nicolas Dupont", "Oliver Schmidt", "Pierre Martin",
    "Rafael Gomez", "Samuel Weber", "Thomas Fischer", "Victor Hugo",
    "Adrian Barbu", "Bogdan Lazar", "Cosmin Tudose", "Dragos Mihai",
    "Eduard Cristea", "Florin Nitu", "Gabi Popa", "Horatiu Oancea",
    "Ionut Ciobanu", "Javier Morales", "Krisztian Toth", "Lucas Mendez",
    "Mihai Neagu", "Niculae Dobre", "Octavian Rosca", "Petre Vasile",
    "Razvan Stoica", "Sorin Florescu", "Tudor Oprea", "Valentin Moise",
    "Andrei Pascu", "Bogdan Hrib", "Ciprian Serban", "Doru Blaj",
    "Emilian Chirita", "Flavius Coman", "George Bucur", "Horia Pintea",
    "Iulian Duta", "Jean-Paul Renard", "Karl Hoffman", "Leonardo Santos",
    "Manuel Torres", "Nicusor Dobre", "Orlando Vasquez", "Patrick Meyer",
    "Quentin Bernard", "Radu Jipa", "Stefan Badea", "Tiberiu Morar",
    "Vasile Petre", "Willem de Jong", "Xavi Alonso", "Yannick Perrin",
]

NATIONALITIES = [
    "Romanian", "Romanian", "Romanian", "Romanian", "Romanian",
    "French", "German", "Italian", "Spanish", "Dutch",
    "Portuguese", "Brazilian", "Argentine", "Croatian", "Czech",
]


def get_name(idx: int) -> str:
    if idx < len(PLAYER_NAMES):
        return PLAYER_NAMES[idx]
    return f"Player {idx + 1}"


def get_nationality(idx: int) -> str:
    return NATIONALITIES[idx % len(NATIONALITIES)]


def main():
    app = create_app("development")
    data_csv = os.path.join(os.path.dirname(__file__), "..", "data.csv")

    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database tables created.")

        # ----- Teams ---------------------------------------------------------
        teams_data = [
            {"name": "FC Analytics United", "city": "Bucharest"},
            {"name": "Sport Tech FC",        "city": "Cluj-Napoca"},
            {"name": "Data Driven SC",       "city": "Timișoara"},
        ]
        teams = []
        for td in teams_data:
            t = Team(name=td["name"], city=td["city"], sport="Football", fl_participant=True)
            db.session.add(t)
            teams.append(t)
        db.session.flush()
        print(f"Created {len(teams)} teams.")

        # ----- Users ---------------------------------------------------------
        users_data = [
            # team 0
            {"username": "admin",   "email": "admin@fcau.ro",    "password": "admin123",  "role": "admin",   "team": 0},
            {"username": "coach1",  "email": "coach@fcau.ro",    "password": "coach123",  "role": "coach",   "team": 0},
            {"username": "medical1","email": "medical@fcau.ro",  "password": "medical123","role": "medical", "team": 0},
            # team 1
            {"username": "admin2",  "email": "admin@stfc.ro",    "password": "admin123",  "role": "admin",   "team": 1},
            {"username": "coach2",  "email": "coach@stfc.ro",    "password": "coach123",  "role": "coach",   "team": 1},
            # team 2
            {"username": "admin3",  "email": "admin@ddsc.ro",    "password": "admin123",  "role": "admin",   "team": 2},
            {"username": "coach3",  "email": "coach@ddsc.ro",    "password": "coach123",  "role": "coach",   "team": 2},
        ]
        for ud in users_data:
            u = User(username=ud["username"], email=ud["email"], role=ud["role"],
                     team_id=teams[ud["team"]].id)
            u.set_password(ud["password"])
            db.session.add(u)
        db.session.commit()
        print(f"Created {len(users_data)} users.")

        # ----- Load CSV + fit scaler ----------------------------------------
        df = pd.read_csv(data_csv)
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

        num_cols = NUMERICAL_FEATURES  # 17 columns

        # Map CSV column names to the model feature names (they already match)
        num_data = df[num_cols].values.astype(float)
        mean = num_data.mean(axis=0).tolist()
        std  = num_data.std(axis=0).tolist()
        scaler = {"mean": mean, "std": std}
        os.makedirs(app.config["MODEL_DIR"], exist_ok=True)
        save_scaler(scaler)
        print("Scaler fitted and saved.")

        # ----- Split data into 3 teams (40/33/27) ---------------------------
        n = len(df)
        splits = [int(n * 0.40), int(n * 0.33)]
        splits.append(n - splits[0] - splits[1])
        boundaries = [0, splits[0], splits[0]+splits[1], n]

        all_X, all_y = [], []
        player_idx = 0

        for team_idx, team in enumerate(teams):
            start, end = boundaries[team_idx], boundaries[team_idx + 1]
            chunk = df.iloc[start:end].reset_index(drop=True)

            for i, row in chunk.iterrows():
                player = Player(
                    full_name=get_name(player_idx),
                    position=row["Position"],
                    age=int(row["Age"]),
                    height_cm=float(row["Height_cm"]),
                    weight_kg=float(row["Weight_kg"]),
                    nationality=get_nationality(player_idx),
                    status="active",
                    team_id=team.id,
                )
                db.session.add(player)
                db.session.flush()

                metrics = PlayerMetrics(
                    player_id=player.id,
                    training_hours_per_week=float(row["Training_Hours_Per_Week"]),
                    matches_played_past_season=int(row["Matches_Played_Past_Season"]),
                    previous_injury_count=int(row["Previous_Injury_Count"]),
                    knee_strength_score=float(row["Knee_Strength_Score"]),
                    hamstring_flexibility=float(row["Hamstring_Flexibility"]),
                    reaction_time_ms=float(row["Reaction_Time_ms"]),
                    balance_test_score=float(row["Balance_Test_Score"]),
                    sprint_speed_10m_s=float(row["Sprint_Speed_10m_s"]),
                    agility_score=float(row["Agility_Score"]),
                    sleep_hours_per_night=float(row["Sleep_Hours_Per_Night"]),
                    stress_level_score=float(row["Stress_Level_Score"]),
                    nutrition_quality_score=float(row["Nutrition_Quality_Score"]),
                    warmup_routine_adherence=float(row["Warmup_Routine_Adherence"]),
                )
                db.session.add(metrics)

                # Build feature vector for training
                nums = [
                    row["Age"], row["Height_cm"], row["Weight_kg"], row["BMI"],
                    row["Training_Hours_Per_Week"], row["Matches_Played_Past_Season"],
                    row["Previous_Injury_Count"], row["Knee_Strength_Score"],
                    row["Hamstring_Flexibility"], row["Reaction_Time_ms"],
                    row["Balance_Test_Score"], row["Sprint_Speed_10m_s"],
                    row["Agility_Score"], row["Sleep_Hours_Per_Night"],
                    row["Stress_Level_Score"], row["Nutrition_Quality_Score"],
                    row["Warmup_Routine_Adherence"],
                ]
                all_X.append(nums)
                all_y.append(int(row["Injury_Next_Season"]))
                player_idx += 1

            team.local_data_points = end - start

        db.session.commit()
        print(f"Created {player_idx} players with metrics.")

        # ----- Train initial global model -----------------------------------
        X = np.array(all_X, dtype=float)
        y = np.array(all_y, dtype=float)

        # Standardise using fitted scaler
        m_arr = np.array(mean)
        s_arr = np.array(std)
        s_arr = np.where(s_arr == 0, 1.0, s_arr)
        X_norm = (X - m_arr) / s_arr

        # One-hot encode position
        positions = df["Position"].values
        pos_enc = np.array([
            [1.0 if cls == pos else 0.0 for cls in POSITION_CLASSES]
            for pos in positions
        ])
        X_full = np.hstack([X_norm, pos_enc])

        model = NeuralNetwork(seed=42)
        stats = model.train(X_full, y, epochs=50, lr=0.01)
        save_global_model(model)

        print(f"Initial global model trained — accuracy: {stats['accuracy']:.4f}, loss: {stats['loss']:.4f}")

        # ----- Run initial predictions for all players ----------------------
        from app.ml.predictor import load_scaler, load_global_model as lgm
        scaler_loaded = load_scaler()
        global_model = lgm()

        players_all = Player.query.all()
        pred_count = 0
        for player in players_all:
            latest = (
                PlayerMetrics.query.filter_by(player_id=player.id)
                .order_by(PlayerMetrics.recorded_at.desc())
                .first()
            )
            if not latest:
                continue

            nums = [
                player.age, player.height_cm, player.weight_kg, player.bmi or 0,
                latest.training_hours_per_week, latest.matches_played_past_season,
                latest.previous_injury_count, latest.knee_strength_score,
                latest.hamstring_flexibility, latest.reaction_time_ms,
                latest.balance_test_score, latest.sprint_speed_10m_s,
                latest.agility_score, latest.sleep_hours_per_night,
                latest.stress_level_score, latest.nutrition_quality_score,
                latest.warmup_routine_adherence,
            ]
            nums_arr = np.array(nums, dtype=float)
            m_a = np.array(scaler_loaded["mean"])
            s_a = np.array(scaler_loaded["std"])
            s_a = np.where(s_a == 0, 1.0, s_a)
            nums_norm = (nums_arr - m_a) / s_a

            pos_v = np.array([1.0 if cls == player.position else 0.0 for cls in POSITION_CLASSES])
            X_p = np.concatenate([nums_norm, pos_v]).reshape(1, -1)

            score = float(global_model.predict_proba(X_p)[0])
            level = "low" if score < 0.35 else ("medium" if score < 0.65 else "high")

            pred = Prediction(
                player_id=player.id,
                injury_risk_score=score,
                risk_level=level,
                model_version=0,
                metrics_id=latest.id,
            )
            db.session.add(pred)
            pred_count += 1

        db.session.commit()
        print(f"Generated {pred_count} initial predictions.")
        print("\n=== Seed complete ===")
        print("Demo credentials:")
        print("  admin@fcau.ro / admin123  (FC Analytics United — admin)")
        print("  coach@fcau.ro / coach123  (FC Analytics United — coach)")
        print("  admin@stfc.ro / admin123  (Sport Tech FC — admin)")
        print("  admin@ddsc.ro / admin123  (Data Driven SC — admin)")


if __name__ == "__main__":
    main()
