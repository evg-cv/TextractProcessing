# TextractProcessing

## Overview

This project is to extract the necessary information from the scanned information using AWS Textract and image processing
with OpenCV & PyMyPDf library. 
This is deployed on AWS Lambda.

## Structure

- app

    The main execution file on local environment

- config

    The configuration file for AWS Access Key
    
- helper

    The source code for extraction of the necessary information
    
- lambda_function

    The main execution file on AWS Lambda
    
- modifier

    The source code to supplement the result

- requirements

    All the dependencies for this project
    
- settings

    Several settings for some constants

- trp

    The source code for tool
    
## Installation

- Environment

    Ubuntu 18.04, Python 3.6
    
- Installation

    Please go ahead to this project directory and run the following command in the terminal.
    ```
        pip3 install -r requirements.txt
    ```

## Execution

- Please set AWS Access keys in config.cfg file and DOCUMENT_NAME in settings file with the pdf file name of s3 bucket.

- Please run the following command in the terminal.

    ```
        python3 app.py
    ```
    