import os
from openai import OpenAI
from github import Github
from dotenv import load_dotenv
import difflib
import traceback

# Load environment variables
load_dotenv()

# --- GitHub and OpenAI Auth ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not set in environment variables.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment variables.")


# Set up OpenAI key (no proxies, no extras)
client = OpenAI(api_key=OPENAI_API_KEY)

# GitHub authentication
g = Github(login_or_token=GITHUB_TOKEN)
user = g.get_user()

# Generate a new GitHub description based on the repo name, topics, and readme
def generate_description(name, readme, topics):
    prompt = f"""You are an assistant that writes clean, professional GitHub repo descriptions.
Repo Name: {name}
Topics: {', '.join(topics)}
README (first 1000 characters): {readme[:1000]}

Write a 1–2 sentence summary of this repo for the GitHub description field:"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=100
    )

    return response.choices[0].message.content.strip()

# Determine whether the new description is better
def is_better(new_desc, old_desc):
    if not old_desc:
        return True
    if len(new_desc) > len(old_desc) + 10:
        return True
    similarity = difflib.SequenceMatcher(None, old_desc.lower(), new_desc.lower()).ratio()
    return similarity < 0.85

# Main loop to go through repos
if __name__ == "__main__":
    for repo in user.get_repos():
        try:
            name = repo.name
            topics = repo.get_topics()

            # Get README content if available
            try:
                readme = repo.get_readme()
                readme_content = readme.decoded_content.decode()
            except:
                readme_content = ""

            old_description = repo.description or ""
            new_description = generate_description(name, readme_content, topics)

            if is_better(new_description, old_description):
                repo.edit(description=new_description)
                print(f"✏️ Updated '{name}' → {new_description}")
            else:
                print(f"✅ Kept existing description for '{name}'")

        except Exception as e:
            traceback.print_exc()
            print(f"⚠️ Error processing '{repo.name}': {e}")
