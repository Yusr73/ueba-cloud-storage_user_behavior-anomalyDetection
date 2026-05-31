#!/usr/bin/env python3
"""
Daily Attack Simulation Script - With CORRECT Thresholds

=============================================================================
REAL THRESHOLDS FROM DATABASE (must EXCEED these):
=============================================================================
| Attack              | Alice                          | Bob                            |
|---------------------|--------------------------------|--------------------------------|
| RANSOMWARE          | writes > 3, paths > 264        | writes > 16, paths > 7408      |
| DATA_THEFT          | reads > 53, paths > 264        | reads > 428, paths > 7408      |
| DIRECTORY_TRAVERSAL | dir2 > 3                       | dir2 > 19                      |
| ACCOUNT_TAKEOVER    | attempts > 62, 25% success     | attempts > 188, 25% success    |
| BRUTE_FORCE         | attempts > 62, 0% success      | attempts > 188, 0% success     |
| MASS_ACTIVITY       | events > 688                   | events > 7525                  |
=============================================================================

SIMULATION VALUES:
=============================================================================
| Attack              | Alice                          | Bob                            |
|---------------------|--------------------------------|--------------------------------|
| RANSOMWARE          | 400 writes, 300 paths          | 10000 writes, 8000 paths       |
| DATA_THEFT          | 500 reads, 300 paths           | 10000 reads, 8000 paths        |
| DIRECTORY_TRAVERSAL | 30 directories                 | 30 directories                 |
| ACCOUNT_TAKEOVER    | 100 attempts, 25 successes     | 250 attempts, 63 successes     |
| BRUTE_FORCE         | 100 failed attempts            | 250 failed attempts            |
| MASS_ACTIVITY       | 1000 events on 3 paths         | 8000 events on 3 paths         |
=============================================================================
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import write_log
import time
import random

def clear_logs(uid):
    from models.database import get_db
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM logs WHERE time::date = CURRENT_DATE AND uid = %s", (uid,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Cleared {deleted} existing logs for {uid}")

def simulate_ransomware(uid, user_type):
    """RANSOMWARE: file_written + unique_paths above threshold"""
    print("\n" + "="*60)
    print(f"RANSOMWARE SIMULATION for {user_type.upper()}")
    print("="*60)
    
    if user_type == 'alice':
        NUM_WRITES = 400
        UNIQUE_PATHS = 300
        print(f"Alice needs: writes > 3, paths > 264")
    else:
        NUM_WRITES = 10000
        UNIQUE_PATHS = 8000
        print(f"Bob needs: writes > 16, paths > 7408")
        print(f"WARNING: This will generate {NUM_WRITES} events on {UNIQUE_PATHS} paths - will take time!")
    
    print(f"Generating {NUM_WRITES} writes on {UNIQUE_PATHS} unique paths...")
    
    paths = [f"/documents/file_{i}.encrypted" for i in range(UNIQUE_PATHS)]
    
    for i in range(NUM_WRITES):
        path = random.choice(paths)
        write_log(
            event_type="file_written",
            uid=uid,
            uid_type="name",
            params={"path": path, "size": 1048576},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        if (i + 1) % 500 == 0:
            print(f"  Progress: {i+1}/{NUM_WRITES}")
    
    print(f"✅ Generated {NUM_WRITES} file_written events on {UNIQUE_PATHS} unique paths")
    print("→ Expected: RANSOMWARE")

def simulate_data_theft(uid, user_type):
    """DATA_THEFT: file_accessed + unique_paths above threshold"""
    print("\n" + "="*60)
    print(f"DATA_THEFT SIMULATION for {user_type.upper()}")
    print("="*60)
    
    if user_type == 'alice':
        NUM_READS = 500
        UNIQUE_PATHS = 300
        print(f"Alice needs: reads > 53, paths > 264")
    else:
        NUM_READS = 10000
        UNIQUE_PATHS = 8000
        print(f"Bob needs: reads > 428, paths > 7408")
        print(f"WARNING: This will generate {NUM_READS} events on {UNIQUE_PATHS} paths - will take time!")
    
    print(f"Generating {NUM_READS} reads on {UNIQUE_PATHS} unique paths...")
    
    paths = [f"/documents/file_{i}.pdf" for i in range(UNIQUE_PATHS)]
    
    for i in range(NUM_READS):
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
        if (i + 1) % 500 == 0:
            print(f"  Progress: {i+1}/{NUM_READS}")
    
    print(f"✅ Generated {NUM_READS} file_accessed events on {UNIQUE_PATHS} unique paths")
    print("→ Expected: DATA_THEFT")

def simulate_account_takeover(uid, user_type):
    """ACCOUNT_TAKEOVER: Many logins, some succeed (25% success rate)"""
    print("\n" + "="*60)
    print(f"ACCOUNT_TAKEOVER SIMULATION for {user_type.upper()}")
    print("="*60)
    
    if user_type == 'alice':
        TOTAL_ATTEMPTS = 100
        SUCCESSFUL = 25
        print(f"Alice needs: attempts > 62")
    else:
        TOTAL_ATTEMPTS = 250
        SUCCESSFUL = 63
        print(f"Bob needs: attempts > 188")
    
    print(f"Generating {TOTAL_ATTEMPTS} login attempts, {SUCCESSFUL} successes (25% success rate)...")
    
    for i in range(TOTAL_ATTEMPTS):
        is_success = i < SUCCESSFUL
        
        write_log(
            event_type="login_attempt",
            uid=uid,
            uid_type="name",
            params={"username": uid, "success": is_success},
            is_local_ip=False,
            role=None,
            location={"country": "External"}
        )
        
        if is_success:
            write_log(
                event_type="login_successful",
                uid=uid,
                uid_type="name",
                params={"username": uid},
                is_local_ip=False,
                role="user",
                location={"country": "External"}
            )
        
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{TOTAL_ATTEMPTS} login attempts")
    
    success_rate = (SUCCESSFUL / TOTAL_ATTEMPTS) * 100
    print(f"✅ Generated {TOTAL_ATTEMPTS} login attempts, {SUCCESSFUL} successes ({success_rate:.0f}% success rate)")
    print("→ Expected: ACCOUNT_TAKEOVER")

def simulate_brute_force(uid, user_type):
    """BRUTE_FORCE: Many failed logins, zero successes"""
    print("\n" + "="*60)
    print(f"BRUTE_FORCE SIMULATION for {user_type.upper()}")
    print("="*60)
    
    if user_type == 'alice':
        FAILED_ATTEMPTS = 100
        print(f"Alice needs: attempts > 62")
    else:
        FAILED_ATTEMPTS = 250
        print(f"Bob needs: attempts > 188")
    
    print(f"Generating {FAILED_ATTEMPTS} failed login attempts (0% success rate)...")
    
    for i in range(FAILED_ATTEMPTS):
        write_log(
            event_type="login_attempt",
            uid=uid,
            uid_type="name",
            params={"username": uid, "success": False},
            is_local_ip=False,
            role=None,
            location={"country": "External"}
        )
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{FAILED_ATTEMPTS} failed attempts")
    
    print(f"✅ Generated {FAILED_ATTEMPTS} failed login attempts, 0 successes")
    print("→ Expected: BRUTE_FORCE")

def simulate_directory_traversal(uid, user_type):
    """DIRECTORY_TRAVERSAL: Many different directories"""
    print("\n" + "="*60)
    print(f"DIRECTORY_TRAVERSAL SIMULATION for {user_type.upper()}")
    print("="*60)
    
    directories = [f"dir_{i}" for i in range(30)]
    
    if user_type == 'alice':
        print(f"Alice needs: unique_dir2 > 3")
    else:
        print(f"Bob needs: unique_dir2 > 19")
    
    print(f"Generating accesses to {len(directories)} unique directories...")
    
    for directory in directories:
        for j in range(3):
            write_log(
                event_type="file_accessed",
                uid=uid,
                uid_type="name",
                params={"path": f"/{directory}/file_{j}.txt"},
                is_local_ip=True,
                role="user",
                location={"city": "unknown"}
            )
    
    print(f"✅ Generated accesses to {len(directories)} unique directories")
    print("→ Expected: DIRECTORY_TRAVERSAL")

def simulate_mass_activity(uid, user_type):
    """MASS_ACTIVITY: High volume on few paths (no unique_paths spike)"""
    print("\n" + "="*60)
    print(f"MASS_ACTIVITY SIMULATION for {user_type.upper()}")
    print("="*60)
    
    if user_type == 'alice':
        NUM_EVENTS = 1000
        print(f"Alice needs: events > 688")
    else:
        NUM_EVENTS = 8000
        print(f"Bob needs: events > 7525")
    
    PATHS = ['/documents/file1.txt', '/documents/file2.txt', '/documents/file3.txt']
    
    print(f"Generating {NUM_EVENTS} events on only {len(PATHS)} paths...")
    
    for i in range(NUM_EVENTS):
        path = random.choice(PATHS)
        write_log(
            event_type="file_accessed",
            uid=uid,
            uid_type="name",
            params={"path": path},
            is_local_ip=True,
            role="user",
            location={"city": "unknown"}
        )
        if (i + 1) % 1000 == 0:
            print(f"  Progress: {i+1}/{NUM_EVENTS} events")
    
    print(f"✅ Generated {NUM_EVENTS} events on only {len(PATHS)} paths")
    print("→ Expected: MASS_ACTIVITY")

def run_all(uid, user_type):
    """Run all simulations"""
    print("\n" + "="*60)
    print(f"RUNNING ALL SIMULATIONS for {user_type.upper()}")
    print("="*60)
    
    simulate_ransomware(uid, user_type)
    time.sleep(2)
    simulate_data_theft(uid, user_type)
    time.sleep(2)
    simulate_account_takeover(uid, user_type)
    time.sleep(2)
    simulate_brute_force(uid, user_type)
    time.sleep(2)
    simulate_directory_traversal(uid, user_type)
    time.sleep(2)
    simulate_mass_activity(uid, user_type)

def main():
    print("\n" + "="*60)
    print("DAILY ATTACK SIMULATION SUITE")
    print("="*60)
    
    print("\nSelect target user:")
    print("1. Alice")
    print("2. Bob (WARNING: Ransomware/DataTheft will take very long!)")
    choice = input("\nEnter choice (1-2): ")
    
    if choice == '1':
        TARGET_USER = 'alice'
        USER_TYPE = 'alice'
    else:
        TARGET_USER = 'bob'
        USER_TYPE = 'bob'
    
    clear = input(f"\nClear today's logs for {TARGET_USER}? (y/n): ")
    if clear.lower() == 'y':
        clear_logs(TARGET_USER)
    
    print("\nSelect attack:")
    print("1. RANSOMWARE")
    print("2. DATA_THEFT")
    print("3. ACCOUNT_TAKEOVER")
    print("4. BRUTE_FORCE")
    print("5. DIRECTORY_TRAVERSAL")
    print("6. MASS_ACTIVITY")
    print("7. RUN ALL")
    
    attack = input("\nEnter choice (1-7): ")
    
    if attack == '1':
        simulate_ransomware(TARGET_USER, USER_TYPE)
    elif attack == '2':
        simulate_data_theft(TARGET_USER, USER_TYPE)
    elif attack == '3':
        simulate_account_takeover(TARGET_USER, USER_TYPE)
    elif attack == '4':
        simulate_brute_force(TARGET_USER, USER_TYPE)
    elif attack == '5':
        simulate_directory_traversal(TARGET_USER, USER_TYPE)
    elif attack == '6':
        simulate_mass_activity(TARGET_USER, USER_TYPE)
    elif attack == '7':
        run_all(TARGET_USER, USER_TYPE)
    else:
        print("Invalid choice")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("SIMULATION COMPLETE")
    print("="*60)
    print(f"\nGo to Detection page, select {TARGET_USER}, click 'Analyze Today'")

if __name__ == "__main__":
    main()