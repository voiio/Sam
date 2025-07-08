# Contributing

## Getting Started

To install the dependencies, run the following command:

```bash
python -m pip install -r '.[test,lint]'
```

### Running a local instance

You can run sam locally in your terminal by running the following command:
```bash
sam run -v slack
```

You may also use Docker to run Sam. To do so, first ensure you have Docker and Docker Compose installed.

```bash
cp .env.example .env
# Edit the .env file to set your environment variables
docker-compose up --build
```

### Running Tests

To run the tests, run the following command:

```bash
python -m pytest
```

## Design Principles

With AI we have a unique opportunity to build a intelligent
that isn't prone to the same biases that humans are. We can
build a system that is fair and equitable to all.

### Gender Neutrality

Sam is a gender-neutral name by design. Though users may choose
to alter Sam's behavior to whatever they like. We must avoid
imposing our own biases on the system.

### Turing Test

Sam is designed decrease the barriers between human machine interaction.
We want to make it as easy as possible for humans to interact with Sam.
Sam should mimic human behavior as much as possible to be more approachable.

### Privacy

Sam is designed to be a personal assistant. Sam should not be used to collect
data on users. Sam should not be used to track users.
