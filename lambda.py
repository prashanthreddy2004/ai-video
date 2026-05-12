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

rekognition = boto3.client(
    "rekognition",
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
                box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
            }}

            h1 {{
                color: #2c3e50;
            }}

            p {{
                line-height: 1.8;
                color: #333;
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

        <title>Resume Highlights</title>

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
                margin-bottom: 50px;
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
# REKOGNITION ANALYSIS
# =========================================================

def analyze_confidence(bucket, key):

    try:

        print("Starting Rekognition")

        response = rekognition.start_face_detection(
            Video={
                "S3Object": {
                    "Bucket": bucket,
                    "Name": key
                }
            },
            FaceAttributes="ALL"
        )

        job_id = response["JobId"]

        while True:

            result = rekognition.get_face_detection(
                JobId=job_id
            )

            status = result["JobStatus"]

            print("Rekognition Status:", status)

            if status == "SUCCEEDED":
                break

            if status == "FAILED":

                return {
                    "confidence_score": 50,
                    "communication_score": 50,
                    "emotion": "UNKNOWN"
                }

            time.sleep(10)

        emotions = []

        confidence_scores = []

        for item in result["Faces"]:

            face = item.get("Face", {})

            confidence_scores.append(
                face.get("Confidence", 0)
            )

            for emotion in face.get("Emotions", []):

                if emotion["Type"] in [
                    "HAPPY",
                    "CALM",
                    "SURPRISED"
                ]:

                    emotions.append(
                        emotion["Confidence"]
                    )

        confidence_score = int(
            sum(confidence_scores) / len(confidence_scores)
        ) if confidence_scores else 50

        communication_score = int(
            sum(emotions) / len(emotions)
        ) if emotions else 50

        return {
            "confidence_score": confidence_score,
            "communication_score": communication_score,
            "emotion": "POSITIVE"
        }

    except Exception as e:

        print("Rekognition Error")
        print(str(e))

        traceback.print_exc()

        return {
            "confidence_score": 50,
            "communication_score": 50,
            "emotion": "UNKNOWN"
        }

# =========================================================
# DYNAMIC HIGHLIGHT
# =========================================================

def detect_highlight_timestamps(transcript_text):

    try:

        important_words = [
            "project",
            "experience",
            "skills",
            "education",
            "developer",
            "engineer"
        ]

        score = 0

        text = transcript_text.lower()

        for word in important_words:

            if word in text:
                score += 1

        if score >= 3:

            return {
                "start": "00:00:00:00",
                "end": "00:00:45:00"
            }

        return {
            "start": "00:00:00:00",
            "end": "00:00:30:00"
        }

    except:

        return {
            "start": "00:00:00:00",
            "end": "00:00:30:00"
        }

# =========================================================
# CREATE HIGHLIGHT CLIP
# =========================================================

def create_highlight_clip(bucket, input_key, start_time, end_time):

    try:

        print("Starting MediaConvert")

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

        print("Highlight:", start_time, end_time)

        job_settings = {

            "Inputs": [
                {
                    "FileInput": f"s3://{bucket}/{input_key}",

                    "TimecodeSource": "ZEROBASED",

                    "InputClippings": [
                        {
                            "StartTimecode": start_time,
                            "EndTimecode": end_time
                        }
                    ],

                    "AudioSelectors": {
                        "Audio Selector 1": {
                            "DefaultSelection": "DEFAULT"
                        }
                    }
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

                                "Width": 1280,
                                "Height": 720,

                                "CodecSettings": {

                                    "Codec": "H_264",

                                    "H264Settings": {

                                        "RateControlMode": "QVBR",

                                        "MaxBitrate": 5000000,

                                        "QvbrSettings": {
                                            "QvbrQualityLevel": 7
                                        },

                                        "SceneChangeDetect": "TRANSITION_DETECTION",

                                        "QualityTuningLevel": "SINGLE_PASS"
                                    }
                                }
                            },

                            "AudioDescriptions": [
                                {
                                    "CodecSettings": {

                                        "Codec": "AAC",

                                        "AacSettings": {

                                            "Bitrate": 96000,

                                            "CodingMode": "CODING_MODE_2_0",

                                            "SampleRate": 48000
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        response = mc_client.create_job(
            Role=os.environ["MEDIACONVERT_ROLE"],
            Settings=job_settings
        )

        print("MediaConvert Job Submitted")

        print(response)

        clip_url = (
            f"https://{bucket}.s3.amazonaws.com/"
            f"clips/{file_name}_highlight.mp4"
        )

        return clip_url

    except Exception as e:

        print("MediaConvert Error")
        print(str(e))

        traceback.print_exc()

        return ""

# =========================================================
# PROCESS VIDEO
# =========================================================

def process_uploaded_video(event):

    try:

        print("S3 EVENT RECEIVED")

        bucket = event["Records"][0]["s3"]["bucket"]["name"]

        key = urllib.parse.unquote_plus(
            event["Records"][0]["s3"]["object"]["key"]
        )

        print("Uploaded File:", key)

        if (
            key.startswith("clips/")
            or key.startswith("results/")
            or key.startswith("resumes/")
        ):

            return {
                "statusCode": 200,
                "body": "Skipped"
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
        # TRANSCRIBE
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

        attempts = 0

        while attempts < 60:

            status = transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )

            job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]

            print("Current Status:", job_status)

            if job_status == "COMPLETED":
                break

            if job_status == "FAILED":

                return {
                    "statusCode": 500,
                    "body": "Transcription Failed"
                }

            attempts += 1

            time.sleep(10)

        transcript_url = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]

        response = urllib.request.urlopen(transcript_url)

        transcript_json = json.loads(response.read())

        transcript_text = transcript_json[
            "results"
        ]["transcripts"][0]["transcript"]

        print("Transcript Extracted")

        # =========================================================
        # REKOGNITION
        # =========================================================

        analysis = analyze_confidence(
            bucket,
            key
        )

        confidence_score = analysis["confidence_score"]

        communication_score = analysis["communication_score"]

        emotion = analysis["emotion"]

        print("Confidence Analysis Done")

        # =========================================================
        # RESUME GENERATION
        # =========================================================

        resume_prompt = f"""
Create a professional ATS-friendly resume.

Include:
1. Summary
2. Skills
3. Experience
4. Education
5. Projects
6. Certifications

Transcript:

{transcript_text}
"""

        request_body = {

            "messages": [
                {
                    "role": "user",

                    "content": [
                        {
                            "text": resume_prompt
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

        resume_text = response_body[
            "output"
        ]["message"]["content"][0]["text"]

        print("Resume Generated")

        # =========================================================
        # BULLET POINTS
        # =========================================================

        bullet_prompt = f"""
Convert resume into 5 short bullet points.

Rules:
- One line each
- Max 10 words
- No numbering

Resume:

{resume_text}
"""

        bullet_request = {

            "messages": [
                {
                    "role": "user",

                    "content": [
                        {
                            "text": bullet_prompt
                        }
                    ]
                }
            ],

            "inferenceConfig": {
                "maxTokens": 200,
                "temperature": 0.3
            }
        }

        bullet_response = bedrock.invoke_model(
            modelId=NOVA_MODEL_ID,
            body=json.dumps(bullet_request),
            contentType="application/json",
            accept="application/json"
        )

        bullet_body = json.loads(
            bullet_response["body"].read()
        )

        bullet_points = bullet_body[
            "output"
        ]["message"]["content"][0]["text"]

        print("Bullet Points Generated")

        # =========================================================
        # HIGHLIGHT DETECTION
        # =========================================================

        highlight = detect_highlight_timestamps(
            transcript_text
        )

        start_time = highlight["start"]

        end_time = highlight["end"]

        # =========================================================
        # CREATE HTML FILES
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

        bullet_key = f"clips/{file_name}_bullets.html"

        s3.upload_file(
            resume_html_path,
            bucket,
            resume_key,
            ExtraArgs={
                "ContentType": "text/html"
            }
        )

        s3.upload_file(
            bullets_html_path,
            bucket,
            bullet_key,
            ExtraArgs={
                "ContentType": "text/html"
            }
        )

        resume_url = (
            f"https://{bucket}.s3.amazonaws.com/{resume_key}"
        )

        bullet_url = (
            f"https://{bucket}.s3.amazonaws.com/{bullet_key}"
        )

        print("HTML Uploaded")

        # =========================================================
        # CREATE VIDEO CLIP
        # =========================================================

        clip_url = create_highlight_clip(
            bucket,
            key,
            start_time,
            end_time
        )

        # =========================================================
        # SAVE RESULT JSON
        # =========================================================

        result_data = {

            "status": "COMPLETED",

            "uploaded_video": key,

            "resume_html": resume_url,

            "bullet_points_html": bullet_url,

            "highlight_clip": clip_url,

            "bullet_points": bullet_points,

            "confidence_score": confidence_score,

            "communication_score": communication_score,

            "emotion": emotion
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
                "ContentType": "application/json"
            }
        )

        print("Result JSON Uploaded")

        # =========================================================
        # DELETE TRANSCRIBE JOB
        # =========================================================

        try:

            transcribe.delete_transcription_job(
                TranscriptionJobName=job_name
            )

        except:
            pass

        return {
            "statusCode": 200,
            "body": "Processing Completed"
        }

    except Exception as e:

        print("ERROR OCCURRED")
        print(str(e))

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

        # =========================================================
        # OPTIONS REQUEST
        # =========================================================

        if event.get("requestContext") and \
           event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":

            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "message": "CORS OK"
                })
            }

        # =========================================================
        # API GATEWAY REQUEST
        # =========================================================

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

        # =========================================================
        # S3 EVENT
        # =========================================================

        elif "Records" in event:

            return process_uploaded_video(event)

        # =========================================================
        # UNKNOWN EVENT
        # =========================================================

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