# 🛠️ GitHub Repo Maintenance

Automate tagging and description updates for your GitHub repositories using the GitHub API and OpenAI.

This project provides tools to:
- Automatically assign topics (tags) to your repositories
- Generate clean, informative descriptions using GPT
- Keep your profile fresh and discoverable

---

## 📦 Features

✅ Add intelligent repo tags based on keywords  
✅ Update missing or weak descriptions using AI (GPT-3.5 or GPT-4)  
✅ Works with both public and private repos  
✅ Uses a `.env` file for secure key storage

---

## 🧰 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

**Required Packages:**

```
PyGithub==1.59.0
openai==1.10.0
python-dotenv==1.0.1
```

---

## 🔐 Setup

1. **Clone this repo**:

```bash
git clone https://github.com/your-username/GitHub_Repo_Maintenance.git
cd GitHub_Repo_Maintenance
```

2. **Create a `.env` file**:

```bash
touch .env
```

3. **Add your credentials**:

```
GITHUB_TOKEN=ghp_your_token_here
OPENAI_API_KEY=sk-your_openai_key
```

---

## 🏷️ Tag Repositories Automatically

Script: `auto_tag_repos.py`

Assigns topics to each repo using name/description keywords.

```bash
python auto_tag_repos.py
```

✅ Safe: Only updates topics  
🧠 Keyword-driven (editable in the script)

---

## ✍️ Generate Descriptions with AI

Script: `auto_describe_repos.py`

Uses OpenAI GPT to generate descriptions for repos missing them.

```bash
python auto_describe_repos.py
```

✅ Works on public & private repos  
📝 Uses README and topics for context  
🧠 Skips repos with decent existing descriptions

---

## 🧪 Example Output

```
🏷️ Tagging 'OMSCS-Anki' with: ['anki', 'flashcards', 'study']
✏️ Updated 'FASCLASS' → A Python scraper for federal position descriptions using FASCLASS.
```

---

## 🧠 Customization Ideas

- Add more keyword rules in `auto_tag_repos.py`
- Improve prompt logic in `auto_describe_repos.py`
- Schedule with GitHub Actions or CRON

---

## 👐 Contributing

Feel free to fork and improve this tool for your workflow! Pull requests welcome.

---

## ⚠️ License

MIT License — free for personal and commercial use.
