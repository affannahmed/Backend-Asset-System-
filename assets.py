from flask import Flask, request, jsonify
import os
import json
import re
from werkzeug.utils import secure_filename
from flask_cors import CORS
import shutil
import zipfile


app = Flask(__name__)
CORS(app)

# --- Configurable Paths ---
BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'Imagine-New')

JSON_FOLDER = os.path.join(BASE_PATH, "Json_Files")
STATIC_URL_PATH = "/static/Imagine-New"
UPLOAD_FOLDER = BASE_PATH



# --- Helper function to sanitize folder names ---
def sanitize_name(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip())



                ########  **** ( IMAGINE APP ) **** ########
# ----- Login Function -----
VALID_EMAIL = "admin@codeknitters.com"
VALID_PASSWORD = "codeknitters123"
@app.route('/login', methods=['POST'])
def login():
    try:
        if not request.is_json:
            return jsonify({'message': 'Request must be JSON'}), 400

        data = request.get_json()

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Email and password are required'}), 400

        if email == VALID_EMAIL and password == VALID_PASSWORD:
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'message': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


    ################# -----  FOR ADDING NEW CATEGORY  ------ ##################
@app.route('/add-category', methods=['POST'])
def add_category():
    main_category = request.form.get('main_category')
    sub_category = request.form.get('sub_category')  # optional

    if not main_category:
        return jsonify({"error": "main_category is required"}), 400

    main_category = sanitize_name(main_category)
    if sub_category:
        sub_category = sanitize_name(sub_category)

    image_keys = [key for key in request.files if key.startswith('image_')]
    if not image_keys:
        return jsonify({"error": "No image files provided."}), 400

    # --- Create folders ---
    image_folder = os.path.join(BASE_PATH, main_category, sub_category) if sub_category else os.path.join(BASE_PATH, main_category)
    os.makedirs(image_folder, exist_ok=True)

    json_folder = os.path.join(JSON_FOLDER, main_category)
    os.makedirs(json_folder, exist_ok=True)

    json_file_path = os.path.join(json_folder, f"{sub_category}.json") if sub_category else os.path.join(json_folder, f"{main_category}.json")

    # --- Load or initialize JSON ---
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as f:
            json_data = json.load(f)
    else:
        json_data = {}

    # --- Process all images ---
    index = 0
    for key in sorted(image_keys):  
        file = request.files[key]

        if not file.content_type.startswith("image/"):
            return jsonify({"error": f"File {key} is not a valid image type."}), 400

        ext_key = f'file_extension_{index}'
        user_ext = request.form.get(ext_key, '').lower().strip('.')
        if not user_ext:
            user_ext = 'jpg'  
        actual_ext = f'.{user_ext}'

        # --- Save file ---
        filename = f"{index}{actual_ext}"
        filepath = os.path.join(image_folder, secure_filename(filename))
        file.save(filepath)

        # --- Metadata ---
        prem_str = request.form.get(f'prem_{index}', 'false')
        prem = prem_str.lower() == 'true'
        objects = request.form.getlist(f'objects_{index}')

        entry = {
            "Name": str(index),
            "Prem": prem,
            "main_category": main_category,
            "objects": objects
        }
        if sub_category:
            entry["sub_category"] = sub_category

        json_data[f"Image{index}"] = entry
        index += 1

    with open(json_file_path, 'w') as f:
        json.dump(json_data, f, indent=4)

    return jsonify({"message": "Category and images added successfully."}), 200



        ################## --- GET Categories and Subcategories with Images and Metadata ( For Delete & Update Category Action ) ---#################
@app.route('/get-categories', methods=['GET'])
def get_categories():
    all_categories = []

    if not os.path.exists(BASE_PATH):
        return jsonify({"categories": []}), 200

    for main_cat in os.listdir(BASE_PATH):
        main_cat_path = os.path.join(BASE_PATH, main_cat)

        if not os.path.isdir(main_cat_path) or main_cat == "Json_Files":
            continue

        sub_cats = []
        found_sub = False

        for sub in os.listdir(main_cat_path):
            sub_path = os.path.join(main_cat_path, sub)
            if not os.path.isdir(sub_path):
                continue

            found_sub = True

            images = []
            for img_file in os.listdir(sub_path):
                if img_file.endswith('.jpg') or img_file.endswith('.png'):
                    image_url = f"{STATIC_URL_PATH}/{sanitize_name(main_cat)}/{sanitize_name(sub)}/{img_file}"
                    images.append({
                        "url": image_url,
                        "name": img_file
                    })

            json_path = os.path.join(JSON_FOLDER, main_cat, f"{sub}.json")
            json_data = {}
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as jf:
                        json_data = json.load(jf)
                except:
                    json_data = {}

            sub_cats.append({
                "name": sub,
                "images": images,
                "json": json_data
            })

        # Handle case where no subfolders (images directly under main_cat)
        if not found_sub:
            images = []
            for img_file in os.listdir(main_cat_path):
                if img_file.endswith('.jpg') or img_file.endswith('.png'):
                    image_url = f"{STATIC_URL_PATH}/{sanitize_name(main_cat)}/{img_file}"
                    images.append({
                        "url": image_url,
                        "name": img_file
                    })

            json_path = os.path.join(JSON_FOLDER, main_cat, f"{main_cat}.json")
            json_data = {}
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as jf:
                        json_data = json.load(jf)
                except:
                    json_data = {}

            sub_cats.append({
                "name": None,
                "images": images,
                "json": json_data
            })

        all_categories.append({
            "main_category": main_cat,
            "sub_categories": sub_cats
        })

    return jsonify({"categories": all_categories}), 200


#####################################################  UPDATE ANY SUB-CATEGORY ( ACTION ) ##########################################################
    # --- Update the metdata of existing images --- 
