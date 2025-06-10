FROM python:3.11.0

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt

# Copy the application code
COPY . /app

# Expose the port the app runs on
EXPOSE 80

# Start Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--ws-ping-interval", "30", "--ws-ping-timeout", "20"]