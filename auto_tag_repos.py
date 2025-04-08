import os
import json
from github import Github
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not set in environment variables.")

# Load topic rules
TOPIC_RULES_PATH = "topic_rules.json"
try:
    with open(TOPIC_RULES_PATH, "r") as f:
        TOPIC_RULES = json.load(f)
        TOPIC_RULES = {k.lower(): v for k, v in TOPIC_RULES.items()}  # Normalize
except FileNotFoundError:
    print(f"❌ ERROR: Could not find topic rules file at {TOPIC_RULES_PATH}")
    exit(1)

# Authenticate with GitHub
g = Github(GITHUB_TOKEN)
user = g.get_user()
print(f"\n🔍 Logged in as: {user.login}")

# Loop through user repositories
for repo in user.get_repos():
    if repo.fork or repo.archived:
        print(f"⏭️ Skipping '{repo.name}' (fork or archived)")
        continue

    name = repo.name.lower()
    desc = (repo.description or "").lower()

    # Try to fetch README for additional context
    readme_content = ""
    try:
        readme = repo.get_readme()
        readme_content = readme.decoded_content.decode().lower()
    except Exception:
        pass

    matched_topics = set()

    for keyword, topics in TOPIC_RULES.items():
        if keyword in name or keyword in desc or keyword in readme_content:
            matched_topics.update(topics)

    if not matched_topics:
        print(f"❌ Skipped '{repo.name}': No topic rules matched.")
        continue

    try:
        print(f"🏷️ Tagging '{repo.name}' with: {sorted(matched_topics)}")
        repo.replace_topics(sorted(matched_topics))
    except Exception as e:
        print(f"⚠️ Error tagging '{repo.name}': {e}")
