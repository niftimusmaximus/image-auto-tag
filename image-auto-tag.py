#!/usr/bin/python3

########### Python 3.2 #############
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

MAXIMUM_AZURE_RESIZE_WIDTH = 10000


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def check_width(value):    
    ivalue = int(value)
    if (ivalue < 0):
        raise argparse.ArgumentTypeError("%s is an invalid width - width must be greater than zero" % value)
    if (ivalue >= MAXIMUM_AZURE_RESIZE_WIDTH):
        raise argparse.ArgumentTypeError("%s is greater than the maximum Azure resize width (%d)" % (value,MAXIMUM_AZURE_RESIZE_WIDTH))
    return ivalue

parser = argparse.ArgumentParser(description='Add XMP metadata based on Azure Computer Vision')
parser.add_argument('--key', nargs='?',required=True, help='Azure Computer Vision API key')
parser.add_argument('--captionConfidenceLevel', help='Confidence level for adding caption',type=float, default=0.9)
parser.add_argument('--tagConfidenceLevel', help='Confidence level for adding tags',type=float, default=0.9)
parser.add_argument('--categoryConfidenceLevel', help='Confidence level for adding category',type=float, default=0.9)
parser.add_argument('--azureResizeWidth', required=False, help='Temporarily resize to <azureResizeWidth> before uploading to Azure (0 for original size)', type=check_width, default=0)
parser.add_argument('inputFiles', help='Input file list', type=argparse.FileType('rb'), nargs='+')
args = parser.parse_args()


p_tag_confidence_level=args.tagConfidenceLevel;
p_caption_confidence_level=args.captionConfidenceLevel;
p_category_confidence_level=args.categoryConfidenceLevel;
p_azure_resize_width=args.azureResizeWidth;
v_tags=[]

XMPMeta.register_namespace("http://www.digikam.org/ns/1.0/", "digiKam");

for v_input_file in args.inputFiles:   

    eprint("INFO: Reading input file %s" % v_input_file.name)

    try:       
        byteio = io.BytesIO()        
        img = Image.open(v_input_file.name)
        if p_azure_resize_width > 0 and img.size[0] > p_azure_resize_width:
            wpercent = (p_azure_resize_width / float(img.size[0]))
            hsize = int((float(img.size[1]) * float(wpercent)))
            img = img.resize((p_azure_resize_width, hsize), PIL.Image.ANTIALIAS)
        img.save(byteio, format="JPEG")
        byteio.seek(0)
        byte=byteio.read()
        img.close()
        byteio.close()
        eprint("INFO: Temporarily resized %s to %dx%d (%d bytes)" % (v_input_file.name, p_azure_resize_width, hsize, len(byte)))
    finally:
        v_input_file.close()




    headers = {
        # Request headers
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': args.key,
    }

    params = urllib.parse.urlencode({
        # Request parameters
        'visualFeatures': 'Categories,Tags,Description',
    })

    try:
        v_conn = http.client.HTTPSConnection('api.projectoxford.ai')
        v_conn.request("POST", "/vision/v1.0/analyze?%s" % params, byte, headers)
        eprint("INFO: Contacting Azure Computer Vision API...")
        v_response = v_conn.getresponse()
        v_response_data = v_response.read()
        eprint("INFO: ...got response back from Azure Computer Vision API (length: %d bytes)" % len(v_response_data))
        v_conn.close()
    except Exception as e:
        eprint("ERROR: [Errno {0}] {1}".format(e.errno, e.strerror))

    v_json_result=json.loads(v_response_data.decode("utf-8"))
    sys.stdout.flush()

    xmpfile = XMPFiles( file_path=v_input_file.name, open_forupdate=True )
    xmp = xmpfile.get_xmp()
       
    if v_json_result['description']['captions'][0]['confidence'] >= p_caption_confidence_level:
        xmp.delete_property(consts.XMP_NS_DC, u'description')
        xmp.set_property(consts.XMP_NS_DC, u'description', v_json_result['description']['captions'][0]['text'] )
        eprint("INFO: Appending caption '%s'" % v_json_result['description']['captions'][0]['text'])
    
    if v_json_result['categories'][0]['score'] >= p_category_confidence_level:
        xmp.delete_property('http://www.digikam.org/ns/1.0/', u'TagsList')   
        xmp.set_property('http://www.digikam.org/ns/1.0/', u'TagsList', v_json_result['categories'][0]['name'])
        
        xmp.delete_property(consts.XMP_NS_Photoshop, u'SupplementalCategories')   
        xmp.set_property(consts.XMP_NS_Photoshop, u'SupplementalCategories', v_json_result['categories'][0]['name'])
        
    for v_tag in v_json_result['tags']:
        if (v_tag['confidence']>=p_tag_confidence_level):
            print(p_tag_confidence_level)
            eprint("INFO: Appending tag '%s' (confidence: %f)" % (v_tag['name'],v_tag['confidence']))
            if not xmp.does_array_item_exist(consts.XMP_NS_DC, u'subject', v_tag['name']):
                xmp.append_array_item(consts.XMP_NS_DC, u'subject', v_tag['name'], {'prop_array_is_ordered': True, 'prop_value_is_array': True} )
    
    v_tags=[]
    
    if xmpfile.can_put_xmp(xmp):
        eprint("INFO: Writing XMP data to file %s" % v_input_file.name)
        xmpfile.put_xmp(xmp)
    xmpfile.close_file()


####################################


