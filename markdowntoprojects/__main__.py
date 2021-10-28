import os
import yaml
import logging
import argparse
from typing import List
from dataclasses import dataclass

from requests import session as requests_session

from markdowntoprojects.models import *

# read project directory from file
# connect to github api to create a new project from a markdown file

parser = argparse.ArgumentParser(
    description="Create a new GitHub project from a markdown file"
)
parser.add_argument("--debug", action="store_true", help="debug mode")
parser.add_argument(
    "-p", "--project-path", default=os.environ.get("PROJECT_PATH"), help="project path"
)

parser_github = parser.add_argument_group("GitHub")
parser_github.add_argument(
    "-t", "--token", help="GitHub token", default=os.environ.get("GITHUB_TOKEN")
)
parser_github.add_argument(
    "-r", "--repository", help="GitHub repository", required=True
)


@dataclass
class GitHub:
    repository: str
    token: str

    session: requests_session = None

    def __post_init__(self):
        self.session = requests_session()
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    def createProject(self, name: str, description: str):
        """
        Create a new GitHub project from a markdown file
        :param name: name of the project
        :param repository: repository name
        :param token: GitHub token
        :return:
        """
        logging.info(f"Creating project {name}")
        with self.session.post(
            f"https://api.github.com/repos/{self.repository}/projects",
            json={"name": name, "body": description},
        ) as response:
            if response.status_code == 201:
                return response.json()
            raise Exception(response.json())

    def createColumn(self, project_id: int, name: str):
        """Create a new column in a project
        :param project_id: project id
        :param name: name of the column
        :return:
        """
        logging.info(f"Creating column {name}")
        with self.session.post(
            f"https://api.github.com/projects/{project_id}/columns",
            json={"name": name},
        ) as response:
            if response.status_code == 201:
                return response.json()
            raise Exception(response.json())

    def createIssue(
        self, name: str, content: str, labels: List[str], assignees: List[str] = []
    ):
        """
        Create a new issue in the project
        :param name: name of the issue
        :param content: markdown content
        :param labels: list of labels
        :return:
        """
        logging.info(f"Creating issue {name}")
        with self.session.post(
            f"https://api.github.com/repos/{self.repository}/issues",
            json={
                "title": name,
                "body": content,
                "labels": labels,
                "assignees": assignees,
            },
        ) as response:
            if response.status_code == 201:
                return response.json()
            raise Exception(response.json())

    def createProjectCard(self, column_id: int, issue_id: int):
        """
        Create a new project card
        :param column_id: column id
        :param issue_id: issue id
        :return:
        """
        logging.info(f"Creating project card: {column_id} -> {issue_id}")
        with self.session.post(
            f"https://api.github.com/projects/columns/{column_id}/cards",
            json={"content_id": issue_id, "content_type": "Issue"},
        ) as response:
            if response.status_code == 201:
                return response.json()
            raise Exception(response.json())


if __name__ == "__main__":
    arguments = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if arguments.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logging.info(f"Repository :: {arguments.repository}")
    logging.info(f"Project Path :: {arguments.project_path}")

    with open(arguments.project_path, "r") as config_file:
        config = loader(Config, yaml.safe_load(config_file))

    github = GitHub(arguments.repository, arguments.token)
    # create project board
    project = github.createProject(config.project.name, config.project.description)

    # create columns
    default_column = None
    columns = []
    for column in config.project.columns:
        c = github.createColumn(project.get("id"), column)
        columns.append((column, c.get("id")))

        if column == config.default_column:
            default_column = c.get("id")

        logging.info(f"Created column {column} ({c.get('id')})")

    # create issues
    for issue in config.issues:
        # read markdown file
        root = os.path.join(config.root, issue.content)
        with open(root, "r") as content_file:
            content = content_file.read()

        # create issue
        i = github.createIssue(issue.name, content, issue.labels)
        issue.id = i.get("id")
        logging.info(f"Created issue {issue.id}")

        # find column
        column_id = None
        for column, c_id in columns:
            if column in issue.labels:
                column_id = c_id
                break

        if column_id is None:
            logging.warning(f"No column found for '{issue.name}' ()")
            # set to default column
            column_id = default_column

        # create project cards
        github.createProjectCard(column_id, issue.id)

    logging.info("Done")
