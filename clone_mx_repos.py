import os
import subprocess
import requests
import time

TARGET_DIR = "/home/misi/MX_LINUX_RAG"
GITHUB_API_URL = "https://api.github.com/search/repositories?q=user:MX-Linux+language:C+language:C%2B%2B+language:Python+language:Shell&per_page=100&sort=stars"
GITHUB_API_URL_2 = "https://api.github.com/search/repositories?q=MX+Linux+language:C+language:C%2B%2B+language:Python+language:Shell&per_page=100&sort=stars"

def run_cmd(cmd):
    try:
        subprocess.run(cmd, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run command: {cmd}")

def get_repos(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('items', [])
    else:
        print(f"Failed to fetch repos from {url}. Status code: {response.status_code}")
        return []

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Target directory {TARGET_DIR} does not exist.")
        return

    repos = get_repos(GITHUB_API_URL) + get_repos(GITHUB_API_URL_2)

    unique_repos = {}
    for repo in repos:
        name = repo['name']
        clone_url = repo['clone_url']
        size = repo['size']
        if size > 10:
            unique_repos[name] = clone_url

    existing_dirs = os.listdir(TARGET_DIR)

    for name, clone_url in unique_repos.items():
        already_exists = False
        for d in existing_dirs:
            if name.lower() in d.lower():
                already_exists = True
                break

        if not already_exists:
            print(f"Cloning {name}...")
            clone_path = os.path.join(TARGET_DIR, name)
            run_cmd(f"git clone {clone_url} {clone_path}")
            time.sleep(1)

if __name__ == '__main__':
    main()
