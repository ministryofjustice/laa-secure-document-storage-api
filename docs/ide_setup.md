# PyCharm

The community edition can be used for our work, as the license does not restrict commercial development.

Ensure you have pipenv installed and accessible before starting.
In general this should be achievable with either `brew` or `sudo pip3 install pipenv`
You should be able to run `pipenv --version` from a terminal and get a sensible output.

## Configure python interpreter for the project

After starting PyCharm, open the directory containing the laa-secure-document-storage-api contents.

* Go to PyCharm → Settings…

* Expand Project: laa-secure-document-storage-api and select Python Interpreter

* Click Add Interpreter from the top right, and in the dialog enter:

  - Environment: `Generate new`

  - Type: `Pipenv`

  - Path to pipenv: `<select path to pipenv>`

    + Run `which pipenv` in a terminal to get the path

    + If pipenv is installed via a system Python, pipenv will be at `/Library/Frameworks/Python.framework/Versions/Current/bin/pipenv`

## Running unit-tests

* Right-click on the tests folder

* Select `Run pytest` in tests

* If the test fails on `top_level_collect`:

  - Click the three vertical dots next to pytest in tests in the top right

  - Select `Edit…` under Configuration

  - Change the Working directory to be one level higher, or simply replace with `$ContentRoot$`

## Running Flake8 linting

This is run as an `External tool` which is configured to use pipenv to invoke the flake8 module on the selected files
or directories.

* Go to PyCharm → Settings…

* Expand `Tools` and select `External tools`

* Click the `+` symbol and enter:

  - Name → `Linting` (can actually be anything, it is the name that will appear in the menu)

  - Program → `pipenv`

  - Arguments → `run python3 -m flake8 $FilePath$`

  - Working Directory → `$ContentRoot$`

  - Select `Make console active on message in stdout` and `Make console active on message in stderr`

* Click OK

You can now select a file or directory in the left navigation pane, right-click and select External tools → Linting

Any issues will appear as clickable links in the pop-up terminal window.

## Running the SDS API

* Use the menu Run → Edit Configurations...

* Select `Python` in the left tree, then `Add new run configuration…`

* Enter the following settings:

  - Name: `SDS API` (or similar)

  - Run: (should already be `pipenv`, otherwise select `Project default`)

  - Change `script` to `module` and enter `uvicorn`

  - Script parameters: `src.main:app --reload`

  - Working directory: `$ContentRoot$`

  - Path to “.env” files: `<full path to project .env>`

* Click OK

You should now be able to run the SDS API from the top right widget

Remember you will need to start the other docker services before running the SDS API in the IDE:
`docker compose up -d localstack laa-clamav`

And you can now also set breakpoints in the code and run in debug in the IDE :)
