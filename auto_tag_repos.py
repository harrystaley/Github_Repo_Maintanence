import os
import json
from github import Github

# --- Load Topic Rules ---
TOPIC_RULES_PATH = "topic_rules.json"  # Update this path if needed

try:
    with open(TOPIC_RULES_PATH, "r") as f:
        TOPIC_RULES = json.load(f)
except FileNotFoundError:
    print(f"❌ ERROR: Could not find topic rules file at {TOPIC_RULES_PATH}")
    exit(1)

# --- GitHub Auth ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not set in environment variables.")

g = Github(GITHUB_TOKEN)
user = g.get_user()

print(f"\n🔍 Logged in as: {user.login}")

# --- Process Repositories ---
for repo in user.get_repos():
    name = repo.name.lower()
    desc = (repo.description or "").lower()

    matched_topics = set()

    for keyword, topics in TOPIC_RULES.items():
        if keyword in name or keyword in desc:
            matched_topics.update(topics)

    if not matched_topics:
        print(f"❌ Skipped '{repo.name}': No topic rules matched.")
        continue

    try:
        print(f"🏷️ Tagging '{repo.name}' with: {matched_topics}")
        repo.replace_topics(list(matched_topics))
    except Exception as e:
        print(f"⚠️ Error tagging '{repo.name}': {e}")
