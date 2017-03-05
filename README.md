# Squared Away Reporter

Some reporting application connected to MTO's Squared Away running on Flask with
Zappa and AWS Lambda functions.

## Running Locally

Copy the `config.py.example` file to `config.py` with real values for a database
connection URI and a secret key. This will only run with an application where the
database matches the schema in `models.py`, and it is intended as a read-only app.

Create a virtual environment, and run `pip install -r requirements.txt`. Once you've
installed dependencies, just run `python runserver.py` and you should see the application
running locally at `localhost:5000`.

## Deploying

If you want to deploy to AWS, you'll need valid AWS credentials set up locally.
To initially deploy the app, run `zappa deploy dev`, and to update it later run
`zappa update dev`.
