# Git Gallery 
## CSC325 - Group 2 Capstone

**Team Members:** Frank Baiata, Olena Fedochynska, Jordan Tisdol, Mariella Wood, Kailani Valladares

## Project Description

- Git, an industry standard version control tool, only produces text results when showing differences between code commits. This is useful for developers, but almost useless for a non-technical audience like designers or managers. Git Gallery instead produces visual results for the changes between commits for these users to view and compare how a webpage looked as it was changed over time. 
- The project will be narrowly scoped to ensure the team can complete it with the time given. Git Gallery accepts a link to a public GitHub repository and with a few additional (but optional) setup steps, produces the visual timeline for your project. The requirements to be an acceptable repository will be strict to ensure simple, repeatable functionality. The submitted GitHub project must be a simple HTML, CSS, and JavaScript website, with other criteria to ensure that it can be processed. 
- AI supports the project by selecting commits and interpreting their visual differences. It reviews commit messages and code changes to group consecutive commits into related milestones and recommends which commits to capture. For a selected screenshot pair, AI provides explanations of visible changes and highlights the areas of change. 
## Test Plan

Git Gallery will use two categories of tests to verify the user stories and acceptance criteria in [the Sprint 0 artifact](docs/sprint0-artifacts/Sprint0.md). These tests are planned for implementation as the application is developed.

### 1. Unit Testing

Unit tests will check individual functions in isolation, using mocked GitHub and AI responses so results are repeatable and do not depend on external services.

- **Repository validation:** Check valid GitHub repository URLs, empty or malformed inputs, unsupported dependencies, and missing HTML pages. Test commit-count boundaries of 0, 1, 50, and 51 to verify the supported 1–50 commit limit.
- **Commit selection and grouping:** Verify that selected commits belong to the repository and that AI-generated groups contain consecutive commits, with each analyzed commit appearing exactly once.
- **Processing status:** Verify that capture results produce the correct Complete, Partially Complete, or Failed status, while preserving successful results and recording failure reasons.
- **Screenshot processing:** Verify that screenshots are associated with the correct commit and selected HTML page. Test successful captures, missing screenshots, individual capture failures, and multiple screenshots across different commits.
- **Visual comparison:** Verify that when two commits are selected for comparison, the correct screenshots are matched to those commits and ordered correctly according to the comparison rules.
- **Error-message generation:** Verify that specific failures produce the correct user-facing error message.
- **AI response validation:** Verify that AI responses follow the expected structure, reference only valid commits and screenshots, and handle missing, malformed, or incomplete responses correctly.
  

Unit tests will run during development and before merging changes. Each test will compare the actual result with a defined expected result.

### 2. Integration and End-to-End Testing

These tests will verify that repository retrieval, screenshot capture, saved results, AI services, and the user interface work together. Small public test repositories with known HTML, CSS, and JavaScript changes will provide predictable inputs.

- **Complete user workflow:** Submit a supported repository, select an HTML page and commits, generate screenshots, navigate the visual timeline, compare versions, and reopen the saved analysis from the project gallery. Confirm that each screenshot matches its selected commit.
- **Failure handling and recovery:** Test inaccessible repositories, unsupported projects, GitHub or AI service failures, and individual screenshot failures. Confirm that users receive clear messages, successful captures remain available, and earlier saved analyses are preserved. Leave and reopen an analysis during processing to verify that progress is retained.
- **AI output quality:** Compare screenshots with known visible changes and an unchanged screenshot pair. Verify that explanations describe observable differences without inventing changes or unsupported behavior, and that commit-group recommendations refer to real commits and supporting changes. Use controlled responses for repeatable automated checks and manually review live AI results for accuracy.
- **Saved analysis and gallery:** Verify that completed analyses can be saved, reopened, renamed, and deleted. Confirm that repository information, commits, screenshots, AI results, and processing status are restored correctly when an analysis is reopened.
- **Screenshot pipeline:** Verify that selected commits are processed correctly and that screenshots are generated for the correct version of the project. Confirm that each screenshot is matched with the correct commit and selected HTML page.
  

Integration and end-to-end tests will run after major feature integration and before each sprint demonstration. Results will be checked against the relevant acceptance criteria, and failed scenarios will be recorded and retested after fixes.


## Steps to get setup

Setup Python Virtual Environment (Optional)

- ` python3 -m venv .venv `   
    - Creates a virtual python environment to install required packages on instead of local machine
- ` source .venv/bin/activate `
    - Used to enter the virtual python shell
    - ! Different command to use on windows !
    - ` .\.venv\Scripts\Activate.ps1 `

Setup Frontend React app

- Install Node (Setup using node v22.13.0)
    - https://nodejs.org/en/download

- The React app was already scaffolded using Vite (Build manager tool)
    - ! DO NOT RUN THIS COMMAND ! 
    - ` npm create vite@latest `
        - Name: Frontend
        - Framework: React
        - Variant: JavaScript
        - Linter: ESLint

- While in the `/backend` directory, run `npm install` to download the required dependencies

- To Start the dev server run `npm run dev`

Setup Django Backend

- A Template was used to scaffold this project 
    - https://github.com/mongodb-labs/django-mongodb-project
    - ! DO NOT RUN THIS COMMAND !
    - ` python -m django startproject config . --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/6.0.x.zip `

- ` python -m install -r requirements.txt `
    - Inside the python venv install the requirements
    - requirements include: Django, django-mongodb-backend, djangorestframework

