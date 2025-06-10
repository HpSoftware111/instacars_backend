import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import BotoCoreError, ClientError

# Load environment variables from .env
load_dotenv()


class EmailService:
    def __init__(self):
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY")
        self.aws_secret_key = os.getenv("AWS_SECRET_KEY")
        self.aws_region = os.getenv("AWS_REGION")

        # Initialize the SES client
        self.client = boto3.client(
            'ses',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.aws_region
        )

    def send_email(self, recipient, subject, body, charset="UTF-8"):
        sender = "Instacars <noreply@instacars.io>"
        try:
            response = self.client.send_email(
                Destination={
                    'ToAddresses': [recipient],
                },
                Message={
                    'Body': {'Text': {'Charset': charset, 'Data': body}},
                    'Subject': {'Charset': charset, 'Data': subject},
                },
                Source=sender
            )
            print("✅ Email sent successfully! Message ID:", response['MessageId'])
            return response['MessageId']
        except (BotoCoreError, ClientError) as error:
            print("❌ Error sending email:", error)
            return None
        