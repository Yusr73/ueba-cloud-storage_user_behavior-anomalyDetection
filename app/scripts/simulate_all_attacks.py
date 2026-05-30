#!/usr/bin/env python3
"""
Attack Simulation Script - Matches Detection Rules Exactly

Each simulation is designed to trigger a SPECIFIC attack type
Run this to test detection capabilities
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import get_db
from utils.logger import write_log
from datetime import datetime, timezone, timedelta
import random
import time

TARGET_USER = None

def clear_today_logs(uid):
    """Clear today's logs before simulating new attack"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM logs WHERE time::date = CURRENT_DATE AND uid = %s", (uid,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Cleared {deleted} existing logs for {uid}")
    return deleted

def simulate_ransomware(uid):
    """
    RANSOMWARE - Triggers: file_written + unique_paths
    Writes many files to different paths (encryption pattern)
    """
    print("\n" + "="*60)
    print(f"SIMULATING: RANSOMWARE for {uid}")
    print("="*60)
    
    NUM_WRITES = 300
    UNIQUE_PATHS = 200
    
    dirs = ['documents', 'finance', 'hr', 'projects', 'clients', 'backup']
    subdirs = ['2024', '2025', 'data', 'reports', 'confidential']
    extensions = ['.encrypted', '.locked', '.ransom', '.crypt']
    
    paths = []
    for i in range(UNIQUE_PATHS):
        dir1 = random.choice(dirs)
        dir2 = random.choice(subdirs)
        ext = random.choice(extensions)
        filename = f"file_{random.randint(1000, 9999)}{ext}"
        path = f"/{dir1}/{dir2}/{filename}"
        paths.append(path)
    
    print(f"Generating {NUM_WRITES} file writes on {UNIQUE_PATHS} unique paths...")
    for i in range(NUM_WRITES):
        path = random.choice(paths)
        write_log(
            event_type="file_written",
            uid=uid,
            uid_type="name",
            params={"path": path, "size": random.randint(1024, 1048576)},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        if (i + 1) % 50 == 0:
            print(f"  Generated {i+1}/{NUM_WRITES} file_written events")
    
    print(f"✅ RANSOMWARE: {NUM_WRITES} file writes on {UNIQUE_PATHS} unique paths")

def simulate_data_theft(uid):
    """
    DATA_THEFT - Triggers: file_accessed + unique_paths
    Reads many different files (exfiltration pattern)
    """
    print("\n" + "="*60)
    print(f"SIMULATING: DATA_THEFT for {uid}")
    print("="*60)
    
    NUM_READS = 400
    UNIQUE_PATHS = 250
    
    dirs = ['documents', 'finance', 'hr', 'clients', 'internal', 'confidential', 'secrets']
    subdirs = ['2024', '2025', 'customers', 'employees', 'contracts', 'financials']
    extensions = ['.pdf', '.docx', '.xlsx', '.txt', '.csv', '.db']
    
    paths = []
    for i in range(UNIQUE_PATHS):
        dir1 = random.choice(dirs)
        dir2 = random.choice(subdirs)
        ext = random.choice(extensions)
        filename = f"file_{random.randint(1000, 9999)}{ext}"
        path = f"/{dir1}/{dir2}/{filename}"
        paths.append(path)
    
    print(f"Generating {NUM_READS} file reads on {UNIQUE_PATHS} unique paths...")
    for i in range(NUM_READS):
        path = random.choice(paths)
        write_log(
            event_type="file_accessed",
            uid=uid,
            uid_type="name",
            params={"path": path, "action": "read"},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        if (i + 1) % 50 == 0:
            print(f"  Generated {i+1}/{NUM_READS} file_accessed events")
    
    print(f"✅ DATA_THEFT: {NUM_READS} file reads on {UNIQUE_PATHS} unique paths")

def simulate_account_takeover(uid):
    """
    ACCOUNT_TAKEOVER - Triggers: login_attempt + login_successful + low success rate (<50%)
    Credential stuffing pattern: many attempts, some succeed
    """
    print("\n" + "="*60)
    print(f"SIMULATING: ACCOUNT_TAKEOVER for {uid}")
    print("="*60)
    
    TOTAL_ATTEMPTS = 60
    SUCCESSFUL = 15  # 25% success rate
    
    print(f"Generating {TOTAL_ATTEMPTS} login attempts, {SUCCESSFUL} successful (25% success rate)...")
    
    for i in range(TOTAL_ATTEMPTS):
        is_success = i < SUCCESSFUL
        write_log(
            event_type="login_attempt",
            uid=uid,
            uid_type="name",
            params={"username": uid, "password": f"attempt_{i}", "success": is_success},
            is_local_ip=False,
            role=None,
            location={"city": "unknown", "country": "External"}
        )
        
        if is_success:
            write_log(
                event_type="login_successful",
                uid=uid,
                uid_type="name",
                params={"username": uid, "success": True},
                is_local_ip=False,
                role="user",
                location={"city": "unknown", "country": "External"}
            )
        
        if (i + 1) % 20 == 0:
            print(f"  Generated {i+1}/{TOTAL_ATTEMPTS} login attempts")
    
    success_rate = (SUCCESSFUL / TOTAL_ATTEMPTS) * 100
    print(f"✅ ACCOUNT_TAKEOVER: {TOTAL_ATTEMPTS} attempts, {SUCCESSFUL} successes ({success_rate:.0f}% success rate)")

def simulate_brute_force(uid):
    """
    BRUTE_FORCE - Triggers: login_attempt spike, no login_successful spike
    Password spraying: many failed attempts, zero successes
    """
    print("\n" + "="*60)
    print(f"SIMULATING: BRUTE_FORCE for {uid}")
    print("="*60)
    
    FAILED_ATTEMPTS = 80
    
    print(f"Generating {FAILED_ATTEMPTS} failed login attempts (0% success rate)...")
    
    for i in range(FAILED_ATTEMPTS):
        write_log(
            event_type="login_attempt",
            uid=uid,
            uid_type="name",
            params={"username": uid, "password": f"wrong_{i}", "success": False},
            is_local_ip=False,
            role=None,
            location={"city": "unknown", "country": "External"}
        )
        if (i + 1) % 20 == 0:
            print(f"  Generated {i+1}/{FAILED_ATTEMPTS} failed attempts")
    
    print(f"✅ BRUTE_FORCE: {FAILED_ATTEMPTS} failed attempts, 0 successes")

def simulate_directory_traversal(uid):
    """
    DIRECTORY_TRAVERSAL - Triggers: unique_dir1 or unique_dir2
    Accesses many different directories
    """
    print("\n" + "="*60)
    print(f"SIMULATING: DIRECTORY_TRAVERSAL for {uid}")
    print("="*60)
    
    directories = [
        '/finance', '/hr', '/it', '/legal', '/marketing', '/sales', '/operations',
        '/research', '/development', '/testing', '/deployment', '/security',
        '/admin', '/backup', '/archive', '/temp', '/logs', '/config', '/scripts',
        '/users', '/groups', '/permissions', '/audit', '/compliance', '/risk',
        '/database', '/cache', '/uploads', '/downloads', '/temp', '/var', '/etc'
    ]
    
    print(f"Accessing {len(directories)} different directories...")
    
    for directory in directories:
        for j in range(3):
            write_log(
                event_type="file_accessed",
                uid=uid,
                uid_type="name",
                params={"path": f"{directory}/file_{j}.txt"},
                is_local_ip=True,
                role="user",
                location={"city": "unknown"}
            )
        print(f"  Accessed: {directory}")
    
    print(f"✅ DIRECTORY_TRAVERSAL: {len(directories)} unique directories accessed")

def simulate_off_hours(uid):
    """
    OFF_HOURS - Triggers: night_fraction
    Activity during night hours (0-5 AM)
    NOTE: Need to actually set timestamps to night hours
    """
    print("\n" + "="*60)
    print(f"SIMULATING: OFF_HOURS for {uid}")
    print("="*60)
    print("WARNING: This simulation creates events at current time.")
    print("To truly trigger OFF_HOURS, run this script between 0-5 AM local time,")
    print("or manually modify the timestamps in the database.")
    print("\nGenerating 100 file accesses (they will use current time)...")
    
    EVENTS = 100
    
    for i in range(EVENTS):
        write_log(
            event_type="file_accessed",
            uid=uid,
            uid_type="name",
            params={"path": f"/documents/night_file_{i}.txt"},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        if (i + 1) % 25 == 0:
            print(f"  Generated {i+1}/{EVENTS} events")
    
    print(f"✅ OFF_HOURS: {EVENTS} events (will trigger only if run between 0-5 AM)")

def simulate_mass_activity(uid):
    """
    MASS_ACTIVITY - Triggers: events_total spike (no other spikes)
    Very high volume of normal activity
    """
    print("\n" + "="*60)
    print(f"SIMULATING: MASS_ACTIVITY for {uid}")
    print("="*60)
    
    EVENTS = 1000
    
    print(f"Generating {EVENTS} normal file accesses (reusing same paths)...")
    
    # Use only a few paths so unique_paths doesn't spike
    paths = ['/documents/file1.txt', '/documents/file2.txt', '/documents/file3.txt']
    
    for i in range(EVENTS):
        path = random.choice(paths)
        write_log(
            event_type="file_accessed",
            uid=uid,
            uid_type="name",
            params={"path": path},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        if (i + 1) % 200 == 0:
            print(f"  Generated {i+1}/{EVENTS} events")
    
    print(f"✅ MASS_ACTIVITY: {EVENTS} events on only 3 unique paths")

def simulate_mixed_attack(uid):
    """Combination: DATA_THEFT + ACCOUNT_TAKEOVER"""
    print("\n" + "="*60)
    print(f"SIMULATING: MIXED ATTACK for {uid} (DATA_THEFT + ACCOUNT_TAKEOVER)")
    print("="*60)
    simulate_data_theft(uid)
    simulate_account_takeover(uid)

def run_all_attacks(uid):
    """Run all attack simulations sequentially"""
    print("\n" + "="*60)
    print(f"RUNNING ALL ATTACKS for {uid}")
    print("="*60)
    
    print("\n[1/8] RANSOMWARE")
    simulate_ransomware(uid)
    time.sleep(2)
    
    print("\n[2/8] DATA_THEFT")
    simulate_data_theft(uid)
    time.sleep(2)
    
    print("\n[3/8] ACCOUNT_TAKEOVER")
    simulate_account_takeover(uid)
    time.sleep(2)
    
    print("\n[4/8] BRUTE_FORCE")
    simulate_brute_force(uid)
    time.sleep(2)
    
    print("\n[5/8] DIRECTORY_TRAVERSAL")
    simulate_directory_traversal(uid)
    time.sleep(2)
    
    print("\n[6/8] OFF_HOURS")
    simulate_off_hours(uid)
    time.sleep(2)
    
    print("\n[7/8] MASS_ACTIVITY")
    simulate_mass_activity(uid)
    time.sleep(2)

def main():
    global TARGET_USER
    
    print("\n" + "="*60)
    print("UEBA ATTACK SIMULATION SUITE")
    print("="*60)
    
    print("\nSelect target user:")
    print("1. Alice")
    print("2. Bob")
    user_choice = input("\nEnter choice (1-2): ")
    
    if user_choice == '1':
        TARGET_USER = 'alice'
    elif user_choice == '2':
        TARGET_USER = 'bob'
    else:
        print("Invalid choice, defaulting to alice")
        TARGET_USER = 'alice'
    
    print(f"\nTarget user: {TARGET_USER}")
    
    # Clear today's logs
    response = input(f"\nClear today's logs for {TARGET_USER} before simulation? (y/n): ")
    if response.lower() == 'y':
        clear_today_logs(TARGET_USER)
    
    print("\n" + "="*60)
    print("ATTACK TYPES (matches detection rules):")
    print("="*60)
    print("1. RANSOMWARE        - file_written + unique_paths")
    print("2. DATA_THEFT        - file_accessed + unique_paths")
    print("3. ACCOUNT_TAKEOVER  - login_attempt + login_successful (<50% success)")
    print("4. BRUTE_FORCE       - login_attempt only (0% success)")
    print("5. DIRECTORY_TRAVERSAL - unique_dir1/dir2 spikes")
    print("6. OFF_HOURS         - night_fraction (run between 0-5 AM)")
    print("7. MASS_ACTIVITY     - events_total spike only")
    print("8. MIXED ATTACK      - DATA_THEFT + ACCOUNT_TAKEOVER")
    print("9. RUN ALL ATTACKS   - sequential")
    
    choice = input("\nEnter choice (1-9): ")
    
    if choice == '1':
        simulate_ransomware(TARGET_USER)
    elif choice == '2':
        simulate_data_theft(TARGET_USER)
    elif choice == '3':
        simulate_account_takeover(TARGET_USER)
    elif choice == '4':
        simulate_brute_force(TARGET_USER)
    elif choice == '5':
        simulate_directory_traversal(TARGET_USER)
    elif choice == '6':
        simulate_off_hours(TARGET_USER)
    elif choice == '7':
        simulate_mass_activity(TARGET_USER)
    elif choice == '8':
        simulate_mixed_attack(TARGET_USER)
    elif choice == '9':
        run_all_attacks(TARGET_USER)
    else:
        print("Invalid choice")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("SIMULATION COMPLETE")
    print("="*60)
    print(f"\nGo to Detection page, select {TARGET_USER}, and click 'Analyze Today'")
    print("Expected attack type should match what you selected")

if __name__ == "__main__":
    main()