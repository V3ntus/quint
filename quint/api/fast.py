from cgitb import text
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Response
from pydantic import BaseModel
import datetime
import re
from pydub import AudioSegment
from quint.transcribtion import google_api as tga
from quint.transcribtion import highlights
from quint.chunk.get_topics import get_topics
from quint.chunk.timestamp import get_timestamp
from quint.chunk.chunking import get_middle_points

from quint.transcribtion.highlights import create_embedding,create_df

import os
output_filepath = os.getenv('OUTPUP_PATH')

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def root():
    return {'greeting': 'Hello'}


@app.post("/transcript")
def upload(file: UploadFile = File(...)):
    audio_file_name= file.filename
    if audio_file_name not in os.listdir("."):
        print('We got a new file')
        try:
            contents = file.file.read()
            with open(file.filename, 'wb') as f:
                # Get audio file name
                audio_file_name = audio_file_name.split('.')[0] + '.wav'
                # if audio_file_name not in os.listdir("."):
                # Save audio file locally
                f.write(contents)
                f.close()
            # # Get audio file transcribtion
            transcript = tga.google_transcribe(audio_file_name)

            # Get colored highlights
            transcript = highlights.get_colored_transcript(transcript)
            # Create name for transcript
            transcript_filename = audio_file_name.split('.')[0] + '.txt'
            # Save transript file locally
            tga.write_transcripts(transcript_filename ,transcript)

            # Return transcript to the api query
            return  {'transcript' : transcript}


        except Exception as error:
            return {"message": error}

        finally:
            file.file.close()

    with open(output_filepath+file.filename.split('.')[0] + '.txt') as f:
        # Get audio file name
        transcript = f.readlines()

        f.close()

    return {'transcript':transcript}





class Body(BaseModel):
    text: str


@app.post("/chunk")
def chunking_text(body: Body):
    input_text = body.text

    #Clean version without most importan words and sentences
    sentences,embeddings = create_embedding(input_text , version=2)
    df = create_df(sentences,embeddings)
    true_middle_points=get_middle_points(df,embeddings)
    #Initiate text
    text=''
    for num, each in enumerate(df['sentence']):
        # Chunk the text
        if num in true_middle_points:
            text+=f' \n \n {each}. '
        else:
            text+=f'{each}. '
    clean_chunks = text.split('\n \n')
    return {'for_summary':clean_chunks}


@app.post("/best")
def highligh_words(body: Body):
    input_text = body.text
    transcript = highlights.get_colored_transcript(input_text)
    return {'edited':transcript}


# @app.post("/topics")
# def get_bert_topics(body: Body):
#     input_text = body.text
#     try:
#         topics = get_topics(input_text)
#     except Exception as e:
#         print(e)
#         topics = 'Text is too short.'
#     return {'edited':topics}
