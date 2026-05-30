import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from models.database import get_db
from models.database import store_daily_anomaly, get_historical_anomalies, get_yesterdays_anomaly
import json

class DetectionService:
    
    FEATURES = [
        "events_total", "active_hours", "night_fraction", "unique_types",
        "file_accessed", "file_written", "login_attempt", "login_successful", "login_success_rate",
        "unique_paths", "path_depth_mean", "unique_dir1", "unique_dir2", "path_reuse_ratio"
    ]
    
    # Map all UID variations to canonical names
    UID_MAPPING = {
        'alice': 'alice',
        'alice-6384e2b2': 'alice',
        'bob': 'bob',
        'bob-9f9d51bc': 'bob',
        'yosr': 'yosr',
        'yosr-4da1a7f0': 'yosr',
        'admin': 'admin',
        'admin-21232f29': 'admin'
    }
    
    @staticmethod
    def get_canonical_uid(uid):
        return DetectionService.UID_MAPPING.get(uid, uid)
    
    @staticmethod
    def get_all_variants(canonical_uid):
        return [uid for uid, canon in DetectionService.UID_MAPPING.items() if canon == canonical_uid]
    
    @staticmethod
    def get_daily_features_for_date_range(uid, start_date, end_date):
        canonical_uid = DetectionService.get_canonical_uid(uid)
        variants = DetectionService.get_all_variants(canonical_uid)
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT time, type, params 
            FROM logs 
            WHERE uid = ANY(%s) AND time >= %s AND time < %s
            ORDER BY time
        """, (variants, start_date, end_date))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        if not rows:
            return pd.DataFrame()
        
        data = []
        for row in rows:
            time = row['time']
            event_type = row['type']
            params = row['params'] if row['params'] else {}
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    params = {}
            path = params.get("path", "") if isinstance(params, dict) else ""
            data.append({
                "time": time,
                "type": event_type,
                "params_path": path,
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
        df["is_file_written"] = (df["type"] == "file_written").astype(int)
        df["is_login_attempt"] = (df["type"] == "login_attempt").astype(int)
        df["is_login_successful"] = (df["type"] == "login_successful").astype(int)
        
        g = df.groupby("date")
        eps = 1e-9
        
        daily_df = pd.DataFrame({
            "events_total": g.size(),
            "active_hours": g["hour"].nunique(),
            "night_events": g["hour"].apply(lambda s: ((s >= 0) & (s <= 5)).sum()),
            "unique_types": g["type"].nunique(),
            "file_accessed": g["is_file_accessed"].sum(),
            "file_written": g["is_file_written"].sum(),
            "login_attempt": g["is_login_attempt"].sum(),
            "login_successful": g["is_login_successful"].sum(),
            "unique_paths": g["params_path"].nunique(dropna=True),
            "path_depth_mean": g["path_depth"].mean(),
            "unique_dir1": g["dir1"].nunique(dropna=True),
            "unique_dir2": g["dir2"].nunique(dropna=True),
        }).reset_index()
        
        daily_df["night_fraction"] = daily_df["night_events"] / (daily_df["events_total"] + eps)
        daily_df["login_success_rate"] = daily_df["login_successful"] / (daily_df["login_attempt"] + eps)
        daily_df["path_reuse_ratio"] = daily_df["file_accessed"] / (daily_df["unique_paths"] + eps)
        daily_df["date"] = daily_df["date"].astype(str)
        
        return daily_df
    
    @staticmethod
    def run_isolation_forest(daily_df, contamination=0.05):
        if daily_df.empty or len(daily_df) < 3:
            return None, None
        
        features_present = [f for f in DetectionService.FEATURES if f in daily_df.columns]
        X = daily_df[features_present].replace([np.inf, -np.inf], np.nan)
        for col in X.columns:
            X[col] = X[col].fillna(X[col].median())
        
        X_scaled = StandardScaler().fit_transform(X)
        iso_model = IsolationForest(n_estimators=100, contamination=contamination, random_state=42).fit(X_scaled)
        
        anomaly_scores = -iso_model.decision_function(X_scaled)
        predictions = iso_model.predict(X_scaled)
        
        return anomaly_scores, predictions
    
    @staticmethod
    def run_baseline(daily_df, percentile=95):
        if daily_df.empty or len(daily_df) < 3:
            return None, None, None
        
        eps = 1e-9
        baseline = {}
        for f in DetectionService.FEATURES:
            if f not in daily_df.columns:
                continue
            s = daily_df[f].replace([np.inf, -np.inf], np.nan).dropna()
            baseline[f] = float(np.nanpercentile(s, percentile)) if not s.empty else np.nan
        
        scores, explanations, flags = [], [], []
        
        for _, row in daily_df.iterrows():
            score, flag_count, contribs = 0.0, 0, []
            for f in DetectionService.FEATURES:
                if f not in row or f not in baseline:
                    continue
                x, t = float(row[f]), baseline[f]
                if np.isnan(t) or t == 0:
                    continue
                if x > t:
                    r = x / (t + eps)
                    score += r - 1.0
                    flag_count += 1
                    contribs.append((f, x, t, r))
            contribs.sort(key=lambda z: z[3], reverse=True)
            expl = "; ".join([f"{f}={x:.3g} vs p{percentile}={t:.3g} ({r:.2f}x)" for (f, x, t, r) in contribs[:5]]) if contribs else "No features exceeded threshold"
            scores.append(score)
            explanations.append(expl)
            flags.append(flag_count)
        
        return scores, flags, explanations
    
    @staticmethod
    def classify_attack(contributors, login_success_rate=None):
        """
        THE RULES - in order of specific to general
        Each attack has a unique fingerprint
        """
        if pd.isna(contributors) or contributors == "No features exceeded threshold":
            return "NONE", [], "No anomalies detected"
        
        spikes = [s.split('=')[0] for s in contributors.split('; ') if '=' in s]
        
        attack_types = []
        descriptions = []
        
        # RULE 1: RANSOMWARE - WRITES files (encryption)
        if 'file_written' in spikes and 'unique_paths' in spikes:
            attack_types.append("RANSOMWARE")
            descriptions.append("Many file write operations on different paths - pattern matches ransomware encryption")
        
        # RULE 2: DATA THEFT - READS files (exfiltration)
        elif 'file_accessed' in spikes and 'unique_paths' in spikes:
            attack_types.append("DATA_THEFT")
            descriptions.append("Many file read operations on different paths - pattern matches data exfiltration")
        
        # RULE 3: ACCOUNT TAKEOVER - Failed logins then success
        elif 'login_attempt' in spikes and 'login_successful' in spikes and login_success_rate is not None and login_success_rate < 0.5:
            attack_types.append("ACCOUNT_TAKEOVER")
            descriptions.append(f"Login attempts with {login_success_rate:.0%} success rate - pattern matches credential stuffing")
        
        # RULE 4: BRUTE FORCE - Many failed logins, no successes
        elif 'login_attempt' in spikes and 'login_successful' not in spikes:
            attack_types.append("BRUTE_FORCE")
            descriptions.append("Many login attempts with no successful logins - pattern matches password brute force")
        
        # RULE 5: DIRECTORY TRAVERSAL - Exploring directories
        elif 'unique_dir1' in spikes or 'unique_dir2' in spikes:
            attack_types.append("DIRECTORY_TRAVERSAL")
            descriptions.append("Accessing many different directories - pattern matches directory enumeration")
        
        # RULE 6: OFF HOURS - Night work
        elif 'night_fraction' in spikes:
            attack_types.append("OFF_HOURS")
            descriptions.append("Activity during night hours (0-5 AM) - unusual timing")
        
        # RULE 7: MASS ACTIVITY - High volume, normal patterns
        elif 'events_total' in spikes and len(spikes) <= 2:
            attack_types.append("MASS_ACTIVITY")
            descriptions.append("Unusually high volume of events")
        
        # RULE 8: UNKNOWN
        else:
            attack_types.append("UNKNOWN")
            descriptions.append(f"Unusual pattern: {', '.join(spikes[:3])}")
        
        # Severity order for primary attack type
        severity_order = ["RANSOMWARE", "DATA_THEFT", "ACCOUNT_TAKEOVER", "BRUTE_FORCE", "DIRECTORY_TRAVERSAL", "OFF_HOURS", "MASS_ACTIVITY", "UNKNOWN"]
        
        primary = "UNKNOWN"
        for sev in severity_order:
            if sev in attack_types:
                primary = sev
                break
        
        combined_desc = " | ".join(descriptions)
        
        return primary, attack_types, combined_desc
    
    @staticmethod
    def verify_data_theft(date_str, daily_df):
        daily_df['date_parsed'] = pd.to_datetime(daily_df['date'])
        row = daily_df[daily_df['date_parsed'] == pd.to_datetime(date_str)]
        if row.empty:
            return "NO_DATA"
        current = float(row['path_reuse_ratio'].iloc[0])
        historical = daily_df[daily_df['date_parsed'] < pd.to_datetime(date_str)]
        if len(historical) == 0:
            return "INSUFFICIENT_HISTORY"
        median = float(historical['path_reuse_ratio'].median())
        if current < median:
            return "CONFIRMED - unusual path reuse pattern"
        return "SUSPICIOUS - elevated but within normal variation"
    
    @staticmethod
    def verify_login(date_str, daily_df):
        daily_df['date_parsed'] = pd.to_datetime(daily_df['date'])
        row = daily_df[daily_df['date_parsed'] == pd.to_datetime(date_str)]
        if row.empty:
            return "NO_DATA"
        rate = float(row['login_success_rate'].iloc[0])
        attempts = int(row['login_attempt'].iloc[0])
        if rate < 0.3:
            return f"ACCOUNT_TAKEOVER_RISK - {attempts} attempts with {rate:.0%} success rate"
        elif rate < 0.7:
            return f"BRUTE_FORCE - {attempts} attempts with {rate:.0%} success rate"
        elif rate > 0.8:
            return f"LEGITIMATE_BUSY_DAY - {attempts} attempts with {rate:.0%} success rate"
        return f"SUSPICIOUS - {attempts} attempts with {rate:.0%} success rate"
    
    @staticmethod
    def analyze_day(uid, target_date):
        start_date = datetime.combine(target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        canonical_uid = DetectionService.get_canonical_uid(uid)
        daily_df = DetectionService.get_daily_features_for_date_range(canonical_uid, start_date, end_date)
        
        if daily_df.empty:
            return {"error": f"No data for {canonical_uid} on {target_date}"}
        
        iso_scores, iso_preds = DetectionService.run_isolation_forest(daily_df)
        baseline_scores, baseline_flags, baseline_contributors = DetectionService.run_baseline(daily_df)
        
        flagged_by_iso = iso_preds is not None and -1 in iso_preds
        flagged_by_baseline = baseline_scores is not None and any(s > 0 for s in baseline_scores)
        
        should_store = flagged_by_iso or flagged_by_baseline
        
        if not should_store:
            return {
                "date": target_date.isoformat(),
                "user_id": canonical_uid,
                "flagged": False,
                "message": "No anomalies detected - not stored"
            }
        
        flagged_idx = None
        if flagged_by_baseline and baseline_scores:
            for i, score in enumerate(baseline_scores):
                if score > 0:
                    flagged_idx = i
                    break
        elif flagged_by_iso and iso_scores is not None:
            for i, pred in enumerate(iso_preds):
                if pred == -1:
                    flagged_idx = i
                    break
        
        attack_type = "UNKNOWN"
        analyst_notes = ""
        confidence = "LOW"
        top_contributors = ""
        num_flagged = 0
        baseline_score_val = 0.0
        iso_score_val = 0.0
        
        if flagged_idx is not None:
            baseline_score_val = float(baseline_scores[flagged_idx]) if baseline_scores else 0.0
            iso_score_val = float(iso_scores[flagged_idx]) if iso_scores is not None else 0.0
            top_contributors = baseline_contributors[flagged_idx] if baseline_contributors else ""
            num_flagged = int(baseline_flags[flagged_idx]) if baseline_flags else 0
            
            if flagged_by_baseline:
                login_rate = float(daily_df.iloc[flagged_idx]['login_success_rate']) if 'login_success_rate' in daily_df.columns else None
                primary_type, all_types, description = DetectionService.classify_attack(top_contributors, login_rate)
                attack_type = primary_type
                
                all_types_str = " + ".join(all_types)
                analyst_notes = f"[{all_types_str}] {description}"
                
                if "DATA_THEFT" in all_types or "RANSOMWARE" in all_types:
                    verification = DetectionService.verify_data_theft(daily_df.iloc[flagged_idx]['date'], daily_df)
                    analyst_notes += f"\nVerification: {verification}"
                elif "ACCOUNT_TAKEOVER" in all_types or "BRUTE_FORCE" in all_types:
                    verification = DetectionService.verify_login(daily_df.iloc[flagged_idx]['date'], daily_df)
                    analyst_notes += f"\nVerification: {verification}"
                
                confidence = "HIGH" if flagged_by_iso else "MEDIUM"
            else:
                analyst_notes = "Recommend further manual raw log investigation - Isolation Forest flagged but baseline did not confirm"
                confidence = "LOW"
                attack_type = "ISOLATION_ONLY"
        
        store_daily_anomaly(
            target_date, canonical_uid, iso_score_val, baseline_score_val,
            flagged_by_iso, flagged_by_baseline, attack_type,
            top_contributors, num_flagged, confidence, analyst_notes
        )
        
        return {
            "date": target_date.isoformat(),
            "user_id": canonical_uid,
            "flagged": True,
            "flagged_by_isolation": flagged_by_iso,
            "flagged_by_baseline": flagged_by_baseline,
            "attack_type": attack_type,
            "confidence": confidence,
            "analyst_notes": analyst_notes,
            "baseline_score": baseline_score_val,
            "iso_score": iso_score_val
        }
    
    @staticmethod
    def analyze_today_cumulative(uid):
        today = datetime.now(timezone.utc).date()
        start_date = datetime.combine(today, datetime.min.time())
        current_time = datetime.now(timezone.utc)
        
        canonical_uid = DetectionService.get_canonical_uid(uid)
        
        today_df = DetectionService.get_daily_features_for_date_range(canonical_uid, start_date, current_time)
        
        if today_df.empty:
            return {
                "date": today.isoformat(),
                "user_id": canonical_uid,
                "cumulative_until": current_time.isoformat(),
                "has_data": False,
                "total_events": 0,
                "message": "No data for today yet"
            }
        
        total_events = int(today_df.iloc[0]['events_total']) if not today_df.empty else 0
        
        hist_start = datetime(2017, 7, 7)
        hist_end = datetime(2017, 10, 4)
        historical_df = DetectionService.get_daily_features_for_date_range(canonical_uid, hist_start, hist_end)
        
        if historical_df.empty:
            return {
                "date": today.isoformat(),
                "user_id": canonical_uid,
                "cumulative_until": current_time.isoformat(),
                "has_data": True,
                "total_events": total_events,
                "flagged": False,
                "message": "No historical data for baseline"
            }
        
        combined_df = pd.concat([historical_df, today_df], ignore_index=True)
        
        iso_scores, iso_preds = DetectionService.run_isolation_forest(combined_df)
        baseline_scores, baseline_flags, baseline_contributors = DetectionService.run_baseline(combined_df)
        
        if baseline_scores is None:
            return {
                "date": today.isoformat(),
                "user_id": canonical_uid,
                "cumulative_until": current_time.isoformat(),
                "has_data": True,
                "total_events": total_events,
                "flagged": False,
                "message": "Baseline calculation failed"
            }
        
        today_score = float(baseline_scores[-1]) if baseline_scores else 0.0
        today_flags = int(baseline_flags[-1]) if baseline_flags else 0
        today_contributors = baseline_contributors[-1] if baseline_contributors else ""
        
        today_iso_flagged = False
        today_iso_score = 0.0
        if iso_preds is not None:
            today_iso_flagged = bool(iso_preds[-1] == -1)
            today_iso_score = float(iso_scores[-1]) if iso_scores is not None else 0.0
        
        flagged_by_baseline = today_score > 0
        flagged_by_iso = today_iso_flagged
        flagged = flagged_by_baseline or flagged_by_iso
        
        result = {
            "date": today.isoformat(),
            "user_id": canonical_uid,
            "cumulative_until": current_time.isoformat(),
            "has_data": True,
            "total_events": total_events,
            "flagged": flagged,
            "flagged_by_baseline": flagged_by_baseline,
            "flagged_by_isolation": flagged_by_iso,
            "baseline_score": today_score if flagged_by_baseline else 0.0,
            "iso_score": today_iso_score
        }
        
        if flagged_by_baseline:
            login_rate = float(today_df.iloc[0]['login_success_rate']) if 'login_success_rate' in today_df.columns else None
            primary_type, all_types, desc = DetectionService.classify_attack(today_contributors, login_rate)
            result["attack_type"] = primary_type
            result["all_attack_types"] = all_types
            result["attack_description"] = desc
            result["top_contributors"] = today_contributors
            result["num_flagged_features"] = today_flags
            
            if "DATA_THEFT" in all_types or "RANSOMWARE" in all_types:
                result["verification"] = DetectionService.verify_data_theft(today_df.iloc[0]['date'], combined_df)
            elif "ACCOUNT_TAKEOVER" in all_types or "BRUTE_FORCE" in all_types:
                result["verification"] = DetectionService.verify_login(today_df.iloc[0]['date'], combined_df)
        elif flagged_by_iso:
            result["attack_type"] = "ISOLATION_ONLY"
            result["all_attack_types"] = ["ISOLATION_ONLY"]
            result["attack_description"] = "Isolation Forest detected anomaly but baseline did not confirm"
            result["analyst_note"] = "Recommend further manual raw log investigation"
        
        return result
    
    @staticmethod
    def get_historical(uid, days_back=30):
        canonical_uid = DetectionService.get_canonical_uid(uid)
        return get_historical_anomalies(canonical_uid, days_back)
    
    @staticmethod
    def get_yesterday(uid):
        canonical_uid = DetectionService.get_canonical_uid(uid)
        return get_yesterdays_anomaly(canonical_uid)
    
    @staticmethod
    def run_midnight_job():
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        results = {}
        for user in ['alice', 'bob']:
            results[user] = DetectionService.analyze_day(user, yesterday)
        return results