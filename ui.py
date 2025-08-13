import qrcode

# Example list of student access codes
access_codes = ["zaki2446", "john123", "mary789"]

for code in access_codes:
    # URL points to your Streamlit app with access_code param
    url = f"http://localhost:8501/?access_code={code}"  # replace localhost with deployed URL
    img = qrcode.make(url)
    img.save(f"qr_{code}.png")
    print(f"QR code saved: qr_{code}.png → {url}")