@app.route('/update-image-meta', methods=['POST'])
def update_image_meta():
    main_category = request.form.get('main_category')
    sub_category = request.form.get('sub_category')  # optional
    image_name = request.form.get('image_name')  # "2.jpg" or "2"

    if not main_category or not image_name:
        return jsonify({"error": "main_category and image_name are required"}), 400

    main_category = sanitize_name(main_category)
    if sub_category:
        sub_category = sanitize_name(sub_category)

    image_index = os.path.splitext(image_name)[0]  # "2.jpg" -> "2"

    image_folder = os.path.join(UPLOAD_FOLDER, main_category, sub_category) if sub_category else os.path.join(UPLOAD_FOLDER, main_category)
    json_file_path = os.path.join(JSON_FOLDER, main_category, f"{sub_category}.json" if sub_category else f"{main_category}.json")

    if not os.path.exists(json_file_path):
        return jsonify({"error": "Metadata JSON file not found."}), 404

    with open(json_file_path, 'r') as f:
        json_data = json.load(f)

    key = f"Image{image_index}"
    if key not in json_data:
        return jsonify({"error": f"Metadata for image {image_name} not found."}), 404

    prem_str = request.form.get('prem')
    if prem_str is not None:
        json_data[key]['Prem'] = prem_str.lower() == 'true'

    objects = request.form.getlist('objects')
    if objects:
        json_data[key]['objects'] = objects

    if sub_category:
        json_data[key]['sub_category'] = sub_category

    new_image = request.files.get('new_image')
    if new_image:
        new_ext = os.path.splitext(new_image.filename)[1]  # e.g., '.png'
        new_filename = f"{image_index}{new_ext}"
        new_image_path = os.path.join(image_folder, new_filename)

        old_ext = os.path.splitext(image_name)[1]
        old_filename = f"{image_index}{old_ext}"
        old_image_path = os.path.join(image_folder, old_filename)
        if os.path.exists(old_image_path):
            os.remove(old_image_path)

        new_image.save(new_image_path)

        json_data[key]['Name'] = image_index  

    with open(json_file_path, 'w') as f:
        json.dump(json_data, f, indent=4)

    return jsonify({"message": f"Metadata and image updated for Image{image_index}."}), 200

    # ---- Delete any exisiting image ----
@app.route('/delete-image', methods=['POST'])
def delete_image():
    main_category = request.form.get('main_category')
    sub_category = request.form.get('sub_category')  # optional
    image_name = request.form.get('image_name')      # e.g., "6.jpg" or "6"

    if not main_category or not image_name:
        return jsonify({"error": "main_category and image_name are required"}), 400

    main_category = sanitize_name(main_category)
    if sub_category:
        sub_category = sanitize_name(sub_category)

    try:
        image_index = int(os.path.splitext(image_name)[0])
    except ValueError:
        return jsonify({"error": "Invalid image_name format"}), 400

    image_dir = os.path.join(UPLOAD_FOLDER, main_category, sub_category if sub_category else "")
    json_file_path = os.path.join(
        JSON_FOLDER, main_category, f"{sub_category}.json" if sub_category else f"{main_category}.json"
    )

    if not os.path.exists(json_file_path) or not os.path.exists(image_dir):
        return jsonify({"error": "Image directory or JSON file not found."}), 404

    with open(json_file_path, 'r') as f:
        json_data = json.load(f)

    key_to_delete = f"Image{image_index}"
    if key_to_delete not in json_data:
        return jsonify({"error": f"No metadata found for image {image_name}"}), 404

    deleted = False
    deleted_ext = None
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        path = os.path.join(image_dir, f"{image_index}{ext}")
        if os.path.exists(path):
            os.remove(path)
            deleted = True
            deleted_ext = ext
            break

    if not deleted:
        return jsonify({"error": "Image file not found."}), 404

    del json_data[key_to_delete]

    image_files = []
    for file in os.listdir(image_dir):
        name, ext = os.path.splitext(file)
        if ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
            try:
                idx = int(name)
                image_files.append((idx, file))
            except ValueError:
                continue

    image_files.sort(key=lambda x: x[0])

    for idx, file in image_files:
        if idx > image_index:
            old_path = os.path.join(image_dir, file)
            new_index = idx - 1
            ext = os.path.splitext(file)[1]
            new_filename = f"{new_index}{ext}"
            new_path = os.path.join(image_dir, new_filename)

            os.rename(old_path, new_path)

            old_key = f"Image{idx}"
            new_key = f"Image{new_index}"

            if old_key in json_data:
                metadata = json_data.pop(old_key)
                metadata['Name'] = str(new_index)
                json_data[new_key] = metadata

    with open(json_file_path, 'w') as f:
        json.dump(json_data, f, indent=4)

    return jsonify({"message": f"Image {image_name} and its metadata deleted and shifted successfully."}), 200


    # ---------- Update Existing Sub Category ( Add more data into it ) ----------
@app.route('/update-subcategory', methods=['POST'])
def update_subcategory():
    old_main_category = sanitize_name(request.form.get('old_main_category'))
    old_sub_category = sanitize_name(request.form.get('old_sub_category'))
    new_sub_category = sanitize_name(request.form.get('new_sub_category')) or old_sub_category

    if not old_main_category or not old_sub_category:
        return jsonify({"error": "old_main_category and old_sub_category are required"}), 400

    old_img_folder = os.path.join(BASE_PATH, old_main_category, old_sub_category)
    new_img_folder = os.path.join(BASE_PATH, old_main_category, new_sub_category)

    old_json_path = os.path.join(JSON_FOLDER, old_main_category, f"{old_sub_category}.json")
    new_json_path = os.path.join(JSON_FOLDER, old_main_category, f"{new_sub_category}.json")

    if old_sub_category != new_sub_category:
        if os.path.exists(old_img_folder):
            shutil.move(old_img_folder, new_img_folder)
        if os.path.exists(old_json_path):
            shutil.move(old_json_path, new_json_path)

    os.makedirs(new_img_folder, exist_ok=True)
    os.makedirs(os.path.dirname(new_json_path), exist_ok=True)

    if os.path.exists(new_json_path):
        with open(new_json_path, 'r') as jf:
            json_data = json.load(jf)
    else:
        json_data = {}

    existing_keys = [int(k.replace("Image", "")) for k in json_data.keys() if k.startswith("Image")]
    next_index = max(existing_keys, default=-1) + 1

    upload_index = 0
    while f'image_{upload_index}' in request.files:
        file = request.files[f'image_{upload_index}']
        if not file.content_type.startswith("image/"):
            return jsonify({"error": f"File image_{upload_index} is not a valid image type."}), 400

        filename = f"{next_index}.jpg"
        filepath = os.path.join(new_img_folder, secure_filename(filename))
        file.save(filepath)

        prem_str = request.form.get(f'prem_{upload_index}', 'false')
        prem = prem_str.lower() == 'true'
        objects = request.form.getlist(f'objects_{upload_index}')  # accepts multiple values

        json_data[f"Image{next_index}"] = {
            "Name": str(next_index),
            "Prem": prem,
            "main_category": old_main_category,
            "sub_category": new_sub_category,
            "objects": objects
        }

        next_index += 1
        upload_index += 1

    with open(new_json_path, 'w') as jf:
        json.dump(json_data, jf, indent=4)

    return jsonify({"message": "Subcategory updated successfully."}), 200

