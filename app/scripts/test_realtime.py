#!/usr/bin/env python3
"""
Test Real-Time Sliding Window Detection
Generates events in quick succession to trigger alerts

Multipliers:
- Alice (stable): ×2
- Bob (unstable): ×3

Historical max values from database (2017 data, excluding 2026 tests)
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import write_log
import time

# Historical maximums - CORRECT VALUES from database
HISTORICAL_MAX = {
    'file_written': {'alice': 3, 'bob': 16},
    'file_deleted': {'alice': 1, 'bob': 85},
    'file_created': {'alice': 3, 'bob': 18},
    'login_sequence': {'alice': 44, 'bob': 327}
}

# Multipliers
MULTIPLIER = {'alice': 2, 'bob': 3}

def calculate_threshold(user, event_type):
    """Calculate threshold for a user and event type"""
    hist_max = HISTORICAL_MAX.get(event_type, {}).get(user, 1)
    mult = MULTIPLIER.get(user, 3)
    return hist_max * mult

def get_events_needed(user, event_type):
    """Calculate how many events needed to trigger an alert"""
    threshold = calculate_threshold(user, event_type)
    return threshold + 1

def test_ransomware(uid, user_type):
    """Test Ransomware detection: rapid file_written events"""
    print("\n" + "="*60)
    print(f"TEST 1: RANSOMWARE - Rapid file_written events for {uid}")
    print("="*60)
    
    threshold = calculate_threshold(user_type, 'file_written')
    events_needed = get_events_needed(user_type, 'file_written')
    
    print(f"  Historical max: {HISTORICAL_MAX['file_written'][user_type]}")
    print(f"  Multiplier: ×{MULTIPLIER[user_type]}")
    print(f"  Threshold: {threshold} events in 1 minute")
    print(f"  Generating: {events_needed} events (need >{threshold})")
    
    for i in range(events_needed):
        write_log(
            event_type="file_written",
            uid=uid,
            uid_type="name",
            params={"path": f"/documents/file_{i}.encrypted", "size": 1048576},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        time.sleep(0.2)
        if (i + 1) % 10 == 0:
            print(f"  Generated {i+1}/{events_needed} events")
    
    print(f"✅ Generated {events_needed} file_written events")

def test_mass_deletion(uid, user_type):
    """Test Mass Deletion detection: rapid file_deleted events"""
    print("\n" + "="*60)
    print(f"TEST 2: MASS DELETION - Rapid file_deleted events for {uid}")
    print("="*60)
    
    threshold = calculate_threshold(user_type, 'file_deleted')
    events_needed = get_events_needed(user_type, 'file_deleted')
    
    print(f"  Historical max: {HISTORICAL_MAX['file_deleted'][user_type]}")
    print(f"  Multiplier: ×{MULTIPLIER[user_type]}")
    print(f"  Threshold: {threshold} events in 5 minutes")
    print(f"  Generating: {events_needed} events (need >{threshold})")
    
    for i in range(events_needed):
        write_log(
            event_type="file_deleted",
            uid=uid,
            uid_type="name",
            params={"path": f"/documents/file_{i}.txt"},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        time.sleep(0.1)
        if (i + 1) % 20 == 0:
            print(f"  Generated {i+1}/{events_needed} events")
    
    print(f"✅ Generated {events_needed} file_deleted events")

def test_malicious_upload(uid, user_type):
    """Test Malicious Upload detection: rapid file_created events"""
    print("\n" + "="*60)
    print(f"TEST 3: MALICIOUS UPLOAD - Rapid file_created events for {uid}")
    print("="*60)
    
    threshold = calculate_threshold(user_type, 'file_created')
    events_needed = get_events_needed(user_type, 'file_created')
    
    print(f"  Historical max: {HISTORICAL_MAX['file_created'][user_type]}")
    print(f"  Multiplier: ×{MULTIPLIER[user_type]}")
    print(f"  Threshold: {threshold} events in 5 minutes")
    print(f"  Generating: {events_needed} events (need >{threshold})")
    
    for i in range(events_needed):
        write_log(
            event_type="file_created",
            uid=uid,
            uid_type="name",
            params={"path": f"/uploads/file_{i}.exe", "size": 2048576},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        time.sleep(0.1)
        if (i + 1) % 10 == 0:
            print(f"  Generated {i+1}/{events_needed} events")
    
    print(f"✅ Generated {events_needed} file_created events")

def test_account_takeover(uid, user_type):
    """Test Account Takeover detection: login + rapid file_accessed"""
    print("\n" + "="*60)
    print(f"TEST 4: ACCOUNT TAKEOVER - Login + rapid file access for {uid}")
    print("="*60)
    
    hist_max = HISTORICAL_MAX['login_sequence'][user_type]
    multiplier = MULTIPLIER[user_type]
    threshold = hist_max * multiplier
    events_needed = threshold + 1
    
    print(f"  Historical max: {hist_max}")
    print(f"  Multiplier: ×{multiplier}")
    print(f"  Threshold: {threshold} accesses in 60 seconds after login")
    print(f"  Generating: {events_needed} accesses (need >{threshold})")
    
    print("\n  Generating login_successful event...")
    write_log(
        event_type="login_successful",
        uid=uid,
        uid_type="name",
        params={"username": uid, "success": True},
        is_local_ip=False,
        role="user",
        location={"city": "unknown", "country": "External"}
    )
    
    time.sleep(0.5)
    
    print(f"  Generating {events_needed} file_accessed events...")
    for i in range(events_needed):
        write_log(
            event_type="file_accessed",
            uid=uid,
            uid_type="name",
            params={"path": f"/confidential/data_{i}.pdf", "action": "download"},
            is_local_ip=False,
            role="user",
            location={"city": "unknown", "country": "External"}
        )
        time.sleep(0.05)
        if (i + 1) % 50 == 0:
            print(f"    Generated {i+1}/{events_needed} accesses")
    
    print(f"✅ Generated login + {events_needed} file accesses")

def test_all(uid, user_type):
    """Run all real-time tests"""
    print("\n" + "="*60)
    print(f"RUNNING ALL REAL-TIME TESTS for {uid} ({user_type})")
    print("="*60)
    
    print("\n[1/4] RANSOMWARE")
    test_ransomware(uid, user_type)
    print("\n" + "-"*40)
    time.sleep(2)
    
    print("\n[2/4] MASS DELETION")
    test_mass_deletion(uid, user_type)
    print("\n" + "-"*40)
    time.sleep(2)
    
    print("\n[3/4] MALICIOUS UPLOAD")
    test_malicious_upload(uid, user_type)
    print("\n" + "-"*40)
    time.sleep(2)
    
    print("\n[4/4] ACCOUNT TAKEOVER")
    test_account_takeover(uid, user_type)

def show_thresholds(user_type):
    """Display thresholds for the selected user"""
    print("\n" + "="*60)
    print(f"THRESHOLDS FOR {user_type.upper()} (Multiplier: ×{MULTIPLIER[user_type]})")
    print("="*60)
    
    for event_type in ['file_written', 'file_deleted', 'file_created', 'login_sequence']:
        hist_max = HISTORICAL_MAX.get(event_type, {}).get(user_type, 1)
        threshold = hist_max * MULTIPLIER[user_type]
        events_needed = threshold + 1
        if event_type == 'file_written':
            window = "1 minute"
        elif event_type == 'login_sequence':
            window = "60 seconds after login"
        else:
            window = "5 minutes"
        print(f"  {event_type}: max={hist_max} ×{MULTIPLIER[user_type]} = threshold={threshold} → need {events_needed} events in {window}")

def clear_today_logs(uid):
    """Clear today's logs for clean test"""
    from models.database import get_db
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM logs WHERE time::date = CURRENT_DATE AND uid = %s", (uid,))
    deleted_logs = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Cleared {deleted_logs} existing logs for {uid}")
    
    conn2 = get_db()
    cur2 = conn2.cursor()
    cur2.execute("DELETE FROM rare_events_alerts WHERE user_id = %s", (uid,))
    deleted_alerts = cur2.rowcount
    conn2.commit()
    cur2.close()
    conn2.close()
    print(f"Cleared {deleted_alerts} existing alerts for {uid}")

