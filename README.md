# Squared Away Reporter

Some reporting application connected to MTO's Squared Away running on Flask with
Zappa and AWS Lambda functions.

## Running Locally

Set environment variables (database connection information in `database.py`, and
`SECRET_KEY`). This will only run with an application where the database matches
the schema in `models.py`, and it is intended as a read-only app.

Create a virtual environment, and run `pip install -r requirements.txt`. Once you've
installed dependencies, just run `python runserver.py` and you should see the application
running locally at `localhost:5000`.

## Deploying

If you want to deploy to AWS, you'll need valid AWS credentials set up locally.
To initially deploy the app, run `zappa deploy dev`, and to update it later run
`zappa update dev`.

## Credits

pyrtree implementation [BSD-licensed](https://opensource.org/licenses/BSD-3-Clause), [original source on Google Code](https://code.google.com/archive/p/pyrtree/).
