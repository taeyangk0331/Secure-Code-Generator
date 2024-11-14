# Makefile for setting up the environment and running the FastAPI server

.PHONY: install run

# Install dependencies from requirements.txt
install:
	sudo apt-get update && sudo apt-get install -y liblzma-dev
	pip install -r requirements.txt

# Run the FastAPI server
run:
	python3 server.py

# Install dependencies and run the server
start: install run
