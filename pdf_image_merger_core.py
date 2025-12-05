# pdf_image_merger_core.py

import os
import traceback
from PyPDF2 import PdfMerger
from PIL import Image

MERGED_FILENAME = "MERGED_OUTPUT.pdf"

# ---------- Worker functions ---------- 
def safe_merge_pdfs(pdf_paths, output_path, log):
    merger = PdfMerger()
    good_files = []

    for pdf in pdf_paths:
        try:
            merger.append(pdf)
            good_files.append(pdf)
        except Exception as e:
            log.append(f"⚠ Skipping corrupted or unreadable PDF: {pdf}")
            log.append(f"    Error: {e}")

    if not good_files:
        log.append("❌ No valid PDFs to merge in this folder.")
        return False

    try:
        merger.write(output_path)
        merger.close()
        log.append(f"✔ Merged {len(good_files)} PDF(s) into: {output_path}")
        return True
    except Exception as e:
        log.append(f"❌ Failed to write merged PDF: {output_path}")
        log.append(str(e))
        return False


def safe_merge_images_to_pdf(image_paths, output_path, log):
    images = []
    try:
        for img_path in image_paths:
            img = Image.open(img_path).convert("RGB")
            images.append(img)
    except Exception as e:
        log.append(f"⚠ Error opening image {img_path}: {e}")

    if not images:
        return False

    try:
        first = images[0]
        if len(images) > 1:
            first.save(output_path, save_all=True, append_images=images[1:])
        else:
            first.save(output_path)
        log.append(f"✔ Merged images into: {output_path}")
        return True
    except Exception as e:
        log.append(f"❌ Failed to write images PDF: {output_path}")
        log.append(str(e))
        return False


# ---------- Directory processing ----------

def gather_target_folders(root_folder, skip_already_merged=True):
    """Return list of folders to process."""
    candidates = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        candidates.append(dirpath)
    return candidates


def process_single_folder(folder_path, log):
    """Process one folder: merge PDFs and/or images if present. Returns True if any merge created."""
    try:
        files = os.listdir(folder_path)
    except Exception as e:
        log.append(f"⚠ Cannot access folder {folder_path}: {e}")
        return False

    if MERGED_FILENAME in files:
        log.append(f"⚠ Skipping folder (already merged): {folder_path}")
        return False

    pdf_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith('.pdf') and f != MERGED_FILENAME]
    image_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    pdf_files.sort()
    image_files.sort()

    created_any = False
    output_path = os.path.join(folder_path, MERGED_FILENAME)

    if pdf_files and image_files:
        tmp_pdf_1 = os.path.join(folder_path, "__tmp_pdf_part1.pdf")
        tmp_pdf_2 = os.path.join(folder_path, "__tmp_pdf_part2.pdf")

        if safe_merge_pdfs(pdf_files, tmp_pdf_1, log):
            if safe_merge_images_to_pdf(image_files, tmp_pdf_2, log):
                try:
                    merger = PdfMerger()
                    merger.append(tmp_pdf_1)
                    merger.append(tmp_pdf_2)
                    merger.write(output_path)
                    merger.close()
                    created_any = True
                    log.append(f"✔ Combined PDFs+images into: {output_path}")
                except Exception as e:
                    log.append(f"❌ Failed to combine tmp parts into final output: {e}")

        for p in (tmp_pdf_1, tmp_pdf_2):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    elif pdf_files:
        if safe_merge_pdfs(pdf_files, output_path, log):
            created_any = True

    elif image_files:
        if safe_merge_images_to_pdf(image_files, output_path, log):
            created_any = True

    else:
        log.append(f"  No PDFs or images found in: {folder_path}")

    return created_any
