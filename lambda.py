import boto3
import json
import time
import urllib.parse
import urllib.request
import os
import traceback
import uuid

# =========================================================
# AWS CLIENTS
# =========================================================
s3 = boto3.client("s3")

transcribe = boto3.client(
    "transcribe",
    region_name="us-east-1"
)

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

mediaconvert = boto3.client(
    "mediaconvert",
    region_name="us-east-1"
)

# =========================================================
# CONFIG
# =========================================================
BUCKET_NAME = "video-resume-uploads"

NOVA_MODEL_ID = "amazon.nova-lite-v1:0"

# =========================================================
# CORS
# =========================================================
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
}

# =========================================================
# GENERATE PRESIGNED URL
# =========================================================
def generate_upload_url():

    try:

        file_id = str(uuid.uuid4())

        file_name = f"uploads/{file_id}.mp4"

        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": file_name,
                "ContentType": "video/mp4"
            },
            ExpiresIn=3600
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "uploadURL": upload_url,
                "videoKey": file_name
            })
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "error": str(e)
            })
        }

# =========================================================
# GET RESULT
# =========================================================
def get_result(event):

    try:

        params = event.get("queryStringParameters", {})

        video_key = params.get("videoKey")

        if not video_key:

            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "error": "videoKey missing"
                })
            }

        file_name = os.path.splitext(
            os.path.basename(video_key)
        )[0]

        result_key = f"results/{file_name}.json"

        print("Fetching:", result_key)

        response = s3.get_object(
            Bucket=BUCKET_NAME,
            Key=result_key
        )

        result_json = response["Body"].read().decode("utf-8")

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": result_json
        }

    except Exception as e:

        print("Result not ready:", str(e))

        return {
            "statusCode": 404,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "status": "PROCESSING"
            })
        }

# =========================================================
# CREATE HTML RESUME
# =========================================================
def create_html_resume(resume_text, output_path):

    safe_resume = resume_text.replace("\n", "<br>")

    html_content = f"""
    <html>
    <head>
        <title>AI Resume</title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                padding: 40px;
            }}

            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>AI Generated Resume</h1>

            <p>{safe_resume}</p>

        </div>

    </body>

    </html>
    """

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)

# =========================================================
# CREATE BULLET HTML
# =========================================================
def create_bullet_html(bullet_points, output_path):

    bullets = ""

    for line in bullet_points.split("\n"):

        line = line.strip()

        if line:
            bullets += f"<li>{line}</li>"

    html_content = f"""
    <html>

    <head>

        <title>Highlights</title>

        <style>

            body {{
                background: black;
                color: white;
                font-family: Arial;
                padding: 80px;
            }}

            h1 {{
                color: cyan;
                text-align: center;
            }}

            li {{
                font-size: 32px;
                margin-bottom: 25px;
            }}

        </style>

    </head>

    <body>

        <h1>Resume Highlights</h1>

        <ul>
            {bullets}
        </ul>

    </body>

    </html>
    """

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)

# =========================================================
# CREATE HIGHLIGHT VIDEO
# =========================================================
def create_highlight_clip(bucket, input_key):

    try:

        endpoints = mediaconvert.describe_endpoints()

        endpoint_url = endpoints["Endpoints"][0]["Url"]

        mc_client = boto3.client(
            "mediaconvert",
            region_name="us-east-1",
            endpoint_url=endpoint_url
        )

        file_name = os.path.splitext(
            os.path.basename(input_key)
        )[0]

        output_destination = f"s3://{bucket}/clips/"

        job_settings = {

            "Inputs": [
                {
                    "FileInput": f"s3://{bucket}/{input_key}"
                }
            ],

            "OutputGroups": [
                {
                    "Name": "File Group",

                    "OutputGroupSettings": {
                        "Type": "FILE_GROUP_SETTINGS",

                        "FileGroupSettings": {
                            "Destination": output_destination
                        }
                    },

                    "Outputs": [
                        {
                            "NameModifier": "_highlight",

                            "ContainerSettings": {
                                "Container": "MP4"
                            },

                            "VideoDescription": {
                                "CodecSettings": {
                                    "Codec": "H_264",

                                    "H264Settings": {
                                        "RateControlMode": "QVBR"
                                    }
                                }
                            }
                        }
                    ]
                }
            ]
        }

        mc_client.create_job(
            Role=os.environ["MEDIACONVERT_ROLE"],
            Settings=job_settings
        )

        clip_url = (
            f"https://{bucket}.s3.amazonaws.com/"
            f"clips/{file_name}_highlight.mp4"
        )

        return clip_url

    except Exception as e:

        traceback.print_exc()

        return ""

