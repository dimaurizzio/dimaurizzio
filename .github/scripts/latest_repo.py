"""Write the newest public repository into README.md, between the LATEST_REPO markers.

Runs from the "Latest repo" workflow. Needs GITHUB_TOKEN; GITHUB_REPOSITORY_OWNER picks the user.
"""
import html
import json
import os
import pathlib
import re
import urllib.request

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "dimaurizzio")
README = pathlib.Path(__file__).resolve().parents[2] / "README.md"
START, END = "<!-- LATEST_REPO:START -->", "<!-- LATEST_REPO:END -->"

# Topic -> icon tile in assets/icons, shown under the card when the repo has that topic.
TOPIC_ICONS = {
    "google-adk": "adk", "adk": "adk", "gemini": "gemini", "vertex-ai": "vertexai",
    "mcp": "mcp", "model-context-protocol": "mcp", "langgraph": "langgraph", "langchain": "langchain",
    "rag": "langchain", "bigquery": "bigquery", "google-cloud": "googlecloud", "gcp": "googlecloud",
    "looker": "looker", "tableau": "tableau", "dbt": "dbt", "fastapi": "fastapi", "python": "python",
    "pydantic": "pydantic", "typescript": "ts", "react": "react", "nextjs": "nextjs", "nodejs": "nodejs",
    "docker": "docker", "postgresql": "postgres", "pandas": "pandas", "jupyter": "jupyter",
}
LANG_ICONS = {"Python": "python", "TypeScript": "ts", "JavaScript": "js"}

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 10, privacy: PUBLIC, isFork: false, ownerAffiliations: OWNER,
                 orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        name url description homepageUrl stargazerCount forkCount createdAt
        openGraphImageUrl usesCustomOpenGraphImage
        primaryLanguage { name }
        repositoryTopics(first: 20) { nodes { topic { name } } }
      }
    }
  }
}
"""


def fetch_latest():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": OWNER}}).encode(),
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    nodes = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]["repositories"]["nodes"]
    # The profile repo itself (owner/owner) is never the one to feature.
    return next((r for r in nodes if r["name"].lower() != OWNER.lower()), None)


def render(repo):
    esc = html.escape
    topics = [n["topic"]["name"] for n in repo["repositoryTopics"]["nodes"]]
    lang = (repo["primaryLanguage"] or {}).get("name")
    icons = []
    for key in ([LANG_ICONS.get(lang)] if lang else []) + [TOPIC_ICONS.get(t) for t in topics]:
        if key and key not in icons:
            icons.append(key)
    image = repo["openGraphImageUrl"]
    meta = [f"🗓️ {repo['createdAt'][:10]}"]
    # Counters only once they are worth showing.
    if repo["forkCount"]:
        meta.insert(0, f"🍴 {repo['forkCount']}")
    if repo["stargazerCount"]:
        meta.insert(0, f"⭐ {repo['stargazerCount']}")
    if lang:
        meta.insert(0, f"💻 {esc(lang)}")

    lines = [
        '<table align="center">',
        "  <tr>",
        '    <td align="center" width="720">',
        f'      <a href="{repo["url"]}"><img src="{image}" width="680" alt="{esc(repo["name"])}" /></a>',
        f'      <h3><a href="{repo["url"]}">{esc(repo["name"])}</a></h3>',
    ]
    # GitHub's default preview image already shows the description.
    if repo["description"] and repo["usesCustomOpenGraphImage"]:
        lines.append(f"      <p>{esc(repo['description'])}</p>")
    if icons:
        lines.append("      <p>")
        lines += [f'        <img src="assets/icons/{k}.svg" width="36" title="{k}" alt="{k}" />' for k in icons]
        lines.append("      </p>")
    if topics:
        lines.append("      <p>" + " ".join(f"<code>{esc(t)}</code>" for t in topics) + "</p>")
    lines.append(f"      <sub>{' &nbsp;·&nbsp; '.join(meta)}</sub>")
    if repo["homepageUrl"]:
        lines.append(f'      <br/><br/><a href="{esc(repo["homepageUrl"])}"><b>🌐 Live demo</b></a>')
    lines += ["    </td>", "  </tr>", "</table>"]
    return "\n".join(lines)


def main():
    repo = fetch_latest()
    if not repo:
        print("No public repository found; README left as is.")
        return
    text = README.read_text(encoding="utf-8")
    block = f"{START}\n{render(repo)}\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if new != text:
        README.write_text(new, encoding="utf-8", newline="\n")
        print(f"Featured {repo['name']}")
    else:
        print(f"{repo['name']} already featured")


if __name__ == "__main__":
    main()
