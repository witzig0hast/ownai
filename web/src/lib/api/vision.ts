import { apiFetch } from "../api-client";

export interface VisionDescribeResult {
  ocr_text: string | null;
  description: string | null;
}

/** POST /vision/describe (multipart) — OCR text plus an optional vision-model description. */
export async function describeImage(imageBlob: Blob): Promise<VisionDescribeResult> {
  const formData = new FormData();
  const extension = imageBlob.type.includes("png") ? "png" : "jpg";
  formData.append("image", imageBlob, `image.${extension}`);

  return apiFetch<VisionDescribeResult>("/vision/describe", {
    method: "POST",
    body: formData,
  });
}
