export const captionStylePresets = [
  {
    id: "minimalist",
    title: "Minimalist",
    description: "Clean and readable for documentaries, history, and dark storytelling.",
    templateName: "minimalist",
  },
  {
    id: "line-focus",
    title: "Line Focus",
    description: "Good for structured narration where each phrase needs strong emphasis.",
    templateName: "line-focus",
  },
  {
    id: "word-focus",
    title: "Word Focus",
    description: "Highlights key words for dramatic hooks and intense short-form pacing.",
    templateName: "word-focus",
  },
  {
    id: "classic",
    title: "Classic",
    description: "Balanced subtitles for general storytelling and historical figures.",
    templateName: "classic",
  },
  {
    id: "neo-minimal",
    title: "Neo Minimal",
    description: "Modern clean subtitles for premium-looking reels and shorts.",
    templateName: "neo-minimal",
  },
  {
    id: "explosive",
    title: "Explosive",
    description: "Best for high drama, disasters, reveals, and shocking moments.",
    templateName: "explosive",
  },
  {
    id: "fast",
    title: "Fast",
    description: "Sharper pacing for high-energy captions and quick cuts.",
    templateName: "fast",
  },
  {
    id: "hype",
    title: "Hype",
    description: "Attention-grabbing style for emotionally loud edits and promo energy.",
    templateName: "hype",
  },
  {
    id: "vibrant",
    title: "Vibrant",
    description: "Bold, colorful captions for more expressive or moral-story content.",
    templateName: "vibrant",
  },
  {
    id: "retro-gaming",
    title: "Retro Gaming",
    description: "Stylized pixel feel for playful edits, irony, or experimental storytelling.",
    templateName: "retro-gaming",
  },
];

export const defaultCaptionStylePreset = captionStylePresets[0];
export const transcriptFormats = [
  { value: "auto", label: "Auto detect" },
  { value: "srt", label: "SRT" },
  { value: "vtt", label: "VTT" },
  { value: "whisper_json", label: "Whisper JSON" },
  { value: "pycaps_json", label: "pycaps JSON" },
];
