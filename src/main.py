import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import date, datetime
from typing import Dict, NamedTuple

from browser_lifecycle import BrowserManager
import llm_utils
import points_tracker
import rewards_tasks
from constants import (
    DEFAULT_MODEL,
    PROFILE_NAME,
    USER_DATA_DIR,
    DISABLE_DATABASE,
    AUTOMATIC,
    REWARDS_HEADLESS
)

# Force the database file to ALWAYS save in the main project folder
DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "completed_profiles.txt"))

# ==========================================
# 1. OLLAMA LIFECYCLE MANAGEMENT
# ==========================================

def ensure_ollama_running(model_name: str):
    """Lazy-start Ollama background process if it isn't running yet."""
    try:
        res = subprocess.run(["tasklist"], capture_output=True, text=True)
        if "ollama" not in res.stdout.lower():
            print("\n[PRE-FLIGHT] Starting Ollama background service...")
            subprocess.Popen(
                ["ollama", "run", model_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)
    except Exception as exc:
        print(f"[WARN] Failed to auto-start Ollama service: {exc}")

def kill_ollama(model_name: str):
    """Unload VRAM and terminate the Ollama background process."""
    print("\n[CLEANUP] Freeing 8GB memory and shutting down Ollama...")
    subprocess.run(["ollama", "stop", model_name], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "ollama*"], capture_output=True)

# ==========================================
# 2. PR-85 DATABASE & PROFILE MANAGEMENT
# ==========================================

class ProfileTask(NamedTuple):
    profile_name: str
    gaia_name: str
    user_name: str

def load_completed_profiles_today() -> set:
    """Reads DB_FILE and returns profile names completed on today's calendar date."""
    if DISABLE_DATABASE:
        return set()

    completed_today = set()
    today_str = date.today().isoformat()

    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "|" not in line:
                    continue
                prof_name, timestamp = line.rsplit("|", 1)
                if timestamp.strip().startswith(today_str):
                    completed_today.add(prof_name.strip())

    return completed_today

def mark_profile_completed(profile_name: str):
    """Appends profile completion with a full date and time timestamp."""
    if DISABLE_DATABASE:
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(f"{profile_name} | {now_str}\n")

def get_info_cache_from_local_state() -> dict:
    """Reads profile info cache directly from Edge's Local State file."""
    local_state_path = os.path.join(USER_DATA_DIR, "Local State")
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("profile", {}).get("info_cache", {})
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[ERROR] Could not read Local State: {exc}")
        return {}

# ==========================================
# 3. PR-75 TASK EXECUTION LOGIC
# ==========================================

def critical_tasks_succeeded(task_status: Dict[str, str]) -> bool:
    """True only if every gate task ran ('ok') in this run."""
    return all(status == "ok" for status in task_status.values())

def run_profile_execution(profile_name: str, args) -> bool:
    """Runs the PR-75 browser isolation and task execution for a specific profile."""
    print(f"\n[PRE-FLIGHT] Initializing isolated browser session for {profile_name}...")
    
    try:
        with BrowserManager(
            user_data_dir=USER_DATA_DIR,
            profile_name=profile_name,
            # Fix: Respect BOTH command line arguments and constants.py headless settings
            headless=(args.headless or getattr(constants, 'REWARDS_HEADLESS', REWARDS_HEADLESS)),
        ) as driver:
            print(f"[INFO] Browser session started successfully for {profile_name}.")

            rewards = rewards_tasks.RewardsTaskUtils(
                driver,
                debug_cursor=args.debug_cursor,
                enable_cooldown=not args.no_cooldown,
                enable_mobile=not args.no_mobile,
            )

            tracker = points_tracker.PointsTracker()
            tracker.record_start(driver)

            task_status = rewards.complete_all_tasks()

            rewards.switch_to_earn_page(refresh_wait=6.0)
            time.sleep(4.0)
            tracker.record_end(driver)

            if critical_tasks_succeeded(task_status):
                print(f"\n[DONE] All scheduled daily tasks finished for {profile_name}.")
                return True
            else:
                print(f"\n[CRITICAL] A critical task did not complete successfully for {profile_name}.")
                return False
    except Exception as exc:
        print(f"\n[FAIL] Execution failed for {profile_name}: {exc}")
        return False

# ==========================================
# 4. MAIN ORCHESTRATOR
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Automated Microsoft Rewards Farmer")
    parser.add_argument("--headless", action="store_true", help="Run Edge in headless mode")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Preferred Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--no-cooldown", action="store_true", help="Disable the 15-minute search cooldown loop")
    parser.add_argument("--no-mobile", action="store_true", help="Disable Edge Mobile search emulation")
    parser.add_argument("--debug-cursor", action="store_true", help="Render red tracking cursor")
    args = parser.parse_args()

    print("=" * 60)
    print("  Microsoft Rewards Farmer - Natural Human Emulation")
    print("=" * 60)

    profiles_data = get_info_cache_from_local_state()
    completed_today_set = load_completed_profiles_today()

    all_tasks = [
        ProfileTask(
            profile_name=prof,
            gaia_name=data.get("gaia_name", ""),
            user_name=data.get("user_name", ""),
        )
        for prof, data in profiles_data.items()
    ]

    if not all_tasks:
        print("[ERROR] No valid profiles detected in Local State.")
        sys.exit(1)

    available_tasks = [t for t in all_tasks if t.profile_name not in completed_today_set]

    if not available_tasks:
        print("\n🎉 All profiles are completed for today!")
        print("They will automatically become available again tomorrow.")
        sys.exit(0)

    try:
        ensure_ollama_running(args.model)
        resolved_model, is_online = llm_utils.resolve_available_model(args.model)
        
        if is_online:
            print(f"[PRE-FLIGHT] Ollama engine ready with model: {resolved_model}")
        else:
            print("[PRE-FLIGHT] Ollama offline or unavailable. Operating with intelligent offline fallback.")

        while True:
            available_tasks = [t for t in all_tasks if t.profile_name not in completed_today_set]
            if not available_tasks:
                print("\n🎉 All profiles are completed for today!")
                break

            print("\n" + "=" * 40)
            print("Remaining profiles to run:")
            for i, task in enumerate(available_tasks):
                print(f"({i}) [{task.profile_name}] | {task.gaia_name} | {task.user_name}")
            print("=" * 40)

            if not AUTOMATIC:
                input_number = input("Select Number: ").strip()
            else:
                random_index = random.randint(0, len(available_tasks) - 1)
                input_number = str(random_index)
                print(f"\n[AUTOMATIC MODE] Selected profile {input_number}")
                time.sleep(random.uniform(1, 3))

            if re.match(r"^\d+$", input_number):
                idx = int(input_number)
                if 0 <= idx < len(available_tasks):
                    selected_task = available_tasks[idx]
                    
                    success = run_profile_execution(selected_task.profile_name, args)
                    if success:
                        mark_profile_completed(selected_task.profile_name)
                        completed_today_set.add(selected_task.profile_name)

                    if not AUTOMATIC:
                        input("Press Enter to return to menu...")
                    else:
                        print(f"\n[AUTOMATIC] Finished {selected_task.profile_name}. Pausing for 5 seconds before booting the next profile...")
                        time.sleep(5)
                else:
                    print(f"Out of range. Pick between 0 and {len(available_tasks) - 1}.")
            else:
                print("Invalid input. NUMBERS ONLY.")
                
    finally:
        kill_ollama(args.model)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Run interrupted by user. Exiting cleanly.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[FATAL] Unhandled error: {exc}")
        sys.exit(1)