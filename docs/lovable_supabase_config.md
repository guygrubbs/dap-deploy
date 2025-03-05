# Lovable/Supabase Integration Guide

## 1. Overview

Your FastAPI backend now has **two main ways** to handle PDF pitch decks:

1. **Ephemeral Usage**: Provide the pitch deck via a **public or signed URL** from Supabase, so the backend can fetch the PDF, extract text, and inject it into GPT prompts **for a single request** (no permanent training).

2. **Optional Fine-Tuning**: If you want to train a custom model on certain pitch decks, you can run a separate flow that converts a deck to `.jsonl` and uploads it to OpenAI with `purpose="fine-tune"`.

**Core Endpoints**:

- **`POST /reports/{report_id}/generate`** (Ephemeral usage)  
- **`POST /pitchdecks/{deck_file}/upload_to_openai`** (Fine-tuning approach)

**Supabase’s role**:  
- **Stores pitch-deck PDFs** in a bucket (like `pitchdecks`).  
- Provides a **public or signed URL** to the PDF so the backend can `GET` it.  
- Optionally, you can store the reference in your `reports` table (or pass it via request parameters).

---

## 2. Setting up Pitch Deck PDFs in Supabase

1. **Create a `pitchdecks` bucket** in Supabase (or any custom name).  
2. **Upload PDF** pitch deck from your front-end (Lovable). Supabase returns a file path or you can generate a **public/signed URL** using the [Supabase Storage APIs](https://supabase.com/docs/guides/storage).  
3. **Store** that `pitch_deck_url` in your front-end database record or pass it directly to the backend’s `parameters`.

> **Example**: A front-end user uploads `deal123.pdf` to `pitchdecks`. The front-end calls the [Supabase Storage `getPublicUrl`](https://supabase.com/docs/reference/javascript/storage-getpublicurl) or `createSignedUrl` method. The result might be:  
> ```
> https://xyzcompany.supabase.co/storage/v1/object/sign/pitchdecks/deal123.pdf?...token=123...
> ```

---

## 3. Ephemeral Usage in “Generate Report”

### 3.1 Providing the PDF URL

When you create a new report or update an existing one, **include** the `pitch_deck_url` in the `parameters` JSON. For instance, from Lovable’s front-end:

```json
{
  "user_id": "123",
  "startup_id": "456",
  "report_type": "investment_readiness",
  "title": "Test Ephemeral Report",
  "parameters": {
    "pitch_deck_url": "https://xyzcompany.supabase.co/storage/v1/object/sign/pitchdecks/deal123.pdf?token=abc..."
  }
}
```

You can store this record in your local DB or call your backend’s `POST /reports` endpoint with this body. The backend now knows the public/signed URL.

### 3.2 Generating the Report

To finalize the report:

```bash
POST /reports/{report_id}/generate
```

**Backend Logic**:

1. It checks `parameters["pitch_deck_url"]`.  
2. If found, the backend does `requests.get(...)` on that URL to download the PDF from Supabase.  
3. Extracts text with OCR fallback (PyMuPDF + Tesseract).  
4. Injects that text **ephemerally** into GPT prompts for each section.  
5. The pitch-deck text is **NOT** stored or fine-tuned—just used once.

**Response**:  
A JSON object containing the final sections, a PDF summary link (if GCS is used), etc.

---

## 4. Optional: Fine-Tuning via “pitchdecks/{deck_file}/upload_to_openai”

If you want the model to “learn” from the pitch deck for more universal usage:

1. **Ensure** the PDF is in the `pitchdecks` bucket under some file name (e.g. `deck123.pdf`).  
2. Call:
   ```bash
   POST /pitchdecks/{deck_file}/upload_to_openai
   ```
   - Path param `{deck_file}` = `deck123.pdf`  
   - Request body can specify `bucket` (default = `pitchdecks`), `output_filename`, and a boolean `upload_to_openai`.  

**What the Backend Does**:

- Downloads the PDF from Supabase (by file name + bucket).  
- Extracts text.  
- Splits it into `.jsonl` records (one record per ~1000 tokens).  
- If `upload_to_openai == true`, calls `openai.File.create(...)` with `purpose="fine-tune"`.  

**Result**:  
- You get an `openai_file_id`. You can then launch a fine-tuning job via the OpenAI CLI or API.  
- This approach is purely for training a custom model, **not ephemeral**.

---

## 5. Updating Lovable’s Flow

### 5.1 Example High-Level Steps

1. **User Logs In** to Lovable, sees a place to upload PDFs.  
2. **Upload** PDF to Supabase bucket `pitchdecks`:
   - Return a **public or signed URL** or store the file path.  
3. **Create or Update** a “report” record in your backend, specifying the `pitch_deck_url` in `parameters`.  
4. **Trigger** the `POST /reports/{report_id}/generate` once the user wants the actual GPT-based analysis.  
5. **Lovable** monitors the status from `GET /reports/{report_id}/status` or similar.  
6. **Finished**: The user can see the final sections or PDF from the backend’s response.

### 5.2 Token / Auth

- The example code uses a **static token** approach with `verify_token`. In production, you might integrate a real OAuth or JWT. Lovable should supply the correct token in the `Authorization: Bearer <token>` header.

---

## 6. Key Environment Variables for Supabase

Ensure your environment or Docker includes:

- `SUPABASE_URL` = `<your-supabase-project-url>`  
- `SUPABASE_SERVICE_KEY` = `<service-role-key>`  

If your app references the “public/signed URL” approach, you might not need `supabase-py` calls for ephemeral usage. But if you prefer direct `bucket.download()` calls, you do.

---

## 7. Confirming Public vs. Signed URLs

**Public**: If your bucket or file is publicly accessible, you can generate a “public” URL once. The backend can simply `requests.get()` that link.  
**Signed**: If your bucket is private, you’d do something like:
```python
signed_url = supabase.storage.from_("pitchdecks").create_signed_url("deck123.pdf", expires_in=3600)
```
Then pass that `signed_url` to the backend. The code will `requests.get` that ephemeral link. This link can expire after 1 hour, providing more security.

---

## 8. Edge Cases & Best Practices

1. **Large PDFs**:
   - The ephemeral approach includes the entire deck text in GPT prompts. If the text is extremely large, you could exceed GPT’s context window.  
   - **Solution**: Summarize or chunk the PDF before passing it to GPT, e.g. only key pages or ~ a few thousand tokens.

2. **OCR Dependencies**:
   - Tesseract must be installed for scanning-based PDFs. If your PDFs are always text-based, you can skip that.

3. **Security**:
   - Signed URLs from Supabase should have short expiration times if sensitive.  
   - The ephemeral usage means the pitch deck is not retained in logs (assuming your logging is safe). The user can re-generate if needed.

4. **Storage**:
   - The final PDF report is optionally uploaded to GCS. That is separate from pitch-deck storage in Supabase. Or you can store the final PDF in Supabase as well. Adjust `finalize_report_with_pdf` if you want to store in Supabase instead.

---

## 9. Example Workflow in Lovable

1. **User** picks a PDF from local machine.  
2. **Lovable** uploads PDF to `pitchdecks` bucket, receives a signed URL.  
3. **Lovable** calls `POST /reports` with some metadata + `"parameters": {"pitch_deck_url": "<that-signed-URL>"}`.  
4. **Lovable** calls `POST /reports/{report_id}/generate`.  
5. The backend fetches the PDF from Supabase, ephemeral usage, merges text into GPT prompt, returns final sections.  
6. The final PDF is stored in GCS (by default) with a signed URL.  
7. **Lovable** calls `GET /reports/{report_id}` or `GET /reports/{report_id}/content` to display the report sections or final PDF link.

---

## 10. Conclusion

With these steps, the **Lovable** front-end can seamlessly provide pitch-decks from Supabase to the backend for ephemeral GPT usage or optional fine-tuning. Key points:

- **Ephemeral**: `pitch_deck_url` → `/reports/generate` → single-run GPT usage.  
- **Fine-tuning**: `pitchdecks/{deck_file}/upload_to_openai` → `.jsonl` → permanent custom model.

**Next Steps**:

- **Ensure** you have all environment variables set.  
- **Test** uploading a sample PDF, see if the ephemeral text is recognized in GPT.  
- **Validate** that large PDFs do not exceed GPT context (or chunk them if needed).  