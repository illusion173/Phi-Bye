import json
import boto3
import os
from pathlib import Path
s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")
dynamodb_resource = boto3.resource("dynamodb")
table = dynamodb_resource.Table('file_table')
dynamodb_client = boto3.client("dynamodb")
from boto3.dynamodb.conditions import Key

# Update DynamoDb for new mp3
def update_dynamodb(result_folder_uuid, filename):
    try: 
        print("AATTEMPT!")
        response = dynamodb_client.put_item(
                TableName = "file_table",
                Item = {
                    'UUID' : {
                        'S' : result_folder_uuid[0],
                        },
                    'original_filename' : {
                        'S' : result_folder_uuid[1] 
                        },
                    'filetype' : {
                        'S' : ".mp3"
                        },
                    'redacted' : {
                        'BOOL' : True
                        },
                    's3_key' : {
                        'S' : 'redacted-' + filename
                        }
                    }
                )
        print("DONE!")
    except Exception as e:
        print(e)
        return {
            'statusCode' : 500
            }

def get_uuid(filename):
    print("GOT TO DYNAMODB!")
    uuid = ""
    response = table.query(
        IndexName='s3_key-index',
        KeyConditionExpression=Key('s3_key').eq(filename)
    )
    uuid = response["Items"][0]["UUID"]
    original_filename = response["Items"][0]["original_filename"]
    return [uuid, original_filename]

def remove_audio(entity_time_stamps, file):
    command_str_p1 = "/opt/bin/ffmpeg -i "
    redact_times = ""
    for time_stamps in entity_time_stamps:
        s = 'volume=enable=\'between(t,' + str(time_stamps[0]) + ',' + str(time_stamps[1]) + ')\':volume=0' + ", "
        redact_times += s
    
    redact_times = "\"" + redact_times[:-2] + "\""
    try:
        os.system(command_str_p1 + "/tmp/" + file + " -af " + redact_times + " /tmp/redacted-" + file)
    
    except Exception as e:
        print(e)
    filename, file_extension = os.path.splitext(file)
    print(filename)
    try:
        print("UPLOADING")
        # Find appropriate folder
        uuid_result_folder = get_uuid(filename)
        print("FINAL RESULT")
        print(uuid_result_folder)
        
        #move to appropriate result bucket & Folder
        response = s3_client.upload_file("/tmp/redacted-" + file, "result-bucket-illusjw", uuid_result_folder[0] + "/" +  'redacted-' + file)
        # update dynamoodb
        update_dynamodb(uuid_result_folder, filename)
        
    except Exception as e:
        print(e)

def parse_url(url: str) -> list:
    scheme_end = url.find("://")
    netloc_start = scheme_end + 3
    netloc_end = url.find("/",netloc_start)
    path_start = netloc_end
    path_end = url.rfind("/") + 1
    path = url[path_start:path_end]
    path = path[1:]
    filename = url[path_end:]
    
    return ([path, filename])

def lambda_handler(event, context):
    
    # First get bucket / key of mp3
    mediaurl = event["Media"]["MediaFileUri"]
    media_url_data = parse_url(mediaurl)
    media_url_data[0] = "in-audio-phi"
    print(media_url_data[1])

    # Second get bucket / key of transcript
    transcripturl = event["Transcript"]["TranscriptFileUri"]
    transcript_url_data = parse_url(transcripturl)
    split_items = transcript_url_data[0].split('/')
    transcript_url_data = [split_items[0], split_items[1] + '/' + transcript_url_data[1]]

    try:
        print("Getting Audio")

        s3_resource.Bucket(media_url_data[0]).download_file(media_url_data[1], '/tmp/' + media_url_data[1])

    except Exception as e:
        print(e)

    #Get the json document
    transcript_file = ""
    try:
        print("Getting Transcript")
        
        transcript_file = s3_resource.Object(transcript_url_data[0], transcript_url_data[1]).get()['Body'].read().decode('utf-8')
        

    except Exception as e:
        print(e)
        
    transcript_json = json.loads(transcript_file)
        
    transcript_results = transcript_json["results"]
    transcript_string = transcript_results["transcripts"][0]["transcript"]
    transcript_entities = transcript_results["entities"]
        
    entity_time_stamps = []
        
    for entity in transcript_entities:
        entity_time_stamps.append([entity["start_time"], entity["end_time"]])
        
    remove_audio(entity_time_stamps, media_url_data[1])
    
    # Delete from worker bucket?



    # need to send transscript data here in return result
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }






