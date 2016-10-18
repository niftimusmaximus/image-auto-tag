#!/usr/bin/python3

########### Python 3.2 #############
from libxmp import XMPFiles,XMPMeta, consts
import argparse
import json
import sys
import http.client, urllib.request, urllib.parse, urllib.error, base64
import PIL
from PIL import Image
import io

parser = argparse.ArgumentParser(description='Add XMP metadata based on Azure Computer Vision')
parser.add_argument('--key', nargs='?',required=True, help='Azure Computer Vision API key')
parser.add_argument('--tagConfidenceLevel', help='Confidence level for adding tags',type=float, default=0.9)
parser.add_argument('--descriptionConfidenceLevel', help='Confidence level for adding description',type=float, default=0.9)
parser.add_argument('--categoryConfidenceLevel', help='Confidence level for adding category',type=float, default=0.9)
parser.add_argument('--azureResizeWidth', required=False, help='Temporarily resize to <azureResizeWidth> before uploading to Azure', type=int, default=800)
parser.add_argument('inputFiles', help='Input file list', type=argparse.FileType('rb'), nargs='+')
args = parser.parse_args()


p_tag_confidence_level=args.tagConfidenceLevel;
p_description_confidence_level=args.descriptionConfidenceLevel;
p_category_confidence_level=args.categoryConfidenceLevel;
p_azure_resize_width=args.azureResizeWidth;
print(args.inputFiles)

v_tags=[]

for v_input_file in args.inputFiles:   

    try:       
        byteio = io.BytesIO()        
        img = Image.open(v_input_file.name)
        wpercent = (p_azure_resize_width / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((p_azure_resize_width, hsize), PIL.Image.ANTIALIAS)
        img.save(byteio, format="JPEG")
        byteio.seek(0)
        byte=byteio.read()
        img.close()
        byteio.close()
        print(len(byte))
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
        conn = http.client.HTTPSConnection('api.projectoxford.ai')
        conn.request("POST", "/vision/v1.0/analyze?%s" % params, byte, headers)
        response = conn.getresponse()
        data = response.read()
        #print(data)   
        conn.close()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))

    v_json_result=json.loads(data.decode("utf-8"))
    print(v_json_result)
    sys.stdout.flush()

    xmpfile = XMPFiles( file_path=v_input_file.name, open_forupdate=True )
    xmp = xmpfile.get_xmp()
    
    XMPMeta.register_namespace("http://www.digikam.org/ns/1.0/", "digiKam");
    
    xmp.delete_property(consts.XMP_NS_DC, u'Subject')
    xmp.delete_property(consts.XMP_NS_DC, u'Description')
    xmp.delete_property('http://www.digikam.org/ns/1.0/', u'TagsList')
    
    xmp.set_property(consts.XMP_NS_DC, u'Description', v_json_result['description']['captions'][0]['text'] )
    xmp.set_property('http://www.digikam.org/ns/1.0/', u'TagsList', v_json_result['categories'][0]['name'])
    
    for v_tag in v_json_result['tags']:
        if (v_tag['confidence']>=p_tag_confidence_level):           
            xmp.append_array_item(consts.XMP_NS_DC, u'Subject', v_tag['name'], {'prop_array_is_ordered': True, 'prop_value_is_array': True} )
    v_tags=[]
    if xmpfile.can_put_xmp(xmp):
        xmpfile.put_xmp(xmp)
    xmpfile.close_file()


####################################


