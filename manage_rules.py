import json
import sys

RULES_FILE = "topic_rules.json"

def load_rules():
    try:
        with open(RULES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_rules(rules):
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)

def add_keyword(keyword, topics):
    rules = load_rules()
    rules[keyword.lower()] = topics
    save_rules(rules)
    print(f"✅ Added keyword '{keyword}' with topics: {topics}")

def remove_keyword(keyword):
    rules = load_rules()
    if keyword.lower() in rules:
        del rules[keyword.lower()]
        save_rules(rules)
        print(f"✅ Removed keyword '{keyword}'")
    else:
        print(f"❌ Keyword '{keyword}' not found")

def list_rules():
    rules = load_rules()
    if not rules:
        print("No rules found. Create some with: python manage_rules.py add <keyword> <topic1> <topic2>...")
        return
    print("\nCurrent rules:")
    for keyword, topics in sorted(rules.items()):
        print(f"  {keyword}: {topics}")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage_rules.py [add|remove|list] [keyword] [topics...]")
        print("\nExamples:")
        print("  python manage_rules.py list")
        print("  python manage_rules.py add python python scripting")
        print("  python manage_rules.py add api api rest backend")
        print("  python manage_rules.py remove oldkeyword")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_rules()
    elif command == "add" and len(sys.argv) >= 4:
        keyword = sys.argv[2]
        topics = sys.argv[3:]
        add_keyword(keyword, topics)
    elif command == "remove" and len(sys.argv) >= 3:
        keyword = sys.argv[2]
        remove_keyword(keyword)
    else:
        print("❌ Invalid command")
