# Use a lightweight Python image
FROM python:3.13-slim

# Set environment variables for Poetry
ENV POETRY_VERSION=1.5.1
ENV PORT=8080

# Install Poetry and dependencies
RUN pip install "poetry==$POETRY_VERSION"

# Set the working directory
WORKDIR /app

# Copy only pyproject.toml and poetry.lock to leverage Docker caching for dependencies
COPY pyproject.toml poetry.lock ./

# Install dependencies without creating a virtual environment
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Copy the rest of the application code
COPY . .

# Configure Streamlit for Cloud Run
RUN mkdir -p ~/.streamlit && \
    echo "[server]\nheadless = true\nport = ${PORT}\nenableCORS = false\n" > ~/.streamlit/config.toml

# Expose the port Streamlit will use
EXPOSE 8080

# Start Streamlit using Poetry
CMD ["poetry", "run", "streamlit", "run", "main.py", "--server.port=8080", "--server.enableCORS=false"]
