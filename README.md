# image-auto-tag
Automatically tag, describe and categorise images using the Microsoft(R) Azure(R) Computer Vision API.

##Usage
~~~~
usage: image-auto-tag.py [-h] --key [KEY]
                         [--captionConfidenceLevel CAPTIONCONFIDENCELEVEL]
                         [--tagConfidenceLevel TAGCONFIDENCELEVEL]
                         [--categoryConfidenceLevel CATEGORYCONFIDENCELEVEL]
                         [--azureResizeWidth AZURERESIZEWIDTH]
                         inputFiles [inputFiles ...]

Add XMP metadata based on Microsoft® Azure® Computer Vision API.

positional arguments:
  inputFiles            Input file list

optional arguments:
  -h, --help            show this help message and exit
  --key [KEY]           Azure Computer Vision API key (default: None)
  --captionConfidenceLevel CAPTIONCONFIDENCELEVEL
                        Confidence level for adding caption) (default: 0.1)
  --tagConfidenceLevel TAGCONFIDENCELEVEL
                        Confidence level for adding tags (default: 0.1)
  --categoryConfidenceLevel CATEGORYCONFIDENCELEVEL
                        Confidence level for adding category (default: 0.0)
  --azureResizeWidth AZURERESIZEWIDTH
                        Temporarily resize to <azureResizeWidth> before
                        uploading to Azure (default: 800)
~~~~

##Prerequisites
1. Azure Computer Vision API Key (proprietary, subscription-based):
https://www.microsoft.com/cognitive-services/en-us/computer-vision-api
2. Python 3
3. Libraries:
	* libxmp
	* argparse
	* PIL
	* Standard libraries:
		* json 
		* sys
		* http
		* urrlib
		* base64
		* io

##Features
* Saves bandwidth when upload to Azure by sending a smaller image
* Writes to standard XMP image metadata tags which can be read in programs such as Digikam, XNView
* Allows customised thresholds for when to tag automatically

