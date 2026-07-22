#!/usr/bin/env python3
"""
GitHub Repository Maintenance Tool

Automates three key repository maintenance tasks:
1. Auto-assign topics based on keyword rules
2. Generate/update README.md files using OpenAI
3. Generate/update repository descriptions using OpenAI

Usage:
    python repo_maintenance.py                    # Dry run with all features
    python repo_maintenance.py --apply            # Apply all changes
    python repo_maintenance.py --topics-only      # Only assign topics
    python repo_maintenance.py --readmes-only     # Only generate READMEs
    python repo_maintenance.py --descriptions-only # Only update descriptions
"""

import os
import json
import argparse
import difflib
from typing import Set, List, Dict, Optional, Tuple
from openai import OpenAI
from github import Github
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# --- GitHub and OpenAI Auth ---
GH_TOKEN = os.getenv("GH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not GH_TOKEN:
    raise ValueError("❌ GH_TOKEN not set in environment variables.")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not set in environment variables.")

# --- Initialize Clients ---
g = Github(GH_TOKEN)
user = g.get_user()
client = OpenAI(api_key=OPENAI_API_KEY)

print(f"\n🔍 Logged in as: {user.login}")


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

def load_config() -> Dict:
    """Load maintenance configuration from file."""
    config_path = "maintenance_config.json"
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Config file not found at {config_path}, using defaults")
        return get_default_config()


def get_default_config() -> Dict:
    """Return default configuration."""
    return {
        "excluded_repos": [".github.io"],
        "readme_generation": {
            "enabled": True,
            "create_if_missing": True,
            "update_existing": True,
            "skip_placeholder_repos": True,
            "max_tokens": 1500
        },
        "description_generation": {
            "enabled": True,
            "update_existing": True,
            "skip_if_similar": True,
            "similarity_threshold": 0.8,
            "max_tokens": 100
        },
        "topics_auto_assignment": {
            "enabled": True,
            "skip_if_topics_exist": False
        },
        "safety": {
            "dry_run_by_default": True,
            "require_confirmation": True,
            "verbose_logging": True
        }
    }


def load_topic_rules() -> Dict:
    """Load topic rules from JSON file."""
    rules_path = "topic_rules.json"
    try:
        with open(rules_path, "r") as f:
            rules = json.load(f)
            return {k.lower(): v for k, v in rules.items()}
    except FileNotFoundError:
        print(f"⚠️ Topic rules file not found at {rules_path}")
        return {}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def should_skip_repo(repo, excluded_repos: List[str]) -> bool:
    """Determine if a repo should be skipped."""
    if repo.fork or repo.archived:
        return True
    if repo.name in excluded_repos:
        return True
    if any(excluded in repo.name for excluded in excluded_repos):
        return True
    if repo.name == user.login or repo.name.endswith(".github.io"):
        return True
    return False


def is_placeholder_repo(repo) -> bool:
    """Check if repo contains only placeholder files."""
    try:
        contents = repo.get_contents("")
        file_names = {content.name for content in contents if content.type == "file"}
        placeholder_files = {"README.md", ".gitignore", "LICENSE", ".gitattributes"}
        return file_names.issubset(placeholder_files) or len(file_names) == 0
    except Exception:
        return False


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max length."""
    return text[:max_length] if len(text) > max_length else text


# ============================================================================
# TOPICS AUTO-ASSIGNMENT
# ============================================================================

def get_topics_for_repo(repo, topic_rules: Dict) -> Set[str]:
    """Generate topics for a repo based on rules."""
    if not topic_rules:
        return set()

    name = repo.name.lower()
    desc = (repo.description or "").lower()

    # Try to fetch README for additional context
    readme_content = ""
    try:
        readme = repo.get_readme()
        readme_content = readme.decoded_content.decode().lower()[:2000]
    except Exception:
        pass

    matched_topics = set()

    for keyword, topics in topic_rules.items():
        if keyword in name or keyword in desc or keyword in readme_content:
            matched_topics.update(topics)

    return matched_topics


def assign_topics(dry_run: bool = True, verbose: bool = True) -> Dict:
    """Auto-assign topics to all repos."""
    config = load_config()
    topic_rules = load_topic_rules()
    excluded_repos = config.get("excluded_repos", [])
    skip_if_exist = config["topics_auto_assignment"].get("skip_if_topics_exist", False)

    stats = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0}

    if not topic_rules:
        print("⚠️ No topic rules loaded. Skipping topic assignment.")
        return stats

    print("\n" + "=" * 70)
    print("🏷️  TOPIC AUTO-ASSIGNMENT")
    print("=" * 70)
    print(f"Mode: {'🔎 DRY RUN' if dry_run else '✅ APPLY'}\n")

    for repo in user.get_repos():
        if should_skip_repo(repo, excluded_repos):
            if verbose:
                print(f"⏭️  Skipping '{repo.name}' (fork/archived/excluded)")
            stats["skipped"] += 1
            continue

        try:
            existing_topics = set(repo.get_topics())

            if skip_if_exist and existing_topics:
                if verbose:
                    print(f"✅ Keeping existing topics for '{repo.name}': {sorted(existing_topics)}")
                stats["skipped"] += 1
                continue

            new_topics = get_topics_for_repo(repo, topic_rules)

            if not new_topics:
                if verbose:
                    print(f"❌ No matching topics for '{repo.name}'")
                stats["skipped"] += 1
                continue

            if new_topics == existing_topics:
                if verbose:
                    print(f"✅ Topics already correct for '{repo.name}'")
                stats["skipped"] += 1
                continue

            if dry_run:
                print(f"🔎 [DRY RUN] Would update '{repo.name}' → {sorted(new_topics)}")
            else:
                repo.replace_topics(sorted(new_topics))
                print(f"🏷️  Updated '{repo.name}' → {sorted(new_topics)}")

            stats["updated"] += 1
            stats["processed"] += 1

        except Exception as e:
            print(f"⚠️  Error processing '{repo.name}': {e}")
            stats["errors"] += 1

    return stats


# ============================================================================
# README GENERATION
# ============================================================================

def generate_readme_content(repo_name: str, description: str, topics: List[str]) -> str:
    """Generate README content using OpenAI."""
    config = load_config()
    max_tokens = config["readme_generation"].get("max_tokens", 1500)

    prompt = f"""You are a helpful assistant who writes high-quality GitHub README.md files.

Repo Name: {repo_name}
Description: {description}
Topics: {', '.join(topics) if topics else 'None'}

Generate a professional README.md that includes:
1. A brief project overview (what the project does)
2. Features or key components if applicable
3. Setup or installation instructions if applicable
4. Usage examples
5. Contribution guidelines (brief)
6. License section

Keep it concise but informative. Use proper markdown formatting.""".strip()

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


def update_readmes(dry_run: bool = True, verbose: bool = True) -> Dict:
    """Generate and update README.md files."""
    config = load_config()
    readme_config = config["readme_generation"]
    excluded_repos = config.get("excluded_repos", [])

    stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}

    if not readme_config.get("enabled", True):
        print("⚠️ README generation is disabled in config.")
        return stats

    print("\n" + "=" * 70)
    print("📄 README GENERATION")
    print("=" * 70)
    print(f"Mode: {'🔎 DRY RUN' if dry_run else '✅ APPLY'}\n")

    for repo in user.get_repos():
        if should_skip_repo(repo, excluded_repos):
            if verbose:
                print(f"⏭️  Skipping '{repo.name}' (fork/archived/excluded)")
            stats["skipped"] += 1
            continue

        if readme_config.get("skip_placeholder_repos", True) and is_placeholder_repo(repo):
            if verbose:
                print(f"⏭️  Skipping '{repo.name}' (placeholder repo)")
            stats["skipped"] += 1
            continue

        try:
            # Get existing README
            try:
                readme_file = repo.get_readme()
                if readme_file.name.lower() != "readme.md":
                    if verbose:
                        print(f"⏭️  Skipping '{repo.name}' (has special README: {readme_file.name})")
                    stats["skipped"] += 1
                    continue
                existing_readme = readme_file.decoded_content.decode()
                readme_sha = readme_file.sha
            except Exception:
                existing_readme = None
                readme_sha = None

            # Generate new README
            new_readme = generate_readme_content(
                repo_name=repo.name,
                description=repo.description or "",
                topics=repo.get_topics()
            )

            # Handle creation
            if existing_readme is None:
                if not readme_config.get("create_if_missing", True):
                    if verbose:
                        print(f"⏭️  Skipping '{repo.name}' (no README, creation disabled)")
                    stats["skipped"] += 1
                    continue

                if dry_run:
                    print(f"🔎 [DRY RUN] Would CREATE README.md for '{repo.name}'")
                else:
                    try:
                        repo.create_file("README.md", "docs: add auto-generated README", new_readme)
                        print(f"✅ Created README.md for '{repo.name}'")
                    except Exception as e:
                        print(f"⚠️  Failed to create README for '{repo.name}': {e}")
                        stats["errors"] += 1
                        continue

                stats["created"] += 1
                stats["processed"] += 1

            # Handle update
            else:
                if not readme_config.get("update_existing", True):
                    if verbose:
                        print(f"⏭️  Skipping '{repo.name}' (update disabled)")
                    stats["skipped"] += 1
                    continue

                if existing_readme.strip() == new_readme.strip():
                    if verbose:
                        print(f"✅ README.md for '{repo.name}' is already up to date")
                    stats["skipped"] += 1
                    continue

                if dry_run:
                    print(f"🔎 [DRY RUN] Would UPDATE README.md for '{repo.name}'")
                    if verbose:
                        similarity = calculate_similarity(existing_readme, new_readme)
                        print(f"   Similarity: {similarity:.1%}")
                else:
                    try:
                        repo.update_file("README.md", "docs: update auto-generated README", new_readme, readme_sha)
                        print(f"✏️  Updated README.md for '{repo.name}'")
                    except Exception as e:
                        print(f"⚠️  Failed to update README for '{repo.name}': {e}")
                        stats["errors"] += 1
                        continue

                stats["updated"] += 1
                stats["processed"] += 1

        except Exception as e:
            print(f"⚠️  Error processing '{repo.name}': {e}")
            stats["errors"] += 1

    return stats


# ============================================================================
# DESCRIPTION GENERATION
# ============================================================================

def generate_description(repo_name: str, readme_content: str, topics: List[str]) -> str:
    """Generate a description using OpenAI."""
    config = load_config()
    max_tokens = config["description_generation"].get("max_tokens", 100)

    readme_preview = truncate_text(readme_content, 1000)

    prompt = f"""You are an expert at writing concise GitHub repository descriptions.

Repo Name: {repo_name}
Topics: {', '.join(topics) if topics else 'None'}
README Preview: {readme_preview}

Write a 1–3 sentence GitHub description that:
- Clearly explains what the repo does
- Mentions key technologies if relevant
- Is professional and concise
- Fits in 140 characters or less if possible

Return ONLY the description text, nothing else.""".strip()

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


def update_descriptions(dry_run: bool = True, verbose: bool = True) -> Dict:
    """Generate and update repository descriptions."""
    config = load_config()
    desc_config = config["description_generation"]
    excluded_repos = config.get("excluded_repos", [])
    threshold = desc_config.get("similarity_threshold", 0.8)

    stats = {"processed": 0, "updated": 0, "kept": 0, "skipped": 0, "errors": 0}

    if not desc_config.get("enabled", True):
        print("⚠️ Description generation is disabled in config.")
        return stats

    print("\n" + "=" * 70)
    print("✏️  DESCRIPTION GENERATION")
    print("=" * 70)
    print(f"Mode: {'🔎 DRY RUN' if dry_run else '✅ APPLY'}\n")

    for repo in user.get_repos():
        if should_skip_repo(repo, excluded_repos):
            if verbose:
                print(f"⏭️  Skipping '{repo.name}' (fork/archived/excluded)")
            stats["skipped"] += 1
            continue

        try:
            # Get README content
            try:
                readme = repo.get_readme()
                readme_content = readme.decoded_content.decode()
            except Exception:
                readme_content = ""

            # Generate new description
            new_description = generate_description(
                repo_name=repo.name,
                readme_content=readme_content,
                topics=repo.get_topics()
            )

            old_description = repo.description or ""

            # Check if we should update
            if old_description:
                if desc_config.get("skip_if_similar", True):
                    similarity = calculate_similarity(old_description, new_description)
                    if similarity >= threshold:
                        if verbose:
                            print(f"✅ Keeping description for '{repo.name}' (similarity: {similarity:.1%})")
                        stats["kept"] += 1
                        continue

                if not desc_config.get("update_existing", True):
                    if verbose:
                        print(f"⏭️  Skipping '{repo.name}' (update disabled)")
                    stats["skipped"] += 1
                    continue

            if dry_run:
                print(f"🔎 [DRY RUN] Would update description for '{repo.name}'")
                if verbose:
                    print(f"   Old: {truncate_text(old_description, 70)}")
                    print(f"   New: {truncate_text(new_description, 70)}")
            else:
                try:
                    repo.edit(description=new_description)
                    print(f"✏️  Updated description for '{repo.name}'")
                    if verbose:
                        print(f"   → {truncate_text(new_description, 70)}")
                except Exception as e:
                    print(f"⚠️  Failed to update description for '{repo.name}': {e}")
                    stats["errors"] += 1
                    continue

            stats["updated"] += 1
            stats["processed"] += 1

        except Exception as e:
            print(f"⚠️  Error processing '{repo.name}': {e}")
            stats["errors"] += 1

    return stats


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="GitHub Repository Maintenance Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Dry run all tasks
  %(prog)s --apply                  # Apply all changes
  %(prog)s --topics-only --apply    # Only assign topics (apply)
  %(prog)s --readmes-only --dry-run # Only generate READMEs (dry run)
        """
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to GitHub (default is dry-run)"
    )
    parser.add_argument(
        "--topics-only",
        action="store_true",
        help="Only perform topic auto-assignment"
    )
    parser.add_argument(
        "--readmes-only",
        action="store_true",
        help="Only generate/update README.md files"
    )
    parser.add_argument(
        "--descriptions-only",
        action="store_true",
        help="Only generate/update repository descriptions"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce verbose output"
    )

    args = parser.parse_args()

    dry_run = not args.apply
    verbose = not args.quiet
    only_topics = args.topics_only
    only_readmes = args.readmes_only
    only_descriptions = args.descriptions_only

    # Determine which tasks to run
    run_topics = not any([only_readmes, only_descriptions]) or only_topics
    run_readmes = not any([only_topics, only_descriptions]) or only_readmes
    run_descriptions = not any([only_topics, only_readmes]) or only_descriptions

    print("\n" + "=" * 70)
    print("🔧 GITHUB REPOSITORY MAINTENANCE TOOL")
    print("=" * 70)
    print(f"User: {user.login}")
    print(f"Mode: {'🔎 DRY RUN' if dry_run else '✅ APPLY CHANGES'}")
    print(f"Verbose: {verbose}")
    print(f"Tasks: Topics={run_topics}, READMEs={run_readmes}, Descriptions={run_descriptions}")

    all_stats = {}

    try:
        if run_topics:
            all_stats["topics"] = assign_topics(dry_run=dry_run, verbose=verbose)

        if run_readmes:
            all_stats["readmes"] = update_readmes(dry_run=dry_run, verbose=verbose)

        if run_descriptions:
            all_stats["descriptions"] = update_descriptions(dry_run=dry_run, verbose=verbose)

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return

    # Print summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)

    for task_name, stats in all_stats.items():
        print(f"\n{task_name.upper()}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    if dry_run:
        print("\n💡 This was a DRY RUN. Use --apply to commit changes to GitHub.")
    else:
        print("\n✅ All changes have been applied to GitHub!")

    print()


if __name__ == "__main__":
    main()