# =========================================================
# PROCESS VIDEO
# =========================================================
def process_uploaded_video(event):

    try:

        bucket = event["Records"][0]["s3"]["bucket"]["name"]

        key = urllib.parse.unquote_plus(
            event["Records"][0]["s3"]["object"]["key"]
        )

        print("Uploaded File:", key)

        # =========================================================
        # SKIP GENERATED FILES
        # =========================================================
        if (
            key.startswith("clips/")
            or key.startswith("results/")
            or key.startswith("resumes/")
        ):

            return {
                "statusCode": 200,
                "body": "Skipped Generated File"
            }

        if not key.lower().endswith(".mp4"):

            return {
                "statusCode": 200,
                "body": "Not MP4"
            }

        file_name = os.path.splitext(
            os.path.basename(key)
        )[0]

        media_uri = f"s3://{bucket}/{key}"

        print("Media URI:", media_uri)

        # =========================================================
        # START TRANSCRIBE
        # =========================================================
        job_name = f"job-{uuid.uuid4()}"

        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={
                "MediaFileUri": media_uri
            },
            MediaFormat="mp4",
            LanguageCode="en-US"
        )

        print("Transcription Started")

        # =========================================================
        # WAIT
        # =========================================================
        while True:

            status = transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )

            job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]

            print("Status:", job_status)

            if job_status == "COMPLETED":
                break

            if job_status == "FAILED":

                return {
                    "statusCode": 500,
                    "body": "Transcription Failed"
                }

            time.sleep(10)

        # =========================================================
        # TRANSCRIPT
        # =========================================================
        transcript_url = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]

        response = urllib.request.urlopen(transcript_url)

        transcript_json = json.loads(response.read())

        transcript_text = transcript_json["results"]["transcripts"][0]["transcript"]

        print("Transcript Extracted")

        # =========================================================
        # RESUME GENERATION
        # =========================================================
        prompt = f"""
Create professional ATS-friendly resume.

Transcript:

{transcript_text}
"""

        request_body = {

            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],

            "inferenceConfig": {
                "maxTokens": 1200,
                "temperature": 0.5
            }
        }

        nova_response = bedrock.invoke_model(
            modelId=NOVA_MODEL_ID,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(
            nova_response["body"].read()
        )

        resume_text = response_body["output"]["message"]["content"][0]["text"]

        print("Resume Generated")

        # =========================================================
        # BULLET POINTS
        # =========================================================
        bullet_points = """
Professional resume generated
AI analyzed video content
Skills extracted successfully
Resume highlights created
Processing completed
"""

        # =========================================================
        # CREATE HTML
        # =========================================================
        resume_html_path = "/tmp/resume.html"

        bullets_html_path = "/tmp/bullets.html"

        create_html_resume(
            resume_text,
            resume_html_path
        )

        create_bullet_html(
            bullet_points,
            bullets_html_path
        )

        # =========================================================
        # UPLOAD HTML
        # =========================================================
        resume_key = f"resumes/{file_name}.html"

        s3.upload_file(
            resume_html_path,
            bucket,
            resume_key,
            ExtraArgs={
                "ContentType": "text/html",
                "ACL": "public-read"
            }
        )

        bullet_key = f"clips/{file_name}_bullets.html"

        s3.upload_file(
            bullets_html_path,
            bucket,
            bullet_key,
            ExtraArgs={
                "ContentType": "text/html",
                "ACL": "public-read"
            }
        )

        resume_url = f"https://{bucket}.s3.amazonaws.com/{resume_key}"

        bullet_url = f"https://{bucket}.s3.amazonaws.com/{bullet_key}"

        # =========================================================
        # CREATE CLIP
        # =========================================================
        clip_url = create_highlight_clip(
            bucket,
            key
        )

        # =========================================================
        # SAVE RESULT JSON
        # =========================================================
        result_data = {

            "status": "COMPLETED",

            "resume_html": resume_url,

            "bullet_points_html": bullet_url,

            "highlight_clip": clip_url,

            "bullet_points": bullet_points
        }

        result_path = "/tmp/result.json"

        with open(result_path, "w") as file:
            json.dump(result_data, file)

        result_key = f"results/{file_name}.json"

        s3.upload_file(
            result_path,
            bucket,
            result_key,
            ExtraArgs={
                "ContentType": "application/json",
                "ACL": "public-read"
            }
        )

        print("Result JSON Uploaded")

        return {
            "statusCode": 200,
            "body": "Completed"
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "statusCode": 500,
            "body": str(e)
        }

# =========================================================
# MAIN HANDLER
# =========================================================
def lambda_handler(event, context):

    print(json.dumps(event))

    try:

        # OPTIONS
        if event.get("requestContext") and \
           event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":

            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "message": "CORS OK"
                })
            }

        # API GATEWAY
        if "requestContext" in event:

            path = event.get("rawPath", "")

            print("API Path:", path)

            if "/upload" in path:

                return generate_upload_url()

            elif "/result" in path:

                return get_result(event)

            else:

                return {
                    "statusCode": 404,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({
                        "error": "Invalid Path"
                    })
                }

        # S3 EVENT
        elif "Records" in event:

            return process_uploaded_video(event)

        else:

            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "error": "Unknown Event"
                })
            }

    except Exception as e:

        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "error": str(e)
            })
        }