"""AI-upscale a video clip frame by frame with Real-ESRGAN (spandrel), streaming to keep RAM low.

704x1280 Wan clip -> x2 model -> resized to --width (default 1080, aspect kept) -> H.264 CRF 14.
The assembler then only center-crops to 1080x1920, so the final video keeps the AI-recovered detail.
Run with the ComfyUI venv (has torch + spandrel + av); do NOT run while ComfyUI renders (shares the GPU):
  ComfyUI/venv/Scripts/python.exe scripts/upscale_video_clip_realesrgan.py in.mp4 out.mp4
"""
import argparse
import sys
import time
from pathlib import Path

import av
import torch
import torch.nn.functional as F
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "ComfyUI" / "models" / "upscale_models" / "RealESRGAN_x2plus.pth"


def load_model(path, device):
    model = ModelLoader().load_from_file(str(path)).eval().to(device)
    half = device == "cuda" and model.supports_half
    if half:
        model.model.half()
    return model, half


@torch.inference_mode()
def upscale_frame(model, half, frame_rgb, device, width):
    x = torch.from_numpy(frame_rgb).to(device).permute(2, 0, 1).unsqueeze(0)
    x = (x.half() if half else x.float()) / 255.0
    y = model(x).float().clamp_(0, 1)
    height = round(width * y.shape[2] / y.shape[3] / 2) * 2  # even height for yuv420p
    y = F.interpolate(y, size=(height, width), mode="bicubic", antialias=True, align_corners=False)
    return (y[0].permute(1, 2, 0).clamp_(0, 1) * 255).round().byte().cpu().numpy()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--model", default=str(DEFAULT_MODEL))
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--max-frames", type=int, default=0, help="for quick tests; 0 = all")
    args = p.parse_args()

    model, half = load_model(args.model, args.device)
    src = av.open(args.input)
    stream_in = src.streams.video[0]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    dst = av.open(args.output, "w")
    stream_out = None
    started, count = time.time(), 0
    try:
        for frame in src.decode(video=0):
            out = upscale_frame(model, half, frame.to_ndarray(format="rgb24"), args.device, args.width)
            if stream_out is None:  # create the encoder once the output size is known
                stream_out = dst.add_stream("libx264", rate=stream_in.average_rate)
                stream_out.width, stream_out.height = out.shape[1], out.shape[0]
                stream_out.pix_fmt = "yuv420p"
                stream_out.options = {"crf": "14", "preset": "slow"}
            for packet in stream_out.encode(av.VideoFrame.from_ndarray(out, format="rgb24")):
                dst.mux(packet)
            count += 1
            if args.max_frames and count >= args.max_frames:
                break
        if stream_out is not None:
            for packet in stream_out.encode():
                dst.mux(packet)
    finally:
        dst.close()
        src.close()
    print(f"OK {args.output}: {count} frames -> {stream_out.width}x{stream_out.height} "
          f"in {time.time() - started:.0f}s ({args.device}{', fp16' if half else ''})")


if __name__ == "__main__":
    main()
