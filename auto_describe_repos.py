import os
from github import Github
from dotenv import load_dotenv
import openai

# Load API keys
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
g = Github(os.getenv("GITHUB_TOKEN"))
user = g.get_user()

def generate_description(name, readme, topics):
    prompt = f"""You are an assistant that writes clean, professional GitHub repo descriptions.
Repo Name: {name}
Topics: {', '.join(topics)}
README: {readme[:1000]}  # (trimmed for length)

Write a 1–2 sentence summary of this repo for the GitHub description field:"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=100
    )
    return response['choices'][0]['message']['content'].strip()

for repo in user.get_repos():
    try:
        name = repo.name
        topics = repo.get_topics()
        readme_content = ""
        try:
            readme = repo.get_readme()
            readme_content = readme.decoded_content.decode()
        except:
            pass

        if repo.description and len(repo.description.strip()) > 10:
            print(f"✅ Skipping '{name}' (already has description).")
            continue

        description = generate_description(name, readme_content, topics)
        repo.edit(description=description)
        print(f"✏️ Updated '{name}' → {description}")

    except Exception as e:
        print(f"⚠️ Error processing '{repo.name}': {e}")
