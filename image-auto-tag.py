#!/usr/bin/python3

# Package imports
from __future__ import print_function
import sys
from libxmp import XMPFiles,XMPMeta, consts
import argparse
import json
import sys
import http.client, urllib.request, urllib.parse, urllib.error, base64
import PIL
from PIL import Image
import io

# Constants
MAXIMUM_AZURE_RESIZE_WIDTH = 10000
AZURE_COMPUTER_VISION_HOST="api.projectoxford.ai"
AZURE_COMPUTER_VISION_PATH="/vision/v1.0/analyze"

# Function to print debugging messages to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Function to check image width input
def check_width(value):    
    ivalue = int(value)
    if (ivalue < 0):
        raise argparse.ArgumentTypeError("%s is an invalid width - width must be greater than zero" % value)
    if (ivalue >= MAXIMUM_AZURE_RESIZE_WIDTH):
        raise argparse.ArgumentTypeError("%s is greater than the maximum Azure resize width (%d)" % (value,MAXIMUM_AZURE_RESIZE_WIDTH))
    return ivalue

# Function to check confidence level input
def check_confidence(value):    
    ivalue = float(value)
    if (ivalue < 0):
        raise argparse.ArgumentTypeError("%s is an invalid confidence score - must be greater than zero" % value)
    if (ivalue > 1.0):
        raise argparse.ArgumentTypeError("%s is an invalid confidence score - must be less than 1" % value)
    return ivalue

# Setup argument parser
parser = argparse.ArgumentParser(description='Add XMP metadata based on Microsoft® Azure® Computer Vision API.', epilog="Not affiliated with Microsoft® in any way.\nSee here to get an API key: https://www.microsoft.com/cognitive-services/en-us/computer-vision-api",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--key', nargs='?',required=True, help='Azure Computer Vision API key')
parser.add_argument('--captionConfidenceLevel', help='Confidence level for adding caption)',type=check_confidence, default=0.1)
parser.add_argument('--tagConfidenceLevel', help='Confidence level for adding tags',type=check_confidence, default=0.1)
parser.add_argument('--categoryConfidenceLevel', help='Confidence level for adding category',type=check_confidence, default=0.0)
parser.add_argument('--azureResizeWidth', required=False, help='Temporarily resize to <azureResizeWidth> before uploading to Azure', type=check_width, default=800)
parser.add_argument('inputFiles', help='Input file list', type=argparse.FileType('rb'), nargs='+')
args = parser.parse_args()

# Set variables based on input parameters
p_tag_confidence_level=args.tagConfidenceLevel;
p_caption_confidence_level=args.captionConfidenceLevel;
p_category_confidence_level=args.categoryConfidenceLevel;
p_azure_resize_width=args.azureResizeWidth;
v_tags=[]

# Process input files
for v_idx, v_input_file in enumerate(args.inputFiles):   

    eprint("INFO: [%s] Reading input file %d/%d" % (v_input_file.name, v_idx+1, len(args.inputFiles)))

    # Read the input file and resize in memory before uploading to Azure
    try:       
        byteio = io.BytesIO()        
        img = Image.open(v_input_file.name)
        if p_azure_resize_width > 0 and img.size[0] > p_azure_resize_width:
            wpercent = (p_azure_resize_width / float(img.size[0]))
            hsize = int((float(img.size[1]) * float(wpercent)))
            img = img.resize((p_azure_resize_width, hsize), PIL.Image.ANTIALIAS)
            eprint("INFO: [%s] Temporarily resized to %dx%d" % (v_input_file.name, p_azure_resize_width, hsize))
        img.save(byteio, format="JPEG")
        byteio.seek(0)
        byte=byteio.read()
        img.close()
        byteio.close()        
    finally:
        v_input_file.close()

    # Request headers
    headers = {
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': args.key,
    }

    # Request parameters
    params = urllib.parse.urlencode({        
        'visualFeatures': 'Categories,Tags,Description',
    })

    # Make request to Computer Vision API
    try:
        conn = http.client.HTTPSConnection(AZURE_COMPUTER_VISION_HOST)
        conn.request("POST", AZURE_COMPUTER_VISION_PATH+"?%s" % params, byte, headers)
        eprint("INFO: [%s] Uploading to Azure Computer Vision API (length: %d bytes)" % (v_input_file.name, len(byte)))
        response = conn.getresponse()
        response_data = response.read()
        eprint("INFO: [%s] Response received from Azure Computer Vision API (length: %d bytes)" % (v_input_file.name,len(response_data)))
        conn.close()
    except Exception as e:
        eprint("ERROR: [Errno {0}] {1}".format(e.errno, e.strerror))

    # Decode the JSON output
    v_json_result=json.loads(response_data.decode("utf-8"))

    # Get existing image XMP data
    xmpfile = XMPFiles( file_path=v_input_file.name, open_forupdate=True )
    xmp = xmpfile.get_xmp()
    
    # Set caption if response is above desired confidence level
    if v_json_result['description']['captions'][0]['confidence'] >= p_caption_confidence_level:
        xmp.delete_property(consts.XMP_NS_DC, u'description')
        xmp.set_property(consts.XMP_NS_DC, u'description', v_json_result['description']['captions'][0]['text'] )
        eprint("INFO: [%s] Appended caption '%s' (confidence: %.2f >= %.2f)" % (v_input_file.name,v_json_result['description']['captions'][0]['text'], v_json_result['description']['captions'][0]['confidence'],p_caption_confidence_level))
    
    # Set category if response is above desired confidence level
    for v_category in v_json_result['categories']:
        if v_category['score'] >= p_category_confidence_level:            
            if not xmp.does_array_item_exist(consts.XMP_NS_Photoshop, u'SupplementalCategories', v_category['name']):
                xmp.append_array_item(consts.XMP_NS_Photoshop, u'SupplementalCategories', v_category['name'],{'prop_array_is_ordered': True, 'prop_value_is_array': True})
                eprint("INFO: [%s] Appended category '%s' (confidence: %.2f >= %.2f)" % (v_input_file.name,v_category['name'], v_category['score'],p_category_confidence_level))
        
    # Add tags if response for a given is above desired confidence level
    for v_tag in v_json_result['tags']:
        if (v_tag['confidence']>=p_tag_confidence_level):
            eprint("INFO: [%s] Appending tag '%s' (confidence: %.2f >= %.2f)" % (v_input_file.name, v_tag['name'],v_tag['confidence'],p_tag_confidence_level))
            if not xmp.does_array_item_exist(consts.XMP_NS_DC, u'subject', v_tag['name']):
                xmp.append_array_item(consts.XMP_NS_DC, u'subject', v_tag['name'], {'prop_array_is_ordered': True, 'prop_value_is_array': True} )
    
    # Write XMP metadata to file
    if xmpfile.can_put_xmp(xmp):       
        xmpfile.put_xmp(xmp)
        eprint("INFO: [%s] Finished writing XMP data to file %d/%d" % (v_input_file.name,v_idx+1, len(args.inputFiles)))
    else:
        eprint("ERROR: [%s] Couldn't write XMP data to file" % v_input_file.name)
    xmpfile.close_file()

    # Clear tags
    v_tags=[]

