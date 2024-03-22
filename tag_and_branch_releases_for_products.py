"""
Description: This Python script interacts with GitHub and Jira APIs to automate the triggering of
GitHub Actions workflows based on Jira ticket data and product mappings. It validates the presence of 
product mappings in a JSON file, fetches Jira ticket data, and triggers workflows for each product. The script 
is designed to enhance the release process by automating the creation of release branches and workflow triggers.

Features:
- Retrieves Jira ticket data using a Jira API token.
- Validates product mappings to ensure that all products in Jira have corresponding mappings.
- Triggers GitHub Actions workflow for each product based on retrieved Jira data.
- Creates release branches and RC Tags.

Usage: 
The script requires necessary environment variables and a JSON file containing product repository mappings. 
It uses command-line arguments to specify the owner, base branch, and Jira ticket. After validation, 
it triggers workflows for each product to facilitate release management.

Dependencies: The script uses the 'requests' module to interact with APIs and requires Python 3.x.

Note: 
Ensure that environment variables ('GH_TOKEN' and 'JIRA_TOKEN') are properly set, 
the JSON file ('product_repo_mappings.json') is available, and the required modules are installed before running the script.
"""

import requests
import os
import argparse
import json
import sys

_gh_token = os.getenv('GH_TOKEN')
_jira_token = os.getenv('JIRA_TOKEN')
_workflow_id = "66795811" # workflow id for 'Create Releaase Branch and RC Tag'
_workflow_repo = "pdk-devops" # workflow repo for Create Release for all PDK Projects

def validate_product_mappings(jira_data, dictionary_data):
    all_found = True
    if jira_data:
        for data in jira_data["fields"]["customfield_15702"]:
            last_space_index = data["name"].rfind(" ")
            product = data["name"][:last_space_index].lower()

            if product not in dictionary_data:
                all_found = False
                print(f'Product mapping not found for: {product}')
                
    return all_found

def trigger_github_workflow(owner, workflow_repo, workflow_id, base_branch, repo, release_branch):
    url = f"https://api.github.com/repos/{owner}/{workflow_repo}/actions/workflows/{workflow_id}/dispatches"

    headers = {
        "Authorization": f"Bearer {_gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "ref": base_branch,
        "inputs": {
            "owner": owner,
            "repo": repo,
            "base_branch": base_branch,
            "release_branch": release_branch
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 204:
        print("Workflow dispatched successfully.")
    else:
        print("Failed to dispatch workflow. Status code:", response.status_code)
        print("Response content:", response.content)

def get_jira_product_data(jira_ticket):
    base_url = f'https://jira.mdsol.com/rest/api/latest/issue/{jira_ticket}' 
    headers = {
        "Authorization": f"Basic {_jira_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(base_url, headers=headers)

    if response.status_code == 200:
        issue_data = response.json()
        return issue_data
    else:
        print(f"Failed to retrieve MDSO Jira Information. Status Code: {response.status_code}")
        sys.exit(1)
#
# entry point
#
def main():
    parser = argparse.ArgumentParser(description="Trigger a GitHub Actions workflow.")
    parser.add_argument("-owner", required=True, help="Owner of the repository")
    parser.add_argument("-base_branch", required=True, help="Base branch for the workflow")
    parser.add_argument("-jira_ticket", required=True, help="Jira ticket to get product data from (e.g. MDSO-19142)")
    parser.add_argument("-dry_run", required=True, help="Dry run mode. Does not trigger workflow that creates release branches.")
    args = parser.parse_args()
    
    is_dry_run = args.dry_run == "true"
    
    #   Get product data from Jira
    jira_data = get_jira_product_data(args.jira_ticket)

    # Read the product mappings from the JSON file
    with open("product_repo_mappings.json") as product_mappings_file:
        dictionary_data = json.load(product_mappings_file)

    # Validate that all products in Jira have a mapping
    # If not, exit and fail the script
    all_products_found = validate_product_mappings(jira_data, dictionary_data)
    if not all_products_found:
        print("Some product mappings were not found. Exiting.")
        print("Please add the missing product mappings to product_repo_mappings.json")
        sys.exit(1)

    if jira_data:
        if is_dry_run:
                print("*** dry run mode - print workflow trigger call ***\n")
                
        for data in jira_data["fields"]["customfield_15702"]:
            name = data["name"]
            last_space_index = name.rfind(" ")

            product = name[:last_space_index].lower()
            release_branch = f"release/{name[last_space_index+1:]}"
            repo_details = dictionary_data.get(product, {})
            repo = repo_details.get('repo')
            skip = repo_details.get('skip') == "true"
            
            if not skip:
                if is_dry_run:
                    print(f'\tProduct: {product}')
                    print(f'\tpython3 trigger_github_workflow.py -owner {args.owner} -workflow_repo {_workflow_repo} -workflow_id {_workflow_id} -repo {repo} -base_branch {args.base_branch} -release_branch {release_branch}\n')
                else:
                    trigger_github_workflow(args.owner, _workflow_repo, _workflow_id, args.base_branch, repo, release_branch)

        if is_dry_run:
            print("*** dry run mode - end print workflow trigger call ***")

if _name_ == "_main_":
    main()
