# TextractProcessing

## Overview

This project is to extract the necessary information from the scanned pdf using AWS Textract 
and image processing with OpenCV & PyMyPDf library. 

## Structure

- app

    The main execution file on local environment
    
- requirements

    All the dependencies for this project
    
- settings

    Several settings for some constants

    
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
    