##############################################  END OF UPDATE CATEGORIES ACTION #######################################################################################

    ################## ----- Delete any sub category ----- #################
@app.route('/delete-subcategory', methods=['DELETE'])
def delete_subcategory():
    data = request.get_json()
    main_category = sanitize_name(data.get('main_category'))
    sub_category = sanitize_name(data.get('sub_category'))

    if not main_category or not sub_category:
        return jsonify({"error": "main_category and sub_category are required"}), 400

    image_sub_path = os.path.join(BASE_PATH, main_category, sub_category)
    if os.path.exists(image_sub_path):
        shutil.rmtree(image_sub_path)

    json_file_path = os.path.join(JSON_FOLDER, main_category, f"{sub_category}.json")
    if os.path.exists(json_file_path):
        os.remove(json_file_path)

    main_image_folder = os.path.join(BASE_PATH, main_category)
    if os.path.exists(main_image_folder) and not os.listdir(main_image_folder):
        shutil.rmtree(main_image_folder)

    main_json_folder = os.path.join(JSON_FOLDER, main_category)
    if os.path.exists(main_json_folder) and not os.listdir(main_json_folder):
        shutil.rmtree(main_json_folder)

    return jsonify({"message": "Subcategory deleted successfully."}), 200


    ################## ----- View All Category  ----- #################                   
@app.route('/get-category-structure', methods=['GET'])
def get_category_structure():
    categories = []

    if not os.path.exists(BASE_PATH):
        return jsonify({"categories": []}), 200

    for main_cat in sorted(os.listdir(BASE_PATH)):
        main_cat_path = os.path.join(BASE_PATH, main_cat)

        if not os.path.isdir(main_cat_path) or main_cat == "Json_Files":
            continue

        has_sub_category = False

        # Handle subcategories
        for sub in sorted(os.listdir(main_cat_path)):
            sub_path = os.path.join(main_cat_path, sub)

            if not os.path.isdir(sub_path):
                continue

            has_sub_category = True

            image_files = sorted([
                f for f in os.listdir(sub_path)
                if f.lower().endswith(('.jpg', '.png'))
            ])

            images = [
                {
                    "name": img_file,
                    "url": f"{STATIC_URL_PATH}/{sanitize_name(main_cat)}/{sanitize_name(sub)}/{img_file}"
                }
                for img_file in image_files
            ]

            categories.append({
                "main_category": main_cat,
                "sub_category": sub,
                "images": images
            })

        # If no sub-categories exist, treat main category as flat
        if not has_sub_category:
            image_files = sorted([
                f for f in os.listdir(main_cat_path)
                if f.lower().endswith(('.jpg', '.png'))
            ])

            images = [
                {
                    "name": img_file,
                    "url": f"{STATIC_URL_PATH}/{sanitize_name(main_cat)}/{img_file}"
                }
                for img_file in image_files
            ]

            categories.append({
                "main_category": main_cat,
                "sub_category": None,
                "images": images
            })

    return jsonify({"categories": categories}), 200


        ########## ------------  Rearrange Images ----------- ##########
@app.route('/swap-images', methods=['POST'])
def swap_images():
    main_category = sanitize_name(request.form.get('main_category'))
    sub_category = sanitize_name(request.form.get('sub_category'))
    image1_name = request.form.get('image1_name')  # e.g. '0.jpg'
    image2_name = request.form.get('image2_name')  # e.g. '1.jpg'

    if not all([main_category, sub_category, image1_name, image2_name]):
        return jsonify({"error": "All fields are required"}), 400

    if image1_name == image2_name:
        return jsonify({"error": "Images must be different to swap"}), 400

    sub_folder = os.path.join(BASE_PATH, main_category, sub_category)
    json_path = os.path.join(JSON_FOLDER, main_category, f"{sub_category}.json")

    img1_path = os.path.join(sub_folder, image1_name)
    img2_path = os.path.join(sub_folder, image2_name)

    if not (os.path.exists(img1_path) and os.path.exists(img2_path)):
        return jsonify({"error": "One or both images do not exist"}), 404

    if not os.path.exists(json_path):
        return jsonify({"error": "Subcategory JSON file not found"}), 404

    with open(json_path, 'r') as jf:
        data = json.load(jf)
    index1 = os.path.splitext(image1_name)[0]  # '0'
    index2 = os.path.splitext(image2_name)[0]  # '1'

    key1 = f"Image{index1}"
    key2 = f"Image{index2}"

    if key1 not in data or key2 not in data:
        return jsonify({"error": "Image keys not found in JSON"}), 404

    data[key1], data[key2] = data[key2], data[key1]
    
    data[key1]["Name"] = index1
    data[key2]["Name"] = index2

    with open(json_path, 'w') as jf:
        json.dump(data, jf, indent=4)

    temp_path = os.path.join(sub_folder, "__temp_swap__.jpg")
    os.rename(img1_path, temp_path)
    os.rename(img2_path, img1_path)
    os.rename(temp_path, img2_path)

    return jsonify({"message": "Images swapped successfully."}), 200


                        ########  **** ( IBGC APP ) **** ########
import json
import os
from datetime import datetime

# === Paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CURRENT_DIR = os.path.join(STATIC_DIR, "Assets_IBGC")
BACKUP_DIR = os.path.join(STATIC_DIR, "Assets_IBGC_Last")
CURRENT_JSON_DIR = os.path.join(CURRENT_DIR, "Json_Files")
BACKUP_JSON_DIR = os.path.join(BACKUP_DIR, "Json_Files_Last")
VERSION_FILE = os.path.join(STATIC_DIR, "version_IBGC.json")

