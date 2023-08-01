# Cloudformation Instructions Phi-Bye Backend

1. Run layer.yml - This will create a lambda layer which you must attach to the RemoveAudioPhiFunction.

2. Run final.yml - This is the complete backend for Phi-Bye.

3. Simply upload audio/text files to the landingphi S3 bucket and output will be in the resultphi bucket in respective folders which can be cross referenced via the file_table dynamodb table.

## NOTE
If the layer.yml is not working, check the serverless repo for the ffmpeg layer [here](https://serverlessrepo.aws.amazon.com/applications/us-east-1/145266761615/ffmpeg-lambda-layer). You will have to create the ffmpeg layer from the repo, download it, change the template so it allows python 3.11 & 3.10. Reupload and manually attach the layer to the RemoveAudioPhiFunction.


## Contact
Email: illusjw@amazon.com