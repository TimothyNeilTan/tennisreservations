# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Install uv
RUN pip install uv

# 4. Copy dependency files
COPY pyproject.toml uv.lock requirements.txt ./

# 5. Install any needed packages specified in requirements.txt using uv
# Using --system to install packages globally in the container
RUN uv pip install --system --no-cache -r requirements.txt

# 5a. Install Playwright browser binaries
RUN playwright install --with-deps

# 6. Copy the rest of the application code into the container
COPY . .

# 7. Make port 8080 available to the world outside this container
EXPOSE 8080

# 8. Define environment variables (can be overridden)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8080
# Optional: Set PYTHONUNBUFFERED to ensure logs are output immediately
ENV PYTHONUNBUFFERED=1

# 9. Run app.py when the container launches using Gunicorn
# The command should be 'gunicorn module:variable'
# Here, module is 'app' (from app.py) and variable is 'app'
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"] 