# CURRENT_DIR = os.path.join(STATIC_DIR, "Assets_IBGC")
# BACKUP_DIR = os.path.join(STATIC_DIR, "Assets_IBGC_Last")
# CURRENT_JSON_DIR = os.path.join(CURRENT_DIR, "Json_Files")
# BACKUP_JSON_DIR = os.path.join(BACKUP_DIR, "Json_Files_Last")
# VERSION_FILE = os.path.join(STATIC_DIR, "version_IBGC.json")

# === Utility: Get Short Name Prefix ===
def get_short_name(category_name):
    return ''.join([c for c in category_name if c.isalpha()])[:4].capitalize()

# === Get Full Version Info (with default fallback)
def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return json.load(f)
    return {
        "current_version": 0,
        "previous_version": 0,
        "current_version_date": None,
        "previous_version_date": None
    }

# === Increment Version on Successful Update
def increment_version():
    data = get_current_version()

    # Shift current to previous
    data["previous_version"] = data.get("current_version", 0)
    data["previous_version_date"] = data.get("current_version_date", None)

    # Update current version
    data["current_version"] = data.get("current_version", 0) + 1
    data["current_version_date"] = datetime.now().isoformat()

    with open(VERSION_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    return data

# === Add New Category IBGC ===
@app.route('/add-category_IBGC', methods=['POST'])
def add_category_IBGC():
    try:
        category_name = request.form.get('category_name')
        images = request.files.getlist('images')
        prem_list = request.form.getlist('prem')  # List of 'true'/'false' strings

        if not category_name or not images:
            return jsonify({"error": "Missing category_name or images"}), 400

        # === Step 1: Backup CURRENT_DIR -> BACKUP_DIR
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(CURRENT_DIR, BACKUP_DIR)

        # Also rename Json_Files to Json_Files_Last inside the backup
        if os.path.exists(os.path.join(BACKUP_DIR, "Json_Files")):
            os.rename(
                os.path.join(BACKUP_DIR, "Json_Files"),
                os.path.join(BACKUP_DIR, "Json_Files_Last")
            )

        # === Step 2: Prepare current structure
        category_path = os.path.join(CURRENT_DIR, category_name)
        os.makedirs(category_path, exist_ok=True)
        os.makedirs(CURRENT_JSON_DIR, exist_ok=True)

        # === Step 3: Save images and prepare JSON
        image_json_data = {}

        for idx, img in enumerate(images):
            filename = f"{idx}.webp"
            img_path = os.path.join(category_path, secure_filename(filename))
            img.save(img_path)

            prem_flag = False
            if idx < len(prem_list):
                prem_flag = prem_list[idx].lower() == 'true'

            image_json_data[f"Image{idx}"] = {
                "Name": str(idx),
                "Prem": prem_flag,
                "category": category_name
            }

        # === Step 4: Save category JSON
        category_json_file = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")
        with open(category_json_file, 'w') as jf:
            json.dump(image_json_data, jf, indent=4)

        # === Step 5: Update version
        version_info = increment_version()

        return jsonify({
            "message": f"Category '{category_name}' added successfully.",
            "new_version": version_info
        })

    except Exception as e:
        # === Rollback: delete current and restore backup
        try:
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)
            if os.path.exists(BACKUP_DIR):
                shutil.move(BACKUP_DIR, CURRENT_DIR)

            # Restore Json_Files_Last back to Json_Files
            backup_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
            if os.path.exists(backup_json_last):
                restored_path = os.path.join(CURRENT_DIR, "Json_Files")
                if os.path.exists(restored_path):
                    shutil.rmtree(restored_path)
                os.rename(backup_json_last, restored_path)

        except Exception as rollback_error:
            return jsonify({
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({
            "error": "Something went wrong.",
            "details": str(e)
        }), 500

# -------- View Categories from Folder --------
@app.route('/view-category_IBGC', methods=['GET'])
def view_category_IBGC():
    try:
        categories = []

        if not os.path.exists(CURRENT_DIR):
            return jsonify({"error": "Assets_IBGC directory not found."}), 404

        for category_name in sorted(os.listdir(CURRENT_DIR)):
            if category_name == "Json_Files":
                continue

            category_path = os.path.join(CURRENT_DIR, category_name)
            json_path = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")

            # Correctly parse JSON dictionary
            image_meta = {}
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        data = json.load(f)
                        for key, meta in data.items():
                            filename = meta.get("Name")
                            prem_value = meta.get("Prem", False)
                            if filename is not None:
                                image_meta[f"{filename}.jpg"] = prem_value  # Add other extensions as needed
                                image_meta[f"{filename}.jpeg"] = prem_value
                                image_meta[f"{filename}.png"] = prem_value
                                image_meta[f"{filename}.webp"] = prem_value
                    except Exception as e:
                        print(f"Failed to read JSON for {category_name}: {e}")

            if os.path.isdir(category_path):
                image_list = []
                for filename in sorted(os.listdir(category_path)):
                    if filename.lower().endswith(('.webp', '.jpg', '.jpeg', '.png')):
                        prem_value = image_meta.get(filename, False)
                        image_list.append({
                            "filename": filename,
                            "url": f"/static/Assets_IBGC/{category_name}/{filename}",
                            "prem": prem_value
                        })

                categories.append({
                    "category": category_name,
                    "images": image_list
                })

        return jsonify(categories)

    except Exception as e:
        return jsonify({
            "error": "Something went wrong while reading categories.",
            "details": str(e)
        }), 500

    

 # -------- For Deleting a Category --------
@app.route('/delete-category_IBGC', methods=['POST'])
def delete_category_IBGC():
    try:
        category_name = request.form.get('category_name')

        if not category_name:
            return jsonify({"error": "Missing category_name"}), 400

        # Step 1: Backup current version
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        
        if os.path.exists(CURRENT_DIR):
            # Rename Json_Files to Json_Files_Last inside CURRENT_DIR
            current_json_folder = os.path.join(CURRENT_DIR, "Json_Files")
            backup_json_folder = os.path.join(CURRENT_DIR, "Json_Files_Last")
            if os.path.exists(current_json_folder):
                if os.path.exists(backup_json_folder):
                    shutil.rmtree(backup_json_folder)
                os.rename(current_json_folder, backup_json_folder)

            # Rename Assets_IBGC to Assets_IBGC_Last
            os.rename(CURRENT_DIR, BACKUP_DIR)

        # Step 2: Work on fresh copy
        shutil.copytree(BACKUP_DIR, CURRENT_DIR)

        # Rename Json_Files_Last back to Json_Files inside CURRENT_DIR
        new_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
        new_json = os.path.join(CURRENT_DIR, "Json_Files")
        if os.path.exists(new_json_last):
            if os.path.exists(new_json):
                shutil.rmtree(new_json)
            os.rename(new_json_last, new_json)

        # Step 3: Delete category folder
        category_path = os.path.join(CURRENT_DIR, category_name)
        if os.path.exists(category_path) and os.path.isdir(category_path):
            shutil.rmtree(category_path)
        else:
            raise FileNotFoundError(f"Category '{category_name}' not found.")

        # Step 4: Delete JSON file (if exists)
        category_json_file = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")
        if os.path.exists(category_json_file):
            os.remove(category_json_file)

        # Step 5: Versioning
        version_info = increment_version()

        return jsonify({
            "message": f"Category '{category_name}' deleted successfully.",
            "new_version": version_info
        })

    except Exception as e:
        try:
            # Clean up current broken state
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)

            # Restore Assets_IBGC from backup
            if os.path.exists(BACKUP_DIR):
                os.rename(BACKUP_DIR, CURRENT_DIR)

                # Restore Json_Files_Last to Json_Files
                restored_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
                restored_json = os.path.join(CURRENT_DIR, "Json_Files")
                if os.path.exists(restored_json_last):
                    if os.path.exists(restored_json):
                        shutil.rmtree(restored_json)
                    os.rename(restored_json_last, restored_json)

        except Exception as rollback_error:
            return jsonify({
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({
            "error": "Something went wrong.",
            "details": str(e)
        }), 500


  #########################  ***  Update Existing Category  *** #########################

 # --- Add more Images to Existing Category ---
@app.route('/add-images-to-category', methods=['POST'])
def add_images_to_category():
    try:
        category_name = request.form.get('category_name')
        images = request.files.getlist('images')
        prem_list = request.form.getlist('prem')  # optional

        if not category_name or not images:
            return jsonify({"error": "Missing category_name or images"}), 400

        # === Step 1: Backup CURRENT_DIR -> BACKUP_DIR
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(CURRENT_DIR, BACKUP_DIR)

        # === Step 2: Rename Json_Files -> Json_Files_Last inside backup
        backup_json_path = os.path.join(BACKUP_DIR, "Json_Files")
        backup_json_last_path = os.path.join(BACKUP_DIR, "Json_Files_Last")
        if os.path.exists(backup_json_path):
            if os.path.exists(backup_json_last_path):
                shutil.rmtree(backup_json_last_path)
            os.rename(backup_json_path, backup_json_last_path)

        # Recreate Json_Files directory (now it's empty)
        os.makedirs(CURRENT_JSON_DIR, exist_ok=True)

        # === Step 3: Prepare category path
        category_path = os.path.join(CURRENT_DIR, category_name)
        if not os.path.exists(category_path):
            raise Exception(f"Category '{category_name}' does not exist.")

        category_json_path = os.path.join(backup_json_last_path, f"{category_name}.json")
        if not os.path.exists(category_json_path):
            raise Exception(f"JSON for category '{category_name}' not found.")

        # Load existing JSON from backup and start fresh in Json_Files
        with open(category_json_path, 'r') as jf:
            existing_data = json.load(jf)

        existing_image_keys = sorted(existing_data.keys(), key=lambda k: int(existing_data[k]['Name']))
        total_new = len(images)

        # Shift existing images
        for key in reversed(existing_image_keys):
            old_index = int(existing_data[key]["Name"])
            new_index = old_index + total_new
            old_file = os.path.join(category_path, f"{old_index}.webp")
            new_file = os.path.join(category_path, f"{new_index}.webp")
            if os.path.exists(old_file):
                os.rename(old_file, new_file)
            existing_data[key]["Name"] = str(new_index)

        # Save new images
        new_data = {}
        for idx, img in enumerate(images):
            filename = f"{idx}.webp"
            img_path = os.path.join(category_path, secure_filename(filename))
            img.save(img_path)

            prem_flag = False
            if idx < len(prem_list):
                prem_flag = prem_list[idx].lower() == 'true'

            new_data[f"Image{idx}"] = {
                "Name": str(idx),
                "Prem": prem_flag,
                "category": category_name
            }

        # Merge and reindex everything
        merged_data = list(new_data.values()) + list(existing_data.values())
        final_data = {}
        for i, item in enumerate(merged_data):
            old_index = int(item["Name"])
            if old_index != i:
                old_path = os.path.join(category_path, f"{old_index}.webp")
                new_path = os.path.join(category_path, f"{i}.webp")
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
            item["Name"] = str(i)
            final_data[f"Image{i}"] = item

        # Save updated JSON
        new_json_path = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")
        with open(new_json_path, 'w') as jf:
            json.dump(final_data, jf, indent=4)

        # === Step 4: Update version
        version_info = increment_version()

        return jsonify({
            "message": f"{len(images)} image(s) added to '{category_name}' at the beginning.",
            "new_version": version_info
        })

    except Exception as e:
        # Rollback
        try:
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)
            if os.path.exists(BACKUP_DIR):
                shutil.move(BACKUP_DIR, CURRENT_DIR)

            # Restore Json_Files_Last back to Json_Files
            backup_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
            if os.path.exists(backup_json_last):
                restored_path = os.path.join(CURRENT_DIR, "Json_Files")
                if os.path.exists(restored_path):
                    shutil.rmtree(restored_path)
                os.rename(backup_json_last, restored_path)

        except Exception as rollback_error:
            return jsonify({
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({
            "error": "Something went wrong.",
            "details": str(e)
        }), 500


# =======  * Rename the Existing Category Name * =======  
@app.route('/rename-category', methods=['POST'])
def rename_category():
    try:
        old_name = request.form.get('old_name')  # e.g., "blur"
        new_name = request.form.get('new_name')  # e.g., "Affan"

        if not old_name or not new_name:
            return jsonify({"success": False, "error": "Missing old_name or new_name"}), 400

        # Step 1: Backup current version using same folder strategy
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)

        if os.path.exists(CURRENT_DIR):
            # Rename Json_Files to Json_Files_Last inside CURRENT_DIR
            current_json_folder = os.path.join(CURRENT_DIR, "Json_Files")
            backup_json_folder = os.path.join(CURRENT_DIR, "Json_Files_Last")
            if os.path.exists(current_json_folder):
                if os.path.exists(backup_json_folder):
                    shutil.rmtree(backup_json_folder)
                os.rename(current_json_folder, backup_json_folder)

            # Rename Assets_IBGC to Assets_IBGC_Last
            os.rename(CURRENT_DIR, BACKUP_DIR)

        # Step 2: Work on fresh copy
        shutil.copytree(BACKUP_DIR, CURRENT_DIR)

        # Rename Json_Files_Last back to Json_Files
        new_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
        new_json = os.path.join(CURRENT_DIR, "Json_Files")
        if os.path.exists(new_json_last):
            if os.path.exists(new_json):
                shutil.rmtree(new_json)
            os.rename(new_json_last, new_json)

        # Step 3: Define paths
        old_category_path = os.path.join(CURRENT_DIR, old_name)
        new_category_path = os.path.join(CURRENT_DIR, new_name)

        old_json_path = os.path.join(CURRENT_JSON_DIR, f"{old_name}.json")
        new_json_path = os.path.join(CURRENT_JSON_DIR, f"{new_name}.json")

        # Step 4: Check existence
        if not os.path.exists(old_category_path):
            raise Exception(f"Category folder '{old_name}' does not exist.")

        if os.path.exists(new_category_path):
            raise Exception(f"Category folder '{new_name}' already exists.")

        if not os.path.exists(old_json_path):
            raise Exception(f"JSON file '{old_name}.json' does not exist.")

        # Step 5: Rename category folder and JSON file
        os.rename(old_category_path, new_category_path)
        os.rename(old_json_path, new_json_path)

        # Step 6: Update version
        version_data = increment_version()

        return jsonify({
            "success": True,
            "message": f"Category renamed from '{old_name}' to '{new_name}' successfully.",
            "version": version_data
        })

    except Exception as e:
        try:
            # Rollback
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)

            if os.path.exists(BACKUP_DIR):
                os.rename(BACKUP_DIR, CURRENT_DIR)

                # Restore Json_Files_Last to Json_Files
                restored_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
                restored_json = os.path.join(CURRENT_DIR, "Json_Files")
                if os.path.exists(restored_json_last):
                    if os.path.exists(restored_json):
                        shutil.rmtree(restored_json)
                    os.rename(restored_json_last, restored_json)

        except Exception as rollback_error:
            return jsonify({
                "success": False,
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({"success": False, "error": str(e)}), 500


# # -----  Replace the Existing Image ------
@app.route('/replace-category-image', methods=['POST'])
def replace_category_image():
    try:
        category_name = request.form.get('category_name')
        old_filename = request.form.get('old_filename')
        new_image = request.files.get('new_image')
        prem_flag_str = request.form.get('prem', 'false')
        prem_flag = prem_flag_str.lower() == 'true'

        if not category_name or not old_filename or not new_image:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        # === Step 1: Backup CURRENT_DIR -> BACKUP_DIR ===
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(CURRENT_DIR, BACKUP_DIR)

        # === Step 2: Rename Json_Files -> Json_Files_Last in backup ===
        backup_json_path = os.path.join(BACKUP_DIR, "Json_Files")
        backup_json_last_path = os.path.join(BACKUP_DIR, "Json_Files_Last")
        if os.path.exists(backup_json_path):
            if os.path.exists(backup_json_last_path):
                shutil.rmtree(backup_json_last_path)
            os.rename(backup_json_path, backup_json_last_path)

        # === Step 3: Prepare category path ===
        category_path = os.path.join(CURRENT_DIR, category_name)
        if not os.path.exists(category_path):
            raise Exception(f"Category '{category_name}' does not exist.")

        # === Step 4: Load JSON from backup ===
        category_json_path = os.path.join(backup_json_last_path, f"{category_name}.json")
        if not os.path.exists(category_json_path):
            raise Exception(f"JSON for category '{category_name}' not found.")

        with open(category_json_path, 'r') as jf:
            json_data = json.load(jf)

        # === Step 5: Replace image ===
        target_file_path = os.path.join(category_path, old_filename)
        if not os.path.exists(target_file_path):
            raise Exception(f"Image '{old_filename}' not found in category '{category_name}'.")

        new_image.save(target_file_path)

        # === Step 6: Update JSON ===
        image_index = os.path.splitext(old_filename)[0]
        image_key = None
        for key, val in json_data.items():
            if val["Name"] == image_index:
                image_key = key
                break

        if not image_key:
            raise Exception(f"JSON entry for image '{old_filename}' not found.")

        json_data[image_key]["Prem"] = prem_flag
        json_data[image_key]["category"] = category_name

        # === Step 7: Save new JSON ===
        os.makedirs(CURRENT_JSON_DIR, exist_ok=True)
        new_json_path = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")
        with open(new_json_path, 'w') as jf:
            json.dump(json_data, jf, indent=4)

        # === Step 8: Update version ===
        version_data = increment_version()

        return jsonify({
            "success": True,
            "message": f"Image '{old_filename}' replaced successfully in '{category_name}' with prem={prem_flag}.",
            "version": version_data
        })

    except Exception as e:
        # === Rollback ===
        try:
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)
            if os.path.exists(BACKUP_DIR):
                shutil.copytree(BACKUP_DIR, CURRENT_DIR)

            # Restore Json_Files_Last -> Json_Files
            backup_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
            restored_path = os.path.join(CURRENT_DIR, "Json_Files")
            if os.path.exists(backup_json_last):
                if os.path.exists(restored_path):
                    shutil.rmtree(restored_path)
                os.rename(backup_json_last, restored_path)

        except Exception as rollback_error:
            return jsonify({
                "success": False,
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



# =======  * Delete the Existing Image * =======  
import re

def extract_index(filename):
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else -1

@app.route('/delete-image-from-category', methods=['POST'])
def deleteImageFromCategory():
    try:
        category_name = request.form.get('category_name')
        filename = request.form.get('filename')

        if not category_name or not filename:
            return jsonify({"success": False, "error": "Missing category_name or filename"}), 400

        # === Step 1: Backup CURRENT_DIR -> BACKUP_DIR
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(CURRENT_DIR, BACKUP_DIR)

        # === Step 2: Rename Json_Files -> Json_Files_Last inside backup
        backup_json_path = os.path.join(BACKUP_DIR, "Json_Files")
        backup_json_last_path = os.path.join(BACKUP_DIR, "Json_Files_Last")
        if os.path.exists(backup_json_path):
            if os.path.exists(backup_json_last_path):
                shutil.rmtree(backup_json_last_path)
            os.rename(backup_json_path, backup_json_last_path)

        # === Step 3: Recreate Json_Files directory
        os.makedirs(CURRENT_JSON_DIR, exist_ok=True)

        # === Step 4: Validate paths
        category_path = os.path.join(CURRENT_DIR, category_name)
        if not os.path.exists(category_path):
            raise Exception(f"Category '{category_name}' not found.")

        deleted_index = extract_index(filename)
        file_path = os.path.join(category_path, filename)
        if not os.path.exists(file_path):
            raise Exception(f"Image '{filename}' not found in category '{category_name}'.")

        # === Step 5: Delete the image file
        os.remove(file_path)

        # === Step 6: Load category JSON from backup and remove deleted index
        category_json_path = os.path.join(backup_json_last_path, f"{category_name}.json")
        if not os.path.exists(category_json_path):
            raise Exception(f"JSON file for category '{category_name}' not found.")

        with open(category_json_path, 'r') as jf:
            json_data = json.load(jf)

        # Rebuild JSON and image filenames after deletion
        json_items = list(json_data.values())
        json_items.sort(key=lambda x: int(x['Name']))

        updated_json = {}
        new_index = 0
        for item in json_items:
            current_index = int(item["Name"])
            if current_index == deleted_index:
                continue  # Skip the deleted image

            old_img_path = os.path.join(category_path, f"{current_index}.webp")
            new_img_path = os.path.join(category_path, f"{new_index}.webp")

            if os.path.exists(old_img_path):
                os.rename(old_img_path, new_img_path)

            item["Name"] = str(new_index)
            updated_json[f"Image{new_index}"] = item
            new_index += 1

        # === Step 7: Save updated JSON to CURRENT_JSON_DIR
        new_json_path = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")
        with open(new_json_path, 'w') as jf:
            json.dump(updated_json, jf, indent=4)

        # === Step 8: Update version
        version_info = increment_version()

        return jsonify({
            "success": True,
            "message": f"Image '{filename}' deleted successfully, JSON and images reindexed.",
            "version": version_info
        })

    except Exception as e:
        # === Rollback
        try:
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)
            if os.path.exists(BACKUP_DIR):
                shutil.copytree(BACKUP_DIR, CURRENT_DIR)

            # Restore Json_Files_Last
            backup_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
            if os.path.exists(backup_json_last):
                restored_path = os.path.join(CURRENT_DIR, "Json_Files")
                if os.path.exists(restored_path):
                    shutil.rmtree(restored_path)
                os.rename(backup_json_last, restored_path)

        except Exception as rollback_error:
            return jsonify({
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

 # ======= *  Update Premium of Existing Images * ========
@app.route('/update-prem-flag', methods=['POST'])
def update_prem_flag():
    try:
        updates = request.get_json()
        if not isinstance(updates, list) or not updates:
            return jsonify({"error": "Invalid or empty update list."}), 400

        # Backup the entire CURRENT_DIR -> BACKUP_DIR
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(CURRENT_DIR, BACKUP_DIR)

        # Rename Json_Files -> Json_Files_Last inside BACKUP_DIR
        backup_json_path = os.path.join(BACKUP_DIR, "Json_Files")
        backup_json_last_path = os.path.join(BACKUP_DIR, "Json_Files_Last")
        if os.path.exists(backup_json_path):
            if os.path.exists(backup_json_last_path):
                shutil.rmtree(backup_json_last_path)
            os.rename(backup_json_path, backup_json_last_path)

        # Recreate empty Json_Files
        os.makedirs(CURRENT_JSON_DIR, exist_ok=True)

        # === Group updates by category ===
        from collections import defaultdict
        updates_by_category = defaultdict(list)
        for item in updates:
            if not isinstance(item, dict):
                continue
            cat = item.get("category_name")
            file = item.get("filename")
            prem = item.get("prem")
            if cat and file and prem is not None:
                updates_by_category[cat].append((file, prem))

        if not updates_by_category:
            return jsonify({"error": "No valid updates found."}), 400

        def extract_index(filename):
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else -1

        failed_updates = []
        success_updates = []

        # === Process updates category-wise ===
        for category_name, files in updates_by_category.items():
            json_path = os.path.join(backup_json_last_path, f"{category_name}.json")
            if not os.path.exists(json_path):
                failed_updates.append({
                    "category": category_name,
                    "reason": "JSON file not found"
                })
                continue

            try:
                with open(json_path, 'r') as jf:
                    json_data = json.load(jf)
            except Exception as e:
                failed_updates.append({
                    "category": category_name,
                    "reason": f"Failed to read JSON: {str(e)}"
                })
                continue

            for filename, prem_value in files:
                index = extract_index(filename)
                image_key = f"Image{index}"
                if image_key not in json_data:
                    failed_updates.append({
                        "category": category_name,
                        "filename": filename,
                        "reason": f"{image_key} not found in JSON"
                    })
                    continue
                json_data[image_key]["Prem"] = prem_value.lower() == "true"
                success_updates.append((category_name, filename))

            # Save updated JSON
            new_json_path = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")
            with open(new_json_path, 'w') as jf:
                json.dump(json_data, jf, indent=4)

        version_info = increment_version()

        return jsonify({
            "success": True,
            "updated": success_updates,
            "failed": failed_updates,
            "version": version_info
        })

    except Exception as e:
        # === Rollback in case of global failure ===
        try:
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)
            if os.path.exists(BACKUP_DIR):
                shutil.copytree(BACKUP_DIR, CURRENT_DIR)

            backup_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
            if os.path.exists(backup_json_last):
                restored_path = os.path.join(CURRENT_DIR, "Json_Files")
                if os.path.exists(restored_path):
                    shutil.rmtree(restored_path)
                os.rename(backup_json_last, restored_path)

        except Exception as rollback_error:
            return jsonify({
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


 # =======  * Rearrange Images * =======  
@app.route('/swap-images_IBGC', methods=['POST'])
def swap_images_IBGC():
    try:
        category_name = request.form.get('category_name')
        image1_name = request.form.get('image1_name')  # e.g., '002.webp'
        image2_name = request.form.get('image2_name')  # e.g., '005.webp'

        if not all([category_name, image1_name, image2_name]):
            return jsonify({"error": "Missing parameters"}), 400

        # === Step 1: Backup CURRENT_DIR -> BACKUP_DIR
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(CURRENT_DIR, BACKUP_DIR)

        # === Step 2: Rename Json_Files -> Json_Files_Last inside backup
        backup_json_path = os.path.join(BACKUP_DIR, "Json_Files")
        backup_json_last_path = os.path.join(BACKUP_DIR, "Json_Files_Last")
        if os.path.exists(backup_json_path):
            if os.path.exists(backup_json_last_path):
                shutil.rmtree(backup_json_last_path)
            os.rename(backup_json_path, backup_json_last_path)

        # === Step 3: Recreate empty Json_Files
        os.makedirs(CURRENT_JSON_DIR, exist_ok=True)

        # === Step 4: Resolve paths
        category_path = os.path.join(CURRENT_DIR, category_name)
        if not os.path.isdir(category_path):
            raise FileNotFoundError(f"Category '{category_name}' not found.")

        img1_path = os.path.join(category_path, image1_name)
        img2_path = os.path.join(category_path, image2_name)
        if not os.path.exists(img1_path) or not os.path.exists(img2_path):
            raise FileNotFoundError("One or both image files not found.")

        # === Step 5: Swap image files
        temp_path = os.path.join(category_path, "__temp_swap__.webp")
        os.rename(img1_path, temp_path)
        os.rename(img2_path, img1_path)
        os.rename(temp_path, img2_path)

        # === Step 6: Load and update JSON from backup
        category_json_path = os.path.join(backup_json_last_path, f"{category_name}.json")
        if not os.path.exists(category_json_path):
            raise Exception(f"JSON for category '{category_name}' not found.")

        with open(category_json_path, 'r') as jf:
            json_data = json.load(jf)

        def extract_index(filename):
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else -1

        index1 = extract_index(image1_name)
        index2 = extract_index(image2_name)

        item1_key = f"Image{index1}"
        item2_key = f"Image{index2}"

        if item1_key not in json_data or item2_key not in json_data:
            raise Exception("One or both images not found in JSON data.")

        # === Step 7: Swap the entire JSON entries
        json_data[item1_key], json_data[item2_key] = (
            json_data[item2_key],
            json_data[item1_key],
        )

        # === Step 8: Ensure their internal "Name" values match their keys
        json_data[item1_key]["Name"] = str(index1)
        json_data[item2_key]["Name"] = str(index2)

        # === Step 9: Save updated JSON
        new_json_path = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")
        with open(new_json_path, 'w') as jf:
            json.dump(json_data, jf, indent=4)

        # === Step 10: Update version
        version_info = increment_version()

        return jsonify({
            "success": True,
            "message": f"Swapped '{image1_name}' and '{image2_name}' successfully.",
            "version": version_info
        })

    except Exception as e:
        # === Rollback
        try:
            if os.path.exists(CURRENT_DIR):
                shutil.rmtree(CURRENT_DIR)
            if os.path.exists(BACKUP_DIR):
                shutil.copytree(BACKUP_DIR, CURRENT_DIR)

            # Restore Json_Files_Last
            backup_json_last = os.path.join(CURRENT_DIR, "Json_Files_Last")
            if os.path.exists(backup_json_last):
                restored_path = os.path.join(CURRENT_DIR, "Json_Files")
                if os.path.exists(restored_path):
                    shutil.rmtree(restored_path)
                os.rename(backup_json_last, restored_path)

        except Exception as rollback_error:
            return jsonify({
                "error": "Rollback failed.",
                "details": str(rollback_error)
            }), 500

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =============== Get Total Categories Count IBGC =====================
@app.route('/GetTotalCountCategories_IBGC', methods=['GET'])
def category_summary_IBGC():
    try:
        response = {}
        count = 0

        if not os.path.exists(CURRENT_DIR):
            return jsonify({"error": "Assets_IBGC directory not found."}), 404

        for folder in sorted(os.listdir(CURRENT_DIR)):
            folder_path = os.path.join(CURRENT_DIR, folder)

            # Skip the JSON directory
            if not os.path.isdir(folder_path) or folder == "Json_Files":
                continue

            # Count image files (you can adjust allowed extensions if needed)
            image_count = len([
                file for file in os.listdir(folder_path)
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            ])

            response[str(count)] = {
                "category_name": folder,
                "total_assets": image_count
            }
            count += 1

        response["Total_Categories"] = count
        return jsonify(response)

    except Exception as e:
        return jsonify({
            "error": "Failed to generate category summary.",
            "details": str(e)
        }), 500

# ================================  Get Url of Image of any Category ===============================
@app.route('/get-template-info_IBGC', methods=['GET'])
def get_template_info_IBGC():
    try:
        category_name = request.args.get('category_name')
        template_number = request.args.get('template_number')

        if not category_name or template_number is None:
            return jsonify({"error": "Missing category_name or template_number"}), 400

        image_filename = f"{template_number}.webp"
        json_file_path = os.path.join(CURRENT_JSON_DIR, f"{category_name}.json")

        if not os.path.exists(json_file_path):
            return jsonify({"error": "JSON for category not found."}), 404

        with open(json_file_path, 'r') as jf:
            data = json.load(jf)

        image_key = f"Image{template_number}"
        if image_key not in data:
            return jsonify({"error": f"Template number {template_number} not found in JSON."}), 404

        image_data = data[image_key]

        base_url = request.host_url.rstrip('/') 
        image_url = f"{base_url}/static/Assets_IBGC/{category_name}/{image_filename}"

        return jsonify({
            "ImageUrl": image_url,
            "Name": image_data.get("Name"),
            "Prem": image_data.get("Prem")
        })

    except Exception as e:
        return jsonify({
            "error": "Something went wrong while fetching template info.",
            "details": str(e)
        }), 500

# ============================ CHECK VERSION ===============================
@app.route("/check-version_IBGC", methods=["GET"])
def check_version_IBGC():
    data = get_current_version()
    return jsonify(data)



# --- Runing :))) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
