import colorsys
from flask import Flask, request, render_template, send_file
import zlib, blackboxprotobuf, random, copy, io, base64

app = Flask(__name__)


def color_to_int(r, g, b, a=255, order='RGBA'):
    if order.upper() == 'RGBA':
        return (r << 24) | (g << 16) | (b << 8) | a
    elif order.upper() == 'ARGB':
        return (a << 24) | (r << 16) | (g << 8) | b

def random_color_int():
    return color_to_int(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        255
    )

def distinct_colors_int(n):
    """Generate n visually distinct colors encoded as 32-bit integers."""
    colors = []
    for i in range(n):
        hue = i / n  # evenly spaced hues around the color wheel
        r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)  # bright and saturated
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        colors.append(color_to_int(r, g, b))
    return colors

def green_to_red(i, x):
    """
    Returns (R,G,B) color from green→yellow→red for i in 1..x.
    """
    if x <= 1:
        return (0, 255, 0)

    # Normalize position into 0..1
    t = (i - 1) / (x - 1)

    # First half: green → yellow (add red)
    if t <= 0.5:
        r = int(510 * t)       # 0 → 255
        g = 255               # stays max
    # Second half: yellow → red (remove green)
    else:
        r = 255               # stays max
        g = int(510 * (1 - t)) # 255 → 0

    return color_to_int(r, g, 0)

@app.route("/")
def index():
    return render_template("index.html")

# AJAX endpoint to extract tabName & propName
@app.route("/upload_ajax", methods=["POST"])
def upload_ajax():
    uploaded = request.files["aptmpl"]
    raw = uploaded.read()

    print(raw)

    #ALL DECODED DATA
    decdata, typeof = blackboxprotobuf.decode_message(raw)
    
    # EXTRACT TEMPLATE PROPERTIES
    blob1 = decdata['4']['6']['3']

    #DECOMPRESS TEMPLATE PROPERTIES
    mes1 = zlib.decompress(blob1)

    # DECODE TEMPLATE PROPERTIES
    decItem, itemTypeOf = blackboxprotobuf.decode_message(mes1)

    first = decItem['1']
    #print(first)

    templateName = decdata['4']['4'].decode()  # existing template name in the file
    tabName  = first['3']['2']['1']['2']['2']['2']['2']['2']['2'].decode()
    propName = first['3']['2']['1']['2']['2']['2']['2']['3']['2'].decode()

    encoded = base64.b64encode(raw).decode()
    #encoded = raw

    return { 
    "tabName": tabName,
    "propName": propName,
    "templateName": templateName,
    "filedata": encoded
}

# AJAX endpoint to process & return aptmpl file
@app.route("/process_ajax", methods=["POST"])
def process_ajax():
    filedata  = base64.b64decode(request.form["filedata"])
    tabName   = request.form["tabName"].strip()
    propName  = request.form["propName"].strip()
    templateName = request.form["templateName"].strip()
    values = [v.strip() for v in request.form["values"].split(",") if v.strip()]

    decdata, typeof = blackboxprotobuf.decode_message(filedata)
    blob = decdata['4']['6']['3']
    mes = zlib.decompress(blob)
    decItem, itemType = blackboxprotobuf.decode_message(mes)

    decItem['1'] = []

    template = {
        '1': 4,
        '2': 1325369087,
        '3': {
            '1': 0,
            '2': {
                '1': {
                    '2': {
                        '1': 0,
                        '2': {
                            '1': 0,
                            '2': {
                                '2': {
                                    '1': 0,
                                    '2': { '2': b"" },
                                    '3': { '2': b"" },
                                    '4': { '1': 1, '3': 9 },
                                    '5': 6
                                }
                            }
                        },
                        '3': 1
                    }
                }
            }
        }
    }

    decdata['4']['4'] = templateName.encode('utf-8')
    template['3']['2']['1']['2']['2']['2']['2']['2']['2'] = tabName.encode()
    template['3']['2']['1']['2']['2']['2']['2']['3']['2'] = propName.encode()

    color_mode = request.form.get("colorMode", "random").lower()
    n_values = len(values)
    distinct_colors = distinct_colors_int(n_values) if color_mode == "distinct" else []
   

    for i in range(0, n_values):
        entry = copy.deepcopy(template)
        #entry['2'] = random_color_int()
            # assign color based on user selection
        if color_mode == "random":
            entry['2'] = random_color_int()
        elif color_mode == "distinct":
            entry['2'] = distinct_colors[i]
        elif color_mode == "green2red":
            entry['2'] = green_to_red(i+1, n_values)
        else:
            entry['2'] = random_color_int()  # fallback
        entry['3']['2']['1']['2']['2']['2']['2']['4']['3'] = int(values[i])
        decItem['1'].append(entry)

    compressed = zlib.compress(blackboxprotobuf.encode_message(decItem, itemType))
    decdata['4']['6']['3'] = compressed
    final = blackboxprotobuf.encode_message(decdata, typeof)

    out = io.BytesIO(final)
    out.seek(0)

    return send_file(
        out,
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name="Reencoded_AppearSet.aptmpl"
    )
"""
if __name__ == "__main__":
    print("Running on http://127.0.0.1:5000")
    app.run(debug=True)
"""
