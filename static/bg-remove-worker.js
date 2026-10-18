// PureFileConverter: AI background removal, runs entirely in the visitor's browser (Web Worker).
// Library: Transformers.js (Apache-2.0). Model: onnx-community/ormbg-ONNX (Apache-2.0), 8-bit quantized (~44 MB),
// downloaded once from the Hugging Face CDN and cached by the browser. No image ever reaches our server.
import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.1/dist/transformers.min.js";

env.allowLocalModels = false;

let segmenterPromise = null;

function getSegmenter() {
  if (!segmenterPromise) {
    segmenterPromise = pipeline("background-removal", "onnx-community/ormbg-ONNX", {
      dtype: "q8",
      device: "wasm",
      progress_callback: (p) => {
        if (p.status === "progress" && p.file && p.file.endsWith(".onnx")) {
          self.postMessage({ type: "progress", percent: Math.round(p.progress || 0) });
        }
      },
    }).catch((err) => {
      segmenterPromise = null; // allow a retry after a network failure
      throw err;
    });
  }
  return segmenterPromise;
}

self.onmessage = async (event) => {
  try {
    const segmenter = await getSegmenter();
    self.postMessage({ type: "status", text: "Removing background..." });
    const result = await segmenter(event.data.blob);
    const png = await result.toBlob("image/png");
    self.postMessage({ type: "done", blob: png });
  } catch (err) {
    self.postMessage({ type: "error", message: String((err && err.message) || err) });
  }
};