def main():
    print("\n" + "="*60)
    print("REAL-TIME DETECTION TEST SUITE")
    print("="*60)
    
    print("\nSelect target user:")
    print("1. Alice (stable, ×2 multiplier)")
    print("2. Bob (unstable, ×3 multiplier)")
    user_choice = input("\nEnter choice (1-2): ")
    
    if user_choice == '1':
        TARGET_USER = 'alice'
        USER_TYPE = 'alice'
    elif user_choice == '2':
        TARGET_USER = 'bob'
        USER_TYPE = 'bob'
    else:
        print("Invalid choice, defaulting to alice")
        TARGET_USER = 'alice'
        USER_TYPE = 'alice'
    
    show_thresholds(USER_TYPE)
    
    response = input(f"\nClear today's logs and alerts for {TARGET_USER}? (y/n): ")
    if response.lower() == 'y':
        clear_today_logs(TARGET_USER)
    
    print("\nSelect test to run:")
    print("1. Ransomware only")
    print("2. Mass Deletion only")
    print("3. Malicious Upload only")
    print("4. Account Takeover only")
    print("5. RUN ALL TESTS")
    
    choice = input("\nEnter choice (1-5): ")
    
    if choice == '1':
        test_ransomware(TARGET_USER, USER_TYPE)
    elif choice == '2':
        test_mass_deletion(TARGET_USER, USER_TYPE)
    elif choice == '3':
        test_malicious_upload(TARGET_USER, USER_TYPE)
    elif choice == '4':
        test_account_takeover(TARGET_USER, USER_TYPE)
    elif choice == '5':
        test_all(TARGET_USER, USER_TYPE)
    else:
        print("Invalid choice")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\nInstructions:")
    print("1. Go to Detection page: http://localhost:8000/admin/detection")
    print(f"2. Select {TARGET_USER}")
    print("3. Look at the Real-Time panel - alerts should appear within 30 seconds")

if __name__ == "__main__":
    main()