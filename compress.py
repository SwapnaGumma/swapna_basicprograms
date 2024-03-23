from fastapi import FastAPI, File, UploadFile, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from PIL import Image
import zipfile
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Function to compress an image with progress monitoring
def compress_image(input_image, output_image_path, quality=20):
    input_format = input_image.format
    input_image.save(output_image_path, format=input_format, optimize=True, quality=quality)

# Store uploaded images and their compressed versions
uploaded_images = []

# Function to get file size
def get_file_size(file_path):
    return os.path.getsize(file_path)

@app.get("/")
async def read_root(request: Request):
    # Clear the uploaded_images list when the root URL is accessed
    uploaded_images.clear()
    return templates.TemplateResponse("img_compress.html", {"request": request})

@app.post("/compress_image/")
async def compress_image_endpoint(image: UploadFile, output_quality: int = 20):
    try:
        if not image:
            return "No image file provided", 400

        # Open the image and convert it to RGB format
        input_image = Image.open(image.file)
        input_image = input_image.convert("RGB")

        # Track initial file size
        input_file_size = image.file.seek(0, os.SEEK_END)
        image.file.seek(0)

        # Create the "outputs" subdirectory if it doesn't exist
        outputs_directory = "static/outputs"
        os.makedirs(outputs_directory, exist_ok=True)

        # Compress image
        output_image_filename = f"{image.filename}_compressed.jpg"
        output_image_path = os.path.join(outputs_directory, output_image_filename)
        compress_image(input_image, output_image_path, quality=output_quality)

        # Track compressed file size
        output_file_size = get_file_size(output_image_path)

        # Append a tuple containing image path and original filename
        uploaded_images.append((output_image_path, image.filename))

        # return compression percentage and compressed image file size
        compression_percentage = (1 - (output_file_size / input_file_size)) * 100

        return {
            "message": "Image compressed successfully",
            "compression_percentage": f"{compression_percentage:.2f}%",
            "compressed_file_size": f"{output_file_size} bytes"
        }

    except Exception as e:
        return str(e), 500

@app.get("/download_image/")
async def download_image(index: int = Query(..., gt=-1)):
    if uploaded_images:
        image_path, original_filename = uploaded_images[index-1]
        return FileResponse(image_path, headers={"Content-Disposition": f"attachment; filename={original_filename}"})
    else:
        return "No compressed image available to download"

@app.get("/download-all-images/")
async def download_all_compressed_images():
    if not uploaded_images:
        return "No compressed images available to download"

    try:
        output_zip_path = "compressed_images.zip"
        with zipfile.ZipFile(output_zip_path, 'w') as zipf:
            for image_path, original_filename in uploaded_images:
                zipf.write(image_path, original_filename, compress_type=zipfile.ZIP_DEFLATED)

        return FileResponse(output_zip_path, media_type='application/zip', headers={"Content-Disposition": f"attachment; filename={output_zip_path}"})

    except Exception as e:
        return str(e), 500
  
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


