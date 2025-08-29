# Dockerfile

# Use a Python base image
FROM python:3.10-slim-buster

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app
WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt $APP_HOME/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project code
COPY . $APP_HOME/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Gunicorn will listen on
EXPOSE 8000

# Run Gunicorn to serve the application
CMD ["gunicorn", "paragourmet.wsgi:application", "--bind", "0.0.0.0:8000"]
