import pandas as pd
import numpy as np
from models.database import get_db
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class DetectionService:
    
    FEATURES = [
        "events_total", "active_hours", "night_fraction", "unique_types",
        "file_events", "login_attempt", "login_successful", "login_success_rate",
        "unique_paths", "path_depth_mean", "unique_dir1", "unique_dir2", "path_reuse_ratio"
    ]
    
    @staticmethod
    def get_daily_features(uid):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT time, type, params FROM logs WHERE uid = %s ORDER BY time", (uid,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        if not rows:
            return pd.DataFrame()
        
        data = []
        for row in rows:
            time = row[0]
            event_type = row[1]
            params = row[2] if row[2] else {}
            if isinstance(params, str):
                import json
                try:
                    params = json.loads(params)
                except:
                    params = {}
            
            path = params.get("path", "") if isinstance(params, dict) else ""
            
            data.append({
                "time": time,
                "type": event_type,
                "params_path": path,
                "params_nkeys": len(params) if isinstance(params, dict) else 0,
                "hour": time.hour if time else 0,
                "date": time.date() if time else None
            })
        
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame()
        
        df = df.dropna(subset=["date"])
        
        def get_dir(path, idx):
            if not isinstance(path, str):
                return None
            parts = [p for p in path.split("/") if p]
            return parts[idx] if len(parts) > idx else None
        
        df["path_depth"] = df["params_path"].apply(lambda p: len([x for x in str(p).split("/") if x]) if isinstance(p, str) else 0)
        df["dir1"] = df["params_path"].apply(lambda p: get_dir(p, 0))
        df["dir2"] = df["params_path"].apply(lambda p: get_dir(p, 1))
        df["is_file_accessed"] = (df["type"] == "file_accessed").astype(int)
        df["is_login_attempt"] = (df["type"] == "login_attempt").astype(int)
        df["is_login_successful"] = (df["type"] == "login_successful").astype(int)
        
        g = df.groupby("date")
        eps = 1e-9
        
        daily_df = pd.DataFrame({
            "events_total": g.size(),
            "active_hours": g["hour"].nunique(),
            "night_events": g["hour"].apply(lambda s: ((s >= 0) & (s <= 5)).sum()),
            "unique_types": g["type"].nunique(),
            "file_events": g["is_file_accessed"].sum(),
            "login_attempt": g["is_login_attempt"].sum(),
            "login_successful": g["is_login_successful"].sum(),
            "unique_paths": g["params_path"].nunique(dropna=True),
            "path_depth_mean": g["path_depth"].mean(),
            "unique_dir1": g["dir1"].nunique(dropna=True),
            "unique_dir2": g["dir2"].nunique(dropna=True),
        }).reset_index()
        
        daily_df["night_fraction"] = daily_df["night_events"] / (daily_df["events_total"] + eps)
        daily_df["login_success_rate"] = daily_df["login_successful"] / (daily_df["login_attempt"] + eps)
        daily_df["path_reuse_ratio"] = daily_df["file_events"] / (daily_df["unique_paths"] + eps)
        daily_df["date"] = daily_df["date"].astype(str)
        
        return daily_df
    
    @staticmethod
    def compute_global_baseline(daily_df, percentile=95):
        if daily_df.empty or len(daily_df) < 7:
            return pd.DataFrame()
        
        eps = 1e-9
        baseline = {}
        for f in DetectionService.FEATURES:
            if f not in daily_df.columns:
                continue
            s = daily_df[f].replace([np.inf, -np.inf], np.nan).dropna()
            baseline[f] = {"p95": float(np.nanpercentile(s, percentile)) if not s.empty else np.nan}
        
        scores, explanations, flags = [], [], []
        
        for _, row in daily_df.iterrows():
            score, flag_count, contribs = 0.0, 0, []
            for f in DetectionService.FEATURES:
                if f not in row or f not in baseline:
                    continue
                x, t = float(row[f]), baseline[f]["p95"]
                if np.isnan(t) or t == 0:
                    continue
                if x > t:
                    r = x / (t + eps)
                    score += r - 1.0
                    flag_count += 1
                    contribs.append((f, x, t, r))
            contribs.sort(key=lambda z: z[3], reverse=True)
            expl = "; ".join([f"{f}={x:.3g} vs p95={t:.3g} ({r:.2f}x)" for (f, x, t, r) in contribs[:5]]) if contribs else "No features exceeded p95"
            scores.append(score)
            explanations.append(expl)
            flags.append(flag_count)
        
        result = daily_df.copy()
        result["anomaly_score"] = scores
        result["num_flagged_features"] = flags
        result["top_contributors"] = explanations
        return result
    
    @staticmethod
    def compute_isolation_forest(daily_df, contamination=0.05):
        if daily_df.empty or len(daily_df) < 7:
            return pd.DataFrame()
        
        features_present = [f for f in DetectionService.FEATURES if f in daily_df.columns]
        X = daily_df[features_present].replace([np.inf, -np.inf], np.nan)
        for col in X.columns:
            X[col] = X[col].fillna(X[col].median())
        
        X_scaled = StandardScaler().fit_transform(X)
        iso_model = IsolationForest(n_estimators=500, contamination=contamination, random_state=42).fit(X_scaled)
        
        result = daily_df[["date"]].copy()
        result["iso_pred"] = iso_model.predict(X_scaled)
        result["iso_anomaly_score"] = -iso_model.decision_function(X_scaled)
        return result
    
    @staticmethod
    def classify_attack(contributors):
        if pd.isna(contributors) or contributors == "No features exceeded p95":
            return "NONE"
        spikes = [s.split('=')[0] for s in contributors.split('; ') if '=' in s]
        if 'file_events' in spikes and 'unique_paths' in spikes:
            return "DATA_THEFT"
        if 'events_total' in spikes and 'active_hours' in spikes:
            return "BOT_OR_MASS_ACTIVITY"
        if 'unique_dir1' in spikes or 'unique_dir2' in spikes:
            return "DIRECTORY_TRAVERSAL"
        if 'login_attempt' in spikes:
            return "LOGIN_ACTIVITY"
        if 'night_fraction' in spikes:
            return "OFF_HOURS"
        if 'unique_types' in spikes:
            return "DIVERSE_ACTIVITY"
        if 'events_total' in spikes and len(spikes) == 1:
            return "MASS_ACTIVITY"
        if 'path_reuse_ratio' in spikes and len(spikes) == 1:
            return "PATH_REUSE_ANOMALY"
        return "UNKNOWN"
    
    @staticmethod
    def verify_data_theft(date_str, attack_type, daily_df):
        if attack_type != "DATA_THEFT":
            return None
        daily_df['date_parsed'] = pd.to_datetime(daily_df['date'])
        row = daily_df[daily_df['date_parsed'] == pd.to_datetime(date_str)]
        if row.empty:
            return "NO_DATA"
        current = row['path_reuse_ratio'].iloc[0]
        historical = daily_df[daily_df['date_parsed'] < pd.to_datetime(date_str)]
        if len(historical) == 0:
            return "INSUFFICIENT_HISTORY"
        return "CONFIRMED" if current < historical['path_reuse_ratio'].median() else "SUSPICIOUS"
    
    @staticmethod
    def verify_login(date_str, attack_type, daily_df):
        if attack_type != "LOGIN_ACTIVITY":
            return None
        daily_df['date_parsed'] = pd.to_datetime(daily_df['date'])
        row = daily_df[daily_df['date_parsed'] == pd.to_datetime(date_str)]
        if row.empty:
            return "NO_DATA"
        rate = row['login_success_rate'].iloc[0]
        if rate < 0.5:
            return "BRUTE_FORCE"
        if rate > 0.8:
            return "FALSE_POSITIVE_BUSY_DAY"
        return "SUSPICIOUS"
    
    @staticmethod
    def get_full_analysis(uid):
        daily_df = DetectionService.get_daily_features(uid)
        if daily_df.empty:
            return {"error": f"No data for user {uid}"}
        
        baseline_df = DetectionService.compute_global_baseline(daily_df)
        iforest_df = DetectionService.compute_isolation_forest(daily_df)
        
        if baseline_df.empty:
            return {"error": f"Baseline failed for {uid}"}
        
        baseline_df = baseline_df.merge(iforest_df, on="date", how="left")
        baseline_df['if_flagged'] = baseline_df['iso_pred'] == -1
        baseline_df['confidence'] = baseline_df['if_flagged'].apply(lambda x: "HIGH" if x else "MEDIUM")
        baseline_df['attack_type'] = baseline_df['top_contributors'].apply(DetectionService.classify_attack)
        baseline_df['data_theft_verification'] = baseline_df.apply(lambda r: DetectionService.verify_data_theft(r['date'], r['attack_type'], daily_df), axis=1)
        baseline_df['login_verification'] = baseline_df.apply(lambda r: DetectionService.verify_login(r['date'], r['attack_type'], daily_df), axis=1)
        
        return {
            "user_id": uid,
            "total_days": len(daily_df),
            "flagged_days": len(baseline_df[baseline_df['anomaly_score'] > 0]),
            "results": baseline_df.to_dict(orient="records")
        }