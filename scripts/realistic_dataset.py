"""
Transformă setul de date sintetic (prea ușor separabil, ~95% acuratețe) într-unul
mai realist, în două moduri ortogonale și interpretabile:

  1. Dezechilibru de clasă — subeșantionează clasa pozitivă (accidentare) astfel
     încât rata de bază (clasa majoritară = fără accidentare) să fie ~`--baseline`.
     Reflectă faptul că, în realitate, majoritatea sezoanelor nu se soldează cu o
     accidentare gravă.

  2. Zgomot pe etichetă — schimbă aleator etichete între clase, păstrând numărul
     pe clasă (swap pozitiv↔negativ). Reflectă incertitudinea reală: aceleași
     metrici pot duce sau nu la accidentare. Plafonează acuratețea atingibilă.

Caracteristicile (coloanele) NU sunt modificate — rămân metrici realiste de
sportiv. Se schimbă doar eticheta și se subeșantionează rândurile.

Raportează rata de bază și acuratețea/recall-ul cross-validat (5-fold), folosind
EXACT preprocesarea și modelul aplicației (fl.model), deci cifra e cea pe care o
va reproduce și bootstrap-ul din fl-service.
"""

import argparse
import sys

import numpy as np
import pandas as pd

TARGET = "Injury_Next_Season"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", required=True, help="CSV de intrare")
    ap.add_argument("--out", required=True, help="CSV de ieșire")
    ap.add_argument("--baseline", type=float, default=0.57,
                    help="cota clasei majoritare (fără accidentare) dorită")
    ap.add_argument("--noise", type=float, default=0.26,
                    help="fracția de etichete schimbate (swap, păstrează nr. pe clasă)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fl-path", default="services/fl-service",
                    help="cale către pachetul fl (pentru evaluare identică cu app)")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    df = pd.read_csv(a.inp)
    y = df[TARGET].astype(int).values
    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]
    n_neg = len(neg_idx)

    # 1) Dezechilibru: păstrăm toți negativii, subeșantionăm pozitivii
    target_pos = int(round(n_neg * (1 - a.baseline) / a.baseline))
    target_pos = min(target_pos, len(pos_idx))
    keep_pos = rng.choice(pos_idx, size=target_pos, replace=False)
    keep = np.sort(np.concatenate([neg_idx, keep_pos]))
    d = df.iloc[keep].reset_index(drop=True)

    # 2) Zgomot pe etichetă, păstrând numărul pe clasă (swap k pozitivi ↔ k negativi)
    yy = d[TARGET].astype(int).values.copy()
    n = len(yy)
    k = int(round(a.noise * n / 2))
    p_ix = np.where(yy == 1)[0]
    n_ix = np.where(yy == 0)[0]
    k = min(k, len(p_ix), len(n_ix))
    flip_p = rng.choice(p_ix, size=k, replace=False)
    flip_n = rng.choice(n_ix, size=k, replace=False)
    yy[flip_p] = 0
    yy[flip_n] = 1
    d[TARGET] = yy

    # amestecă rândurile
    d = d.sample(frac=1.0, random_state=a.seed).reset_index(drop=True)
    d.to_csv(a.out, index=False)

    base = np.bincount(yy).max() / len(yy)
    print(f"[date] rânduri={n}  rata_baza={base:.3f}  "
          f"rata_pozitivi={(yy == 1).mean():.3f}  etichete_schimbate={2 * k} ({2 * k / n:.1%})")

    # Evaluare identică cu aplicația
    try:
        sys.path.insert(0, a.fl_path)
        from fl.model import FEATURES, preprocess, build_model
        from sklearn.model_selection import cross_val_score
        dd = preprocess(d.copy())
        X = dd[FEATURES].values
        Y = dd[TARGET].astype(int).values
        acc = cross_val_score(build_model(), X, Y, cv=5, scoring="accuracy")
        rec = cross_val_score(build_model(), X, Y, cv=5, scoring="recall")
        print(f"[eval] 5-fold CV  acuratețe={acc.mean():.3f}±{acc.std():.3f}  "
              f"recall={rec.mean():.3f}  (baseline={base:.3f}, "
              f"+{(acc.mean() - base) * 100:.1f} pp)")
        # exact ce va afișa UI-ul: bootstrap = un singur split 15% (seed 42)
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, recall_score
        Xtr, Xte, ytr, yte = train_test_split(X, Y, test_size=0.15,
                                              random_state=42, stratify=Y)
        bm = build_model(); bm.fit(Xtr, ytr)
        pred = bm.predict(Xte)
        print(f"[eval] bootstrap (split 15%%, seed 42 — exact UI)  "
              f"acuratețe={accuracy_score(yte, pred):.3f}  recall={recall_score(yte, pred):.3f}")
    except Exception as exc:
        print("[eval] omis:", exc)


if __name__ == "__main__":
    main()